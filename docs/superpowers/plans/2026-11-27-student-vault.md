# 学生双语课程知识库 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 从 Obsidian 课程页点开课件即可逐段读中英对照，并回查原 PDF。
**Architecture:** Markdown 是阅读笔记和学习记录的存储。Python 命令负责 PDF 归档、抽取、页面状态与安全写入。Codex 按工作流提供中文译文，Obsidian Bases 从笔记属性生成索引。
**Tech Stack:** Obsidian 核心 Bases、Python 3.10+、pypdf、unittest。
**Spec:** docs/superpowers/specs/2026-11-27-student-vault-design.md

## Global Constraints

- 支持带可提取文字的 PDF，原件保留，可见的错误指向原文件页。
- 全文按原文顺序逐段中英对照，可恢复，保留人工改动。
- 默认只有虚构示例、模板与工具可进入公共仓库。
- Codex 由用户主动调用，核心阅读流程无需社区插件。

## Review Focus

- 同名异件、异名同件和中途重复运行。
- 页码及分段匹配、空白扫描页和部分结果。
- 引用/Markdown 结构、文件名特殊字符和用户手写内容。
- 无课程归属、有课程后补归类。
- 样例在全新副本中可用，真实资料路径在 Git 中被忽略。

## Task 1 — 局部可重试的导入和翻译

**Files:** `tools/study.py`、`tools/requirements.txt`、`tests/test_study.py`。
**Interfaces:** 从 vault 根运行 `init`、`prepare PDF [--course NAME]`、`pages NOTE [--from N] [--to N]`、`save NOTE TRANSLATIONS.json`、`status NOTE`。每页有 1 起计的页码与段落数组。译文是页码到中文段落数组的 JSON 对象。
- [x] 先写命令级测试，覆盖空白页、准确英中顺序、原件留存、同件重复、同名异件、后补归类和人工文字保留。
- [x] 运行 `python -m unittest discover -s tests -v`，确认因入口缺失失败。
- [x] 实现以 PDF SHA-256 定位资料目录、原件与阅读笔记，原件可回链到物理页。单次保存先校验所有译文数组长度，再只替换本次可写的占位并原子落盘。
- [x] 运行命令级测试，核对新导入和恢复两种路径可用。

## Task 2 — 课程入口与示例

**Files:** `开始.md`、`基础视图/*.base`、`示例/*`、`AGENTS.md`、`README.md`、`.gitignore`、`LICENSE`。
**Interfaces:** Bases 按内部课程链接筛选资料，默认在课程页展示双语笔记和翻译状态。真实文件全部置于 `我的学习/`。
- [x] 写好课程和资料索引、开始页、中文 Codex 操作指引和清晰的使用步骤。
- [x] 用原创的多页英文课件走实际工作流，生成并校对伴随的中文阅读笔记及对应页码。
- [x] 检查 Git 忽略、所有 vault 链接、示例 PDF 和开源许可。验证公开提交包含模板和示例。

## Task 3 — 发布

- [ ] 运行测试并检查最终提交的文件列表。
- [ ] 发布到 GitHub，启用模板设置并验证匿名打开与默认分支；若需要 GitHub 授权，移交用户登录后继续。
