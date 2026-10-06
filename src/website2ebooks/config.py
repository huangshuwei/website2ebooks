from __future__ import annotations

BOOK_INDEX_URL = "https://buffett.ayaseeri.com/books/buffett-wenda-lu/"
BOOK_PATH_PREFIX = "/books/buffett-wenda-lu/"

NAV_XPATH = "/html/body/div[2]/aside/nav"
NAV_XPATH_FALLBACK = "//aside/nav"

ARTICLE_XPATH = "/html/body/div[2]/main/article"
ARTICLE_XPATH_FALLBACK = "//main/article"

FOOTER_XPATH = '//*[@id="article-content"]/section/section/footer'

# buffett.ayaseeri.com 合集页正文内的「本章目录」
IN_CHAPTER_TOC_XPATH = ".//details[contains(@class,'qa-mobile-toc')]"
# article 内真正问答正文（非页面 aside[2] 侧栏）
ARTICLE_BODY_SECTIONS_XPATH = ".//section[contains(@class,'qa-movement')]"
# 页级本章问答侧栏（不抓取，仅文档/调试）
PAGE_CHAPTER_SIDEBAR_XPATH = "/html/body/div[2]/aside[contains(@class,'col-right')]"
CHAPTER_NAV_IN_ARTICLE_XPATH = ".//nav[contains(@class,'qa-chapter-nav')]"
CHAPTER_CLOSING_ASIDE_XPATH = ".//aside[contains(@class,'qa-chapter-closing')]"

EXCLUDED_CHAPTER_URLS = frozenset(
    {
        "https://buffett.ayaseeri.com/books/buffett-wenda-lu/",
    }
)

BOOK_TITLE = "巴菲特问答录"
STRIP_LINKS = True

STUB_CHAPTER_MESSAGE = (
    "（试读版：本章正文未导出，完整版请使用 --all 或 --content-limit 0。）"
)


def stub_fetch_failed_message(*, attempts: int, error: str) -> str:
    return f"（本章抓取失败，已重试 {attempts} 次。错误：{error}）"
DEFAULT_USER_AGENT = (
    "website2ebooks/0.1 (+https://github.com/local/website2ebooks; respectful crawler)"
)

DEFAULT_CSS = """
/* 正文 1em；标题 1.25em（大两号）。字号 !important 兼容掌阅等阅读器 */
body {
  font-family: serif;
  line-height: 1.6;
  margin: 1em;
  text-align: left;
  font-size: 1em;
}
p {
  text-align: left;
  margin: 0.5em 0;
}
p, li, dd, dt, td, th, blockquote, figcaption,
.text-muted, .qa-source-question p, .qa-answer p {
  font-size: 1em !important;
}
h1.chapter-title, .chapter-title, .w2e-heading {
  line-height: 1.3;
  text-align: left;
  font-weight: bold;
  font-size: 1.25em !important;
  margin: 0.75em 0 0.35em 0;
}
h1.chapter-title, .chapter-title {
  margin: 0 0 0.5em 0;
}
.text-muted {
  color: #666;
  margin-bottom: 0.75em;
}
img { max-width: 100%; height: auto; }
a { color: inherit; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #ccc; padding: 0.25em 0.5em; }
blockquote { margin-left: 1em; opacity: 0.95; }
"""

ARTICLE_CHROME_PATTERNS: tuple[str, ...] = (
    r"^巴菲特问答录\s*$",
    r"^第\s*[0-9一二三四五六七八九十]+\s*[篇章节部分]\s*[·\.]?\s*",
    r"^\d+\s*问\s*$",
)

ARTICLE_TAIL_PATTERNS: tuple[str, ...] = (
    r"上一章|下一章|上一篇|下一篇",
    r"编者过桥",
    r"^编者导读\s*$",
)
