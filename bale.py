"""Compact Bale news messages and Bale Bot API delivery."""

import json
import re
import urllib.error
import urllib.request

from feeds import normalized, summarize_news
from news_rules import topic_tags

API_ROOT = "https://tapi.bale.ai/bot"
CHANNEL_HANDLE = "@emroozchishod"


class BaleAPIError(Exception):
    def __init__(self, code, description):
        super().__init__(f"Bale error {code}: {description}")
        self.code = code


def _safe_markdown(s):
    return re.sub(r"[*_`\[\]]", "", s or "").strip()


def format_post(article):
    """No repeated title, at most two hashtags, channel handle as final line."""
    title = _safe_markdown(article["title"])
    summary = _safe_markdown(summarize_news(article.get("summary", "")))
    if summary and (normalized(summary) == normalized(title) or
                    normalized(summary).startswith(normalized(title))):
        summary = ""

    source = _safe_markdown(article.get("source", "خبرگزاری"))
    link = article["link"]
    tags = topic_tags(article)

    lines = [f"📰 *{title}*"]
    if summary:
        lines += ["", f"{summary}"]
    lines += ["", f"🔗 [منبع: {source}]({link})", " ".join(tags), CHANNEL_HANDLE]
    return "\n".join(lines)


def _api(token, method, fields):
    payload = json.dumps(fields, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{API_ROOT}{token}/{method}",
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.loads(response.read(300_000).decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            error = json.loads(exc.read().decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            error = {}
        raise BaleAPIError(error.get("error_code", exc.code), error.get("description", "Request rejected")) from None
    except (urllib.error.URLError, TimeoutError):
        # Avoid resending after ambiguous network failures: the message may have arrived.
        raise RuntimeError("Bale request failed; delivery status is unknown") from None
    if not isinstance(result, dict) or not result.get("ok"):
        if not isinstance(result, dict):
            raise BaleAPIError("unknown", "Unexpected API response")
        raise BaleAPIError(result.get("error_code", "unknown"), result.get("description", "Request rejected"))
    return result.get("result")


def send_post(token, channel, article):
    text = format_post(article)
    if article.get("photo"):
        try:
            _api(token, "sendPhoto", {"chat_id": channel, "photo": article["photo"], "caption": text})
            return "photo"
        except BaleAPIError as exc:
            if exc.code not in (400, "400"):
                raise
            print("[WARN] Bale rejected photo; retrying as text.")
    _api(token, "sendMessage", {"chat_id": channel, "text": text})
    return "text"
