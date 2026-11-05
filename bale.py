"""Format short news posts and publish them with the official Bale Bot API."""

import json
import re
import urllib.error
import urllib.request

from feeds import normalized, summarize_news

API_ROOT = "https://tapi.bale.ai/bot"


class BaleAPIError(Exception):
    def __init__(self, code, description):
        super().__init__(f"Bale error {code}: {description}")
        self.code = code


def format_post(article):
    """Render one compact post; avoid visual separators and raw long URLs."""
    title = re.sub(r"[*_`\[\]]", "", article["title"]).strip()
    summary = re.sub(r"[*_`\[\]]", "", summarize_news(article["summary"]))
    if normalized(summary) == normalized(title):
        summary = ""
    source = article["source"]
    lines = [f"📡 *{title}*"]
    if summary:
        lines += ["", f"🔹 {summary}"]
    lines += ["", f"📍 منبع: {source}", f"🔗 [مشاهده خبر کامل]({article['link']})"]
    return "\n".join(lines)


def _api(token, method, fields):
    """Use HTTPS + JSON and require Bale's explicit 'ok' response."""
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
    except (urllib.error.URLError, TimeoutError) as exc:
        # Do not send another message on ambiguous network failures: it may duplicate a post.
        raise RuntimeError("Bale request failed; delivery status is unknown") from None
    if not isinstance(result, dict) or not result.get("ok"):
        raise BaleAPIError(result.get("error_code", "unknown"), result.get("description", "Request rejected"))
    return result.get("result")


def send_post(token, channel, article):
    """Try a single image+caption post, falling back to text only on an explicit 400."""
    text = format_post(article)
    if article.get("photo"):
        try:
            _api(token, "sendPhoto", {"chat_id": channel, "photo": article["photo"], "caption": text})
            return "photo"
        except BaleAPIError as exc:
            if exc.code not in (400, "400"):
                raise
            # HTTP 400 typically indicates an unusable image URL or invalid image data.
            print("[WARN] Bale rejected the image; retrying as text.")
    _api(token, "sendMessage", {"chat_id": channel, "text": text})
    return "text"
