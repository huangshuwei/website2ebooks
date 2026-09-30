这是一个根据网址生成电子书的项目。

## 需求摘要

| 项 | 说明 |
|----|------|
| 格式 | EPUB 3（含 NCX，兼容掌阅目录） |
| 站点 | https://buffett.ayaseeri.com/ |
| 目录 DOM | `/html/body/div[2]/aside/nav` 内 `ul.cat-menu`（专题 / 原文 / 解读 全侧栏链接） |
| 正文 DOM | `/html/body/div[2]/main/article` |
| 排除正文 | `//*[@id="article-content"]/section/section/footer` |
| 正文链接 | 导出时去除（保留文字） |

## 安装

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## 使用

**默认（全目录 + 仅前 2 篇正文，其余为占位页）：**

```bash
python -m website2ebooks --output dist/test-2ch.epub
```

**导出全书正文：**

```bash
python -m website2ebooks --all --output dist/buffett-wenda-lu.epub --delay 0.5
```

或 `--content-limit 0`。侧栏解析约 **470+** 条目录；全书抓取耗时较长。

常用参数：

- `--content-limit N`：抓取前 N 篇完整正文（默认 `2`）
- `--delay 0.5`：请求间隔（秒）
- `--book-url`：用于解析侧栏 nav 的页面 URL
- `-v`：调试日志

## 验收建议

1. 微信读书 / 掌阅导入 EPUB，检查目录条目数量与侧栏一致。
2. 默认包：前 2 章有正文，其余章节打开为试读占位说明。
3. 正文中不应出现可点击超链接。

## 测试

```bash
pytest
```

`tests/fixtures/nav_index.html` 为侧栏快照，用于离线校验目录解析数量。

## 项目结构

- `src/website2ebooks/nav.py` — 侧栏 cat-menu 目录解析
- `src/website2ebooks/article.py` — 正文、图片、去链接
- `src/website2ebooks/epub_export.py` — EPUB 扁平 TOC + NCX
- `src/website2ebooks/cli.py` — 命令行入口
