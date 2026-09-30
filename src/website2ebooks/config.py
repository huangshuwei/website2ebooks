from __future__ import annotations

BOOK_INDEX_URL = "https://buffett.ayaseeri.com/books/buffett-wenda-lu/"
BOOK_PATH_PREFIX = "/books/buffett-wenda-lu/"

NAV_XPATH = "/html/body/div[2]/aside/nav"
NAV_XPATH_FALLBACK = "//aside/nav"

ARTICLE_XPATH = "/html/body/div[2]/main/article"
ARTICLE_XPATH_FALLBACK = "//main/article"

FOOTER_XPATH = '//*[@id="article-content"]/section/section/footer'

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
DEFAULT_USER_AGENT = (
    "website2ebooks/0.1 (+https://github.com/local/website2ebooks; respectful crawler)"
)

DEFAULT_CSS = """
body {
  font-family: serif;
  line-height: 1.6;
  margin: 1em;
}
h1, h2, h3, h4 { line-height: 1.3; }
img { max-width: 100%; height: auto; }
a { color: inherit; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #ccc; padding: 0.25em 0.5em; }
blockquote { margin-left: 1em; opacity: 0.95; }
"""
