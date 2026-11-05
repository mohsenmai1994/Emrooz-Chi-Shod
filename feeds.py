"""Collect and normalize recent RSS/Atom news with optional article images."""

import hashlib
import html
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit

from config import ECONOMIC_WORDS

TIMEOUT = 15
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; EmroozNewsBot/1.0; RSS reader)",
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
}


class HTMLData(HTMLParser):
    """Extract plain text, the first inline image, and the Open Graph image."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.ignored = 0
        self.inline_image = ""
        self.og_image = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("script", "style"):
            self.ignored += 1
        if tag == "img" and not self.inline_image:
            self.inline_image = attrs.get("data-src") or attrs.get("src") or ""
        if tag == "meta":
            key = (attrs.get("property") or attrs.get("name") or "").lower()
            if key in ("og:image", "og:image:secure_url", "twitter:image") and not self.og_image:
                self.og_image = attrs.get("content") or ""

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.ignored:
            self.ignored -= 1

    def handle_data(self, data):
        if not self.ignored:
            self.parts.append(data)


def clean_html(value: str) -> str:
    parser = HTMLData()
    parser.feed(html.unescape(value or ""))
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def normalized(value: str) -> str:
    value = (value or "").translate(str.maketrans({"ي": "ی", "ك": "ک", "‌": " "}))
    return re.sub(r"\W+", " ", value.casefold()).strip()


def get_child(item, *names):
    for node in item:
        if node.tag.rsplit("}", 1)[-1].lower() in names:
            if node.text and node.text.strip():
                return node.text.strip()
    return ""


def parse_time(value):
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def valid_url(url, base=""):
    url = urljoin(base, html.unescape(url or "").strip())
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return ""
    return url


def extract_image(item, article_url):
    # RSS media:content / media:thumbnail / enclosure are preferred.
    for preferred in ("content", "enclosure", "thumbnail", "image"):
        for node in item.iter():
            if node.tag.rsplit("}", 1)[-1].lower() != preferred:
                continue
            media_type = (node.attrib.get("type") or "").lower()
            medium = (node.attrib.get("medium") or "").lower()
            if (media_type and not media_type.startswith("image/")) or (medium and medium != "image"):
                continue
            raw = node.attrib.get("url") or node.attrib.get("href")
            if preferred == "image" and not raw:
                raw = node.text
            if raw and valid_url(raw, article_url):
                return valid_url(raw, article_url)

    for node in item.iter():
        if node.tag.rsplit("}", 1)[-1].lower() in ("description", "summary", "encoded") and node.text:
            parser = HTMLData()
            parser.feed(html.unescape(node.text))
            image = valid_url(parser.inline_image, article_url) if parser.inline_image else ""
            if image:
                return image
    return ""


def fetch_feed(source, url):
    """Read at most 80 entries. Skip articles without reliable timestamps."""
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        data = response.read(3_000_001)
    if len(data) > 3_000_000:
        raise ValueError("RSS response is larger than 3 MB")
    root = ET.fromstring(data)
    items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    result = []
    for item in items[:80]:
        title = clean_html(get_child(item, "title"))
        summary = clean_html(get_child(item, "description", "summary", "content", "encoded"))
        published = parse_time(get_child(item, "pubdate", "published", "updated", "date"))
        raw_link = get_child(item, "link")
        if not raw_link:
            for node in item:
                if node.tag.rsplit("}", 1)[-1].lower() == "link" and node.attrib.get("href"):
                    raw_link = node.attrib["href"]
                    break
        link = valid_url(raw_link)
        if not (title and published and link):
            continue
        result.append({
            "title": title,
            "summary": summary,
            "published": published,
            "source": source,
            "link": link,
            "photo": extract_image(item, link),
        })
    return result


def discover_article_image(article_url):
    """Try the selected article's og:image only if its RSS entry had no photo."""
    req = urllib.request.Request(article_url, headers={**HEADERS, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        snippet = response.read(500_000)
        charset = response.headers.get_content_charset() or "utf-8"
    parser = HTMLData()
    parser.feed(snippet.decode(charset, errors="replace"))
    return valid_url(parser.og_image, article_url) if parser.og_image else ""


def is_economic(article):
    title = normalized(article["title"])
    return any(normalized(word) in title for word in ECONOMIC_WORDS)


def fingerprint_keys(article):
    """Prevent duplicates based on both link and normalized headline."""
    parts = urlsplit(article["link"])
    link = urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "", ""))
    heading = normalized(article["title"])
    return [
        hashlib.sha256(("url:" + link).encode("utf-8")).hexdigest(),
        hashlib.sha256(("title:" + heading).encode("utf-8")).hexdigest(),
    ]


