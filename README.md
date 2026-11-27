# 学生双语课程知识库

用 **Obsidian** 按课程找资料，用 **Codex** 整理英文课件。打开课程页里的课件即可逐段读英文和中文，每页都能回到原 PDF。

## 先看示例

1. 下载或克隆仓库，在 Obsidian 选择「打开本地仓库」，选这个文件夹。
2. 在「设置 → 核心插件」开启 **Bases**（中文界面可能显示为「数据库」）。
3. 打开 **开始**，选择 **线性代数（示例）**，再点表格中的 **Lecture 03 - Linear Systems**。

示例的双语笔记已经生成。在 Obsidian 中浏览示例和已生成笔记只需要 Obsidian。 [GitHub 上预览双语文本](./示例/Lecture%2003%20-%20Linear%20Systems（中英对照）.md)

## 整理第一份课件

在 Codex 中打开同一个项目文件夹。将一份可以选中文字的英文 PDF 放到 `我的学习/收件箱/`。如果还没有这个目录，请新建它或请 Codex 初始化。

可以把这句话发给 Codex。

> 请按 AGENTS.md 把收件箱里的 Lecture 03.pdf 归到「线性代数」，生成完整的逐段中英对照笔记，并告诉我有没有需要回查的页。

回到 Obsidian 打开 **开始 → 线性代数 → 资料标题**。英文段落在上，中文紧随其后。点「打开原 PDF 第 N 页」核对公式或图表。你可以在笔记末尾记录自己的疑问。

- 课程暂时不明确时，从 **待归类** 打开笔记。
- 翻译中断后，告诉 Codex 继续同一份资料。它可以从未处理的页面继续，并保留你修改过的段落。
- 首版支持有文字层的 PDF。PPT 可以先导出为文字可选的 PDF。遇到扫描、复杂分栏或提取异常的页，阅读笔记会保留页码和「需核对」提示。

## 第一次运行整理工具

需要 Python 3.10 或更新版本、`pypdf` 和已登录的 Codex。模板没有独立的翻译 API 配置。依赖可安装在项目的虚拟环境中。

**Windows PowerShell**

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r tools/requirements.txt
.\.venv\Scripts\python.exe tools/study.py init
```

**macOS / Linux**

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r tools/requirements.txt
.venv/bin/python tools/study.py init
```

打开同一目录的 Codex 可以代为执行这些步骤。Python 工具负责原件留存、提取、页码和安全写入。翻译由 Codex 生成。

## 个人材料和开源模板

课件、双语笔记、课程页和整理草稿都放在 `我的学习/`。新建笔记和粘贴的附件也默认保存到这里。Git 只记录这个目录里的空文件夹占位文件。公开的示例课件放在 `示例/`。 [MIT 许可](./LICENSE)

你可以从 GitHub 模板创建自己的副本，或者下载 ZIP 解压后直接作为 Obsidian 库使用。

## 参考

- 快速收集、用链接逐步组织知识。 [Steph Ango 的 Obsidian 用法](https://stephango.com/vault) · [第一篇小红书笔记](https://xhslink.cn/o/7pviSEr2yhO)
- 用首页展示笔记里已有的信息。 [紫玉的个人看板](https://github.com/ziyu-llm/obsidian-ai-dashboard) · [第二篇小红书视频](https://xhslink.cn/o/5787BZHVz09)
- 为 AI 写一份知识库工作说明。 [第三篇小红书视频](https://xhslink.cn/o/6t82pYdchZI)
