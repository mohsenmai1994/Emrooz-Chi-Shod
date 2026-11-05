"""Run one news check and optionally publish one post. No internal scheduler."""

import argparse
import sys
import time
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

from bale import format_post, send_post
from config import FEEDS, get_settings
from feeds import fetch_article_details, fetch_feed, fingerprint_keys, is_economic, summarize_news
from state import load_history, save_history


def run_once(settings):
    """Publish at most one fresh, previously unpublished story per invocation."""
    now = datetime.now(timezone.utc)
    history = load_history()
    items = []
    feed_successes = 0

    for source, url in FEEDS.items():
        try:
            feed_items = fetch_feed(source, url)
            feed_successes += 1
            items.extend(feed_items)
            print(f"[RSS] {source}: {len(feed_items)} items")
        except (urllib.error.URLError, TimeoutError, ET.ParseError, OSError, ValueError) as exc:
            print(f"[WARN] {source}: {type(exc).__name__}: {exc}")

    # Treat a full feed outage as a run failure rather than a successful empty check.
    if feed_successes == 0:
        raise RuntimeError("All RSS feeds failed")

    candidates = []
    for item in items:
        age = now - item["published"]
        if not -timedelta(minutes=10) <= age <= timedelta(hours=settings["max_age_hours"]):
            continue
        if settings["economy_only"] and not is_economic(item):
            continue
        if any(key in history for key in fingerprint_keys(item)):
            continue
        candidates.append(item)

    if not candidates:
        print("[INFO] No new eligible news; nothing sent.")
        return None

    # One story at most, even if RSS feeds contain hundreds of articles.
    selected = max(candidates, key=lambda item: item["published"])

    # Fetch the selected article only (never all RSS entries). This supplies a
    # complete lead when the RSS description ends in the middle of a sentence.
    rss_summary = summarize_news(selected["summary"])
    try:
        details = fetch_article_details(selected["link"])
        selected["summary"] = details["summary"] or rss_summary
        selected["photo"] = selected["photo"] or details["photo"]
    except (urllib.error.URLError, TimeoutError, OSError, UnicodeError, ValueError) as exc:
        print(f"[WARN] Article details unavailable: {type(exc).__name__}")
        # A missing complete summary is safer than publishing a broken phrase.
        selected["summary"] = rss_summary

    if settings["preview"]:
        print("[PREVIEW] No message was sent.\n")
        print(format_post(selected))
        print("\n[IMAGE]", selected["photo"] or "No image found")
        return selected

    # Never mark an item as posted unless the Bale API confirms delivery.
    result = send_post(settings["bot_token"], settings["channel"], selected)
    for key in fingerprint_keys(selected):
        history[key] = time.time()
    save_history(history)
    print(f"[SENT] {result}: {selected['source']} / {selected['title']}")
    return selected


def main():
    parser = argparse.ArgumentParser(description="Run a single Bale RSS news check.")
    parser.add_argument("--preview", action="store_true", help="Preview one news item without publishing")
    args = parser.parse_args()
    settings = get_settings(preview=args.preview)
    run_once(settings)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