# Remove editorial datelines such as "Yazd - IRNA -" from article leads.
NEWS_AGENCIES = r"(?:ایرنا|ایسنا|خبرگزاری\s+مهر|مهر|باشگاه\s+خبرنگاران(?:\s+جوان)?)"
DATELINE_PATTERN = re.compile(
    rf"^\s*(?:[\u0600-\u06FF\u200c\s]{{2,42}}\s*[-–—ـ]\s*)?{NEWS_AGENCIES}\s*[-–—ـ:]\s*"
)
REPORTER_PATTERN = re.compile(
    rf"^\s*(?:به\s+گزارش\s+(?:(?:خبرنگار|گروه\s+خبری)\s+)?{NEWS_AGENCIES})\s*[,،:]?\s*"
)
SENTENCE_END_PATTERN = re.compile(r"[.!؟!]+(?=\s|$)")
ELLIPSIS_PATTERN = re.compile(r"…|\.\.\.")
ARTICLE_CONTENT_PATTERN = re.compile(
    r"(?:^|[\s_-])(?:item[-_ ]?text|item[-_ ]?summary|article[-_ ]?(?:body|content|text)|"
    r"news[-_ ]?(?:body|content|text|detail)|story[-_ ]?body|text[-_ ]?body|lead)(?:$|[\s_-])",
    re.IGNORECASE,
)


def clean_news_lead(value):
    """Remove news-agency datelines without changing the news itself."""
    text = clean_html(value)
    for pattern in (DATELINE_PATTERN, REPORTER_PATTERN):
        text = pattern.sub("", text, count=1)
    return text.strip()


def summarize_news(value, max_chars=480, max_sentences=2):
    """Return complete sentences, never a mid-word or mid-sentence cutoff.

    An RSS description ending with an ellipsis is treated as incomplete. The
    caller should fetch the selected article's page to obtain a proper lead.
    """
    text = clean_news_lead(value)
    if not text:
        return ""

    # Drop a publisher-truncated trailing fragment, retaining any full sentences.
    ellipsis = ELLIPSIS_PATTERN.search(text)
    if ellipsis:
        text = text[:ellipsis.start()].rstrip()

    ends = list(SENTENCE_END_PATTERN.finditer(text))
    if not ends:
        return ""

    output = ""
    for match in ends[:max_sentences]:
        candidate = text[:match.end()].strip()
        if len(candidate) > max_chars:
            break
        output = candidate
    return output


class ArticleHTML(HTMLParser):
    """Capture article-body paragraphs, social preview metadata and lead text."""

    VOID_TAGS = {"meta", "link", "img", "br", "hr", "input", "source", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.paragraphs = []
        self.description = ""
        self.photo = ""
        self._paragraph = None
        self._priority = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta":
            key = (attrs.get("property") or attrs.get("name") or "").lower()
            if key in ("og:description", "twitter:description", "description") and not self.description:
                self.description = attrs.get("content", "")
            if key in ("og:image", "og:image:secure_url", "twitter:image") and not self.photo:
                self.photo = attrs.get("content", "")

        if tag == "p":
            self._paragraph = []
            parents = self.stack
            if any(t == "article" for t, _ in parents):
                self._priority = 2
            elif any(ARTICLE_CONTENT_PATTERN.search(css) for _, css in parents):
                self._priority = 1
            else:
                self._priority = 0

        if tag not in self.VOID_TAGS:
            self.stack.append((tag, attrs.get("class", "")))

    def handle_data(self, data):
        if self._paragraph is not None and not any(t in ("script", "style") for t, _ in self.stack):
            self._paragraph.append(data)

    def handle_endtag(self, tag):
        if tag == "p" and self._paragraph is not None:
            value = re.sub(r"\s+", " ", " ".join(self._paragraph)).strip()
            if len(value) >= 60:
                self.paragraphs.append((self._priority, value))
            self._paragraph = None
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break


def fetch_article_details(article_url):
    """Read only the chosen article page for a complete lead and optional image."""
    req = urllib.request.Request(article_url, headers={**HEADERS, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        content = response.read(900_000)
        charset = response.headers.get_content_charset() or "utf-8"
    parser = ArticleHTML()
    parser.feed(content.decode(charset, errors="replace"))

    # A short article-body extract is better than the commonly truncated RSS lead.
    full_summary = ""
    for priority in (2, 1):
        matches = [text for score, text in parser.paragraphs if score == priority]
        for text in matches[:4]:
            full_summary = summarize_news(text)
            if full_summary:
                break
        if full_summary:
            break
    if not full_summary:
        full_summary = summarize_news(parser.description)

    return {
        "summary": full_summary,
        "photo": valid_url(parser.photo, article_url) if parser.photo else "",
    }
