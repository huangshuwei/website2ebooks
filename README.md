这是一个根据网址生成电子书的项目。

## 需求摘要

| 项 | 说明 |
|----|------|
| 格式 | EPUB 3（NCX + 嵌套系统目录，无独立 toc.xhtml） |
| 站点 | [buffett.ayaseeri.com](https://buffett.ayaseeri.com/) · [munger.ayaseeri.com](https://munger.ayaseeri.com/) |
| 听书 | 侧栏每条链接 = 1 个 spine 章节 + 章首 `h1` |
| 标题 | 侧栏目录名与页头标题合并（不一致时为「目录名：页头标题」） |

### 巴菲特（`--site buffett`，默认）

| 项 | 说明 |
|----|------|
| 入口 | `/books/buffett-wenda-lu/` |
| 目录 | 侧栏 `cat-menu`：`summary` → 链接文字 |
| 正文 | `main/article` 内 `section.qa-movement`；剔除章内目录镜像与「本章目录」；正文内链接去除 |

### 芒格（`--site munger`）

| 项 | 说明 |
|----|------|
| 入口 | 首页侧栏 `archive-sidebar`（原文 + 解读 + 其他） |
| 目录 | `sidebar-section` → `sidebar-group-label` → 链接；EPUB 一级分组为「原文 / 解读」 |
| 原文/解读 | `article.reader-layout` → `div.article-body` |
| 芒格问答录 | 侧栏「芒格问答录」展开为 [`/books/munger-qa/reader`](https://munger.ayaseeri.com/books/munger-qa/reader) 内 12 章（单页抓取后按 `#chapter-…` 切片） |

## 安装

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## 使用

**巴菲特 — 快速 smoke（仅前 2 篇正文）：**

```bash
python -m website2ebooks --content-limit 2 --output dist/buffett-test-2ch.epub
```

**芒格整站 — 快速 smoke（仅前 2 篇正文）：**

```bash
python -m website2ebooks --site munger --content-limit 2 -o dist/munger-test-2ch.epub
```

**巴菲特 — 默认测试包（全目录 + 每个侧栏大分组 1 篇正文）：**

```bash
python -m website2ebooks --sample-per-section --output dist/test-2ch.epub
```

**巴菲特 — 全书正文（串行抓取、章间成功等待 5 秒、失败重试 3 次）：**

```bash
python -m website2ebooks --all --output dist/buffett-wenda-lu.epub --delay 0.5 --chapter-success-delay 5 --max-retries 3
```

**芒格 — 全书正文：**

```bash
python -m website2ebooks --site munger --all -o dist/munger-knowledge-base.epub --delay 0.5 --chapter-success-delay 5 --max-retries 3
```

完成后会生成 `<output-stem>-fetch-report.txt`（成功/失败章节汇总）。仍有失败时 EPUB 会写出，但失败章为占位页，进程退出码为 1。

阅读器内使用 **系统目录**（嵌套分组）；听书按目录叶子章节切换。

**掌阅 iReader**：若字号仍异常，请在阅读设置中开启「跟随书籍排版 / 原书样式」，以便加载 EPUB 内嵌 CSS。

## 测试

```bash
pytest
```

## 项目结构

- `sites/` — 站点预设（`buffett` / `munger`）
- `nav.py` — 巴菲特侧栏解析
- `munger_nav.py` / `munger_article.py` — 芒格目录与正文
- `toc_page.py` — 嵌套 `book.toc` 分组
- `article.py` — 巴菲特问答正文去噪
- `epub_export.py` — EPUB 打包
