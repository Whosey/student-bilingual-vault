import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


CLI = Path(__file__).resolve().parents[1] / "tools" / "study.py"


def make_pdf(path, pages, *, rotated_text=False):
    writer = PdfWriter()
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    for paragraphs in pages:
        page = writer.add_blank_page(width=432, height=600)
        if paragraphs:
            page[NameObject("/Resources")] = DictionaryObject({
                NameObject("/Font"): DictionaryObject({NameObject("/F1"): font}),
            })
            source = DecodedStreamObject()
            operations = "\n".join(
                f"1 0 0 1 40 {550 - 40 * index} Tm ({paragraph}) Tj"
                for index, paragraph in enumerate(paragraphs)
            )
            if rotated_text:
                operations += "\n0 1 -1 0 50 150 Tm (Important content) Tj"
            source.set_data(f"BT /F1 12 Tf\n{operations}\nET".encode("ascii"))
            page.replace_contents(source)
    writer.write(path)


class StudyWorkflowTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.pdf = self.root / "Week 03 [slides].pdf"
        make_pdf(self.pdf, [
            ["A linear system contains equations.", "Each equation has a solution set."],
            ["A pivot can determine a variable."],
            [],
        ])

    def command(self, *args, ok=True):
        result = subprocess.run(
            [sys.executable, "-X", "utf8", str(CLI), *map(str, args)],
            cwd=self.root, capture_output=True, encoding="utf-8",
        )
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        return result.stderr

    def save(self, note, data, **kwargs):
        draft = self.root / "translations.json"
        draft.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return self.command("save", note, draft, **kwargs)

    def test_init_creates_inbox(self):
        result = self.command("init")
        self.assertTrue((self.root / result["inbox"]).is_dir())

    def test_import_and_translate_with_links_to_exact_pages(self):
        result = self.command("prepare", self.pdf, "--course", "线性代数")
        note = self.root / result["note"]
        source = self.root / result["source"]
        self.assertEqual(source.read_bytes(), self.pdf.read_bytes())
        pages = self.command("pages", note, "--from", 1, "--to", 1)["pages"]
        self.assertEqual(pages, {
            "1": {"paragraphs": ["A linear system contains equations.", "Each equation has a solution set."]},
        })
        result = self.save(note, {"1": ["线性方程组包含多个方程。", "每个方程都有一个解集。"]})
        self.assertEqual(result["complete"], [1])
        self.assertEqual(result["pending"], [2, 3])
        content = note.read_text(encoding="utf-8")
        self.assertIn(f"[[{source.relative_to(self.root).as_posix()}#page=1|", content)
        self.assertIn("A linear system contains equations.\n\n线性方程组包含多个方程。", content)
        self.assertIn("Each equation has a solution set.\n\n每个方程都有一个解集。", content)
        self.assertEqual(len(list((self.root / "我的学习" / "课程").glob("*.md"))), 1)

    def test_resume_keeps_manual_translation_and_questions(self):
        note = self.root / self.command("prepare", self.pdf)["note"]
        self.save(note, {"1": ["有若干线性方程。", "每个方程都有一个解集。"]})
        edited = note.read_text(encoding="utf-8").replace("有若干线性方程。", "这是我改过的译文。")
        note.write_text(edited + "\n- 为什么主元重要？\n", encoding="utf-8")
        self.assertEqual(self.command("prepare", self.pdf)["note"], note.relative_to(self.root).as_posix())
        result = self.save(note, {"1": ["覆盖一", "覆盖二"], "2": ["主元可以确定一个变量。"]})
        self.assertEqual(result["complete"], [1, 2])
        content = note.read_text(encoding="utf-8")
        self.assertIn("这是我改过的译文。", content)
        self.assertIn("为什么主元重要？", content)
        self.assertNotIn("覆盖一", content)

    def test_invalid_translation_batch_leaves_note_intact(self):
        note = self.root / self.command("prepare", self.pdf)["note"]
        original = note.read_bytes()
        self.save(note, {"1": ["合格一", "合格二"], "2": ["多了一条", "另一条"]}, ok=False)
        self.assertEqual(note.read_bytes(), original)

    def test_empty_page_stays_visible_and_incomplete(self):
        note = self.root / self.command("prepare", self.pdf)["note"]
        issue = self.command("pages", note, "--from", 3)["pages"]["3"]["issue"]
        result = self.save(note, {"1": ["译文一", "译文二"], "2": ["译文三"], "3": {"issue": issue}})
        self.assertEqual(result["blocked"], [3])
        self.assertEqual(result["status"], "需核对")
        self.assertIn(issue, note.read_text(encoding="utf-8"))
        self.assertEqual(self.command("status", note)["remaining"], [3])

    def test_resuming_blocked_page_removes_old_placeholder(self):
        note = self.root / self.command("prepare", self.pdf)["note"]
        self.save(note, {"2": {"issue": "稍后核对原文"}})
        result = self.save(note, {"2": ["主元可以确定一个变量。"]})
        self.assertEqual(result["complete"], [2])
        self.assertNotIn("稍后核对原文", note.read_text(encoding="utf-8"))

    def test_page_with_unreadable_rotated_body_requires_review(self):
        rotated = self.root / "Slide.pdf"
        make_pdf(rotated, [["Slide 1"]], rotated_text=True)
        note = self.root / self.command("prepare", rotated)["note"]
        page = self.command("pages", note)["pages"]["1"]
        self.assertIn("issue", page)
        self.save(note, {"1": ["第 1 页"]}, ok=False)
        self.assertEqual(self.save(note, {"1": page})["blocked"], [1])

    def test_save_preserves_changes_made_after_the_note_was_read(self):
        spec = importlib.util.spec_from_file_location("study", CLI)
        study = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(study)
        result = self.command("prepare", self.pdf)
        draft = self.root / "translations.json"
        draft.write_text('{"2":["主元可以确定一个变量。"]}', encoding="utf-8")
        previous_dir = Path.cwd()
        os.chdir(self.root)
        try:
            note, snapshot = study.load_note(Path(result["note"]))
            edited = snapshot + "\n- 输入期间保存的复习问题\n"
            note.write_text(edited, encoding="utf-8")
            with self.assertRaises(ValueError):
                study.save(note, snapshot, draft)
            self.assertEqual(note.read_text(encoding="utf-8"), edited)
        finally:
            os.chdir(previous_dir)

    def test_identical_content_uses_one_note_and_can_be_assigned_later(self):
        first = self.command("prepare", self.pdf)
        copy = self.root / "A new filename.pdf"
        shutil.copyfile(self.pdf, copy)
        next_result = self.command("prepare", copy, "--course", "线性代数")
        self.assertEqual(first["note"], next_result["note"])
        note = self.root / first["note"]
        self.assertIn("线性代数", note.read_text(encoding="utf-8"))
        self.assertEqual(self.command("prepare", self.pdf)["course"], next_result["course"])

    def test_different_content_with_same_name_has_separate_notes(self):
        different_folder = self.root / "other"
        different_folder.mkdir()
        different_pdf = different_folder / self.pdf.name
        make_pdf(different_pdf, [["Different lecture."]])
        original = self.command("prepare", self.pdf)
        other = self.command("prepare", different_pdf)
        self.assertNotEqual(original["note"], other["note"])
        self.assertEqual((self.root / other["source"]).read_bytes(), different_pdf.read_bytes())


if __name__ == "__main__":
    unittest.main()
