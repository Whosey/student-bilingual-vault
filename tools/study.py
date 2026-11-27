"""Import and update bilingual course readings in an Obsidian vault."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from hashlib import sha256
from html import escape
from io import BytesIO
import json
import os
from pathlib import Path
import re
import sys
from tempfile import NamedTemporaryFile

from pypdf import PdfReader
from pypdf.errors import PyPdfError


PRIVATE = Path("我的学习")
INBOX = PRIVATE / "收件箱"
MATERIALS = PRIVATE / "资料"
COURSES = PRIVATE / "课程"
PENDING_COURSE = Path("待归类.md")
PAGE_MARKER = re.compile(r"^<!-- study:page (\d+) (pending|blocked|done) -->$", re.M)
LAYOUT_GAP = re.compile(r"\S {8,}\S")
LIST_START = re.compile(r"^(?:[•●▪◦‣⁃]|[-*+]\s|\d+[.)]\s)")
WAITING_TEXT = "> 待翻译。"
BLOCKED_PREFIX = "> **需核对** "


def write_atomic(path: Path, data: bytes, *, prior_note: str | None = None) -> None:
    with NamedTemporaryFile(dir=path.parent, delete=False) as temp:
        temp_path = Path(temp.name)
        try:
            temp.write(data)
        except BaseException:
            temp.close()
            temp_path.unlink(missing_ok=True)
            raise
    try:
        if prior_note is not None and path.read_text(encoding="utf-8") != prior_note:
            raise ValueError("阅读笔记刚被修改。已保留草稿，请重新运行后再保存。")
        temp_path.replace(path)
    finally:
        temp_path.unlink(missing_ok=True)


def write_note(path: Path, content: str, *, prior_note: str | None = None) -> None:
    if content != prior_note:
        write_atomic(path, content.encode("utf-8"), prior_note=prior_note)


@contextmanager
def edit_library():
    PRIVATE.mkdir(exist_ok=True)
    with (PRIVATE / ".study-lock").open("a+b") as lock:
        try:
            if os.name == "nt":
                import msvcrt
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise ValueError("另一个整理命令正在写入，请稍后重试。") from error
        yield


def field_value(value: str | int) -> str:
    return json.dumps(value, ensure_ascii=False)


def frontmatter(fields: dict[str, str | int]) -> str:
    return "---\n" + "".join(f"{key}: {field_value(value)}\n" for key, value in fields.items()) + "---\n"


def split_note(content: str) -> tuple[str, str]:
    if not content.startswith("---\n") or "\n---\n" not in content[4:]:
        raise ValueError("阅读笔记缺少属性区。请先恢复文件顶部的属性。")
    header, body = content[4:].split("\n---\n", 1)
    return header, body


def get_field(content: str, key: str) -> str:
    header, _ = split_note(content)
    match = re.search(rf"^{key}: ([^\n]*)$", header, re.M)
    if match is None:
        raise ValueError(f"阅读笔记缺少 {key} 属性。")
    return match[1]


def set_field(content: str, key: str, value: str) -> str:
    get_field(content, key)
    header, body = split_note(content)
    updated = re.sub(rf"^{key}: [^\n]*$", lambda _: f"{key}: {field_value(value)}", header, count=1, flags=re.M)
    return f"---\n{updated}\n---\n{body}"


def plain_text(text: str) -> str:
    return re.sub(r"([\\\x60*_[\]#|~])", r"\\\1", escape(text, quote=False))


def link(path: Path, label: str, page: int | None = None) -> str:
    anchor = f"#page={page}" if page else ""
    return f"[[{path.as_posix()}{anchor}|{label}]]"


def course_reference(path: Path) -> str:
    return f"[[{path.with_suffix('').as_posix()}]]"


def init() -> dict:
    for folder in (INBOX, MATERIALS, COURSES, PRIVATE / "笔记", PRIVATE / "附件"):
        folder.mkdir(parents=True, exist_ok=True)
    return {"inbox": INBOX.as_posix()}


def ensure_course(name: str) -> Path:
    name = " ".join(name.split())
    if not name:
        raise ValueError("请填写课程名，或省略 --course 以放入待归类。")
    safe_name = re.sub(r"[^\w-]+", "-", name).strip("-")[:42] or "课程"
    # The suffix also distinguishes spellings that normalize to the same file name.
    suffix = sha256(name.encode("utf-8")).hexdigest()[:16]
    path = COURSES / f"{safe_name}-{suffix}.md"
    if not path.exists():
        fields = frontmatter({"kind": "course", "title": name})
        write_note(path, f"{fields}\n# {plain_text(name)}\n\n![[基础视图/课程资料.base]]\n\n## 课程笔记\n")
    return path


def pdf_reader(data: bytes) -> PdfReader:
    reader = PdfReader(BytesIO(data))
    if reader.is_encrypted:
        raise ValueError("这个 PDF 受密码保护。请提供你有权使用的已解密副本。")
    if not reader.pages:
        raise ValueError("PDF 没有可打开的页面。")
    return reader


def page_states(content: str) -> dict[int, re.Match]:
    count = int(get_field(content, "page_count"))
    matches = list(PAGE_MARKER.finditer(content))
    states = {int(match[1]): match for match in matches}
    if len(matches) != count or set(states) != set(range(1, count + 1)):
        raise ValueError("阅读笔记的页码标记不完整。请先恢复页码标记。")
    return states


def progress(content: str, note: Path) -> dict:
    pages = page_states(content)
    complete = [number for number, match in sorted(pages.items()) if match[2] == "done"]
    blocked = [number for number, match in sorted(pages.items()) if match[2] == "blocked"]
    pending = [number for number, match in sorted(pages.items()) if match[2] == "pending"]
    if blocked:
        status = "需核对"
    elif pending:
        status = "翻译中" if complete else "待翻译"
    else:
        status = "已完成"
    course = get_field(content, "course")
    return {
        "note": note.as_posix(),
        "source": note.with_name("原件.pdf").as_posix(),
        "course": course.strip("\"'"),
        "page_count": len(pages),
        "complete": complete,
        "pending": pending,
        "blocked": blocked,
        "remaining": sorted(pending + blocked),
        "status": status,
    }


def prepare(pdf: Path, course: str | None) -> dict:
    if pdf.suffix.lower() != ".pdf":
        raise ValueError("首版接受 PDF。请将 PPT 导出为可选中文字的 PDF 后再试。")
    data = pdf.read_bytes()
    count = len(pdf_reader(data).pages)
    init()
    folder = MATERIALS / sha256(data).hexdigest()
    folder.mkdir(exist_ok=True)
    note = folder / "阅读.md"
    source = folder / "原件.pdf"
    if source.exists():
        if source.read_bytes() != data:
            raise ValueError("归档原件已被替换。请先恢复这份原件。")
    else:
        write_atomic(source, data)
    if note.exists():
        content = note.read_text(encoding="utf-8")
        if course is not None:
            prior_note = content
            content = set_field(content, "course", course_reference(ensure_course(course)))
            write_note(note, content, prior_note=prior_note)
        return progress(content, note)

    course_path = PENDING_COURSE if course is None else ensure_course(course)
    content = frontmatter({
        "kind": "reading",
        "title": pdf.stem,
        "course": course_reference(course_path),
        "status": "待翻译",
        "page_count": count,
    })
    content += f"\n# {plain_text(pdf.stem)}（中英对照）\n\n{link(source, '打开原 PDF')}\n"
    for page in range(1, count + 1):
        content += (
            f"\n## 第 {page} 页\n\n{link(source, f'打开原 PDF 第 {page} 页', page)}\n\n"
            f"<!-- study:page {page} pending -->\n{WAITING_TEXT}\n"
        )
    content += "\n## 我的疑问\n"
    write_note(note, content)
    return progress(content, note)


def load_note(path: Path) -> tuple[Path, str]:
    note = path.resolve().relative_to(Path.cwd().resolve())
    if (
        note.parent.parent != MATERIALS
        or note.name != "阅读.md"
        or not re.fullmatch("[a-f0-9]{64}", note.parent.name)
    ):
        raise ValueError("请使用 prepare 返回的阅读笔记路径。")
    return note, note.read_text(encoding="utf-8")


def source_pdf(note: Path) -> PdfReader:
    data = note.with_name("原件.pdf").read_bytes()
    if sha256(data).hexdigest() != note.parent.name:
        raise ValueError("归档原件已被替换。请先恢复对应的原件，再继续翻译。")
    return pdf_reader(data)


def page_text(reader: PdfReader, number: int) -> dict:
    try:
        page = reader.pages[number - 1]
        if page.extract_text(orientations=(90, 180, 270)).strip():
            return {"issue": "这页含有旋转的文字，提取结果可能漏段。请打开原页核对。"}
        text = page.extract_text(extraction_mode="layout")
    except (PyPdfError, ValueError, NotImplementedError) as error:
        return {"issue": f"无法提取这一页的文字（{type(error).__name__}）。请打开原页核对。"}
    if not text or not any(char.isalnum() for char in text):
        return {"issue": "这页未提取到可读文字。请检查原页，扫描件可先添加文字层。"}
    if sum(bool(LAYOUT_GAP.search(line.strip())) for line in text.splitlines()) >= 2:
        return {"issue": "这页可能包含分栏或表格，提取顺序需要核对。请打开原页。"}

    paragraphs = []
    lines = []
    for line in text.splitlines() + [""]:
        line = " ".join(line.split())
        if lines and (not line or LIST_START.match(line)):
            paragraphs.append(" ".join(lines))
            lines = []
        if line:
            lines.append(line)
    return {"paragraphs": paragraphs}


def extract(note: Path, content: str, start: int, stop: int | None) -> dict:
    state = progress(content, note)
    count = state["page_count"]
    stop = min(count, start + 4) if stop is None else stop
    if not 1 <= start <= stop <= count:
        raise ValueError(f"页码范围应在 1 到 {count} 之间。")
    reader = source_pdf(note)
    pages = {
        str(number): page_text(reader, number)
        for number in state["remaining"]
        if start <= number <= stop
    }
    return {**state, "pages": pages}


def translation_block(reader: PdfReader, page: int, value: object) -> tuple[str, str]:
    if isinstance(value, dict) and set(value) == {"issue"}:
        issue = value["issue"]
        if isinstance(issue, str) and issue.strip():
            return "blocked", BLOCKED_PREFIX + plain_text(" ".join(issue.split()))
    original = page_text(reader, page)
    if "issue" in original:
        raise ValueError(f"第 {page} 页需要标为需核对。{original['issue']}")
    english = original["paragraphs"]
    if (
        not isinstance(value, list)
        or len(value) != len(english)
        or any(not isinstance(paragraph, str) or not paragraph.strip() for paragraph in value)
    ):
        raise ValueError(f"第 {page} 页应包含 {len(english)} 个非空中文译段。")
    pairs = []
    for source, translated in zip(english, value):
        safe_translation = translated.strip().replace("<!--", "&lt;!--")
        pairs.append(f"{plain_text(source)}\n\n{safe_translation}")
    return "done", "\n\n".join(pairs)


def replacement_end(content: str, position: int) -> int:
    remaining = content[position:].lstrip("\n")
    next_line = remaining.split("\n", 1)[0]
    if next_line == WAITING_TEXT or next_line.startswith(BLOCKED_PREFIX):
        return len(content) - len(remaining) + len(next_line)
    return position


def save(note: Path, content: str, draft: Path) -> dict:
    prior_note = content
    values = json.loads(draft.read_text(encoding="utf-8-sig"))
    if not isinstance(values, dict) or not values:
        raise ValueError("译稿需要是以页码为键的非空 JSON 对象。")
    states = page_states(content)
    reader = source_pdf(note)
    changes = []
    for key, value in values.items():
        if not re.fullmatch(r"[1-9][0-9]*", key) or int(key) not in states:
            raise ValueError(f"译稿包含无效页码 {key!r}。")
        page = int(key)
        marker = states[page]
        if marker[2] == "done":
            continue
        state, block = translation_block(reader, page, value)
        end = replacement_end(content, marker.end())
        changes.append((marker.start(), end, f"<!-- study:page {page} {state} -->\n\n{block}"))
    if not changes:
        return progress(content, note)
    for start, end, block in sorted(changes, reverse=True):
        # A blank line after each marker keeps it invisible in Obsidian reading view.
        content = content[:start] + block + "\n" + content[end:]
    result = progress(content, note)
    write_note(note, set_field(content, "status", result["status"]), prior_note=prior_note)
    return result


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="课程 PDF 整理和逐段中英对照")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="创建个人资料目录")
    importer = commands.add_parser("prepare", help="归档原件并建立阅读笔记")
    importer.add_argument("pdf", type=Path)
    importer.add_argument("--course")
    extractor = commands.add_parser("pages", help="按页提取待翻原文")
    extractor.add_argument("note", type=Path)
    extractor.add_argument("--from", dest="start", type=int, default=1)
    extractor.add_argument("--to", dest="stop", type=int)
    writer = commands.add_parser("save", help="校验并写入逐段译文")
    writer.add_argument("note", type=Path)
    writer.add_argument("draft", type=Path)
    status = commands.add_parser("status", help="查看待翻及需核对页")
    status.add_argument("note", type=Path)
    args = parser.parse_args()
    try:
        if args.command in {"init", "prepare", "save"}:
            with edit_library():
                if args.command == "init":
                    result = init()
                elif args.command == "prepare":
                    result = prepare(args.pdf, args.course)
                else:
                    result = save(*load_note(args.note), args.draft)
        else:
            note, content = load_note(args.note)
            if args.command == "pages":
                result = extract(note, content, args.start, args.stop)
            else:
                result = progress(content, note)
    except (ValueError, PyPdfError, OSError) as error:
        print(f"整理失败。{error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
