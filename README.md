这是一个根据网址生成电子书的项目。

## 需求摘要

| 项 | 说明 |
|----|------|
| 格式 | EPUB 3（NCX + 嵌套系统目录，无独立 toc.xhtml） |
| 站点 | https://buffett.ayaseeri.com/ |
| 目录 | 侧栏 `cat-menu` 二级：summary → 链接文字 |
| 听书 | 侧栏每条链接 = 1 个 spine 章节 + 章首 `h1` |
| 正文 | 仅 `main/article` 内 `section.qa-movement`（不抓页面 `aside[2]` 侧栏）；剔除章内 `nav` 目录镜像与「本章目录」；正文内链接去除 |
| 标题 | 侧栏目录名与页头标题合并（不一致时为「目录名：页头标题」） |

## 安装

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## 使用

**默认测试包（全目录 + 每个侧栏大分组 1 篇正文）：**

```bash
python -m website2ebooks --sample-per-section --output dist/test-2ch.epub
```

**快速 smoke（仅前 2 篇正文）：**

```bash
python -m website2ebooks --content-limit 2 --output dist/test-2ch.epub
```

**全书正文：**

```bash
python -m website2ebooks --all --output dist/buffett-wenda-lu.epub --delay 0.5
```

阅读器内使用 **系统目录**（嵌套分组）；听书按目录叶子章节切换。章末「上一章/下一章/编者过桥」等已剔除。

**掌阅 iReader**：若字号仍异常，请在阅读设置中开启「跟随书籍排版 / 原书样式」，以便加载 EPUB 内嵌 CSS。

## 测试

```bash
pytest
```

## 项目结构

- `nav.py` — 侧栏解析
- `toc_page.py` — 嵌套 `book.toc` 分组
- `article.py` — 正文去噪
- `epub_export.py` — EPUB 打包
