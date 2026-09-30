这是一个根据网址生成电子书的项目。

## 需求摘要

| 项 | 说明 |
|----|------|
| 格式 | EPUB 3 |
| 站点 | https://buffett.ayaseeri.com/ |
| 目录 DOM | `/html/body/div[2]/aside/nav`（失败时 fallback `//aside/nav`） |
| 正文 DOM | `/html/body/div[2]/main/article` |
| 排除正文 | `//*[@id="article-content"]/section/section/footer` |
| 排除链接 | 书目索引 URL；凡 href 含 `#` 的目录链接 |

## 安装

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## 使用

**测试（README 3.1：先导出 2 章）：**

```bash
python -m website2ebooks --limit 2 --output dist/test-2ch.epub
```

**导出全书（去掉 `--limit`）：**

侧栏 nav 当前解析为 **10** 个章节合集（以站点 nav 为准；首页正文里的年份问答链含 `#` 锚点，按需求不单独导出）。

```bash
python -m website2ebooks --output dist/buffett-wenda-lu.epub --delay 0.5
```

常用参数：

- `--delay 0.5`：请求间隔（秒），减轻对站点压力
- `--book-url`：用于解析侧栏 nav 的书目页 URL
- `-v`：调试日志

## 测试

```bash
pytest
```

## 项目结构

- `src/website2ebooks/nav.py` — 目录解析与链接过滤
- `src/website2ebooks/article.py` — 正文、图片、链接处理
- `src/website2ebooks/epub_export.py` — EPUB 打包
- `src/website2ebooks/cli.py` — 命令行入口
