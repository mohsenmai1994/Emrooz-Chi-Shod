"""RSS sources and deployment settings; keep credentials in GitHub secrets."""

import os

FEEDS = {
    "مهر": "https://www.mehrnews.com/rss/tp/25",
    "ایسنا": "https://www.isna.ir/rss",
    "ایرنا": "https://www.irna.ir/rss",
    "باشگاه خبرنگاران": "https://www.yjc.ir/fa/rss/allnews",
}

# Kept for compatibility with feeds.py's is_economic().
ECONOMIC_WORDS = (
    "اقتصاد", "تورم", "دلار", "ارز", "طلا", "سکه", "بورس", "بانک", "وام",
    "تسهیلات", "مسکن", "اجاره", "حقوق", "دستمزد", "یارانه", "کالابرگ",
    "خودرو", "بنزین", "مالیات", "بودجه", "بیمه", "بازنشسته", "قیمت",
    "بازار", "تجارت", "صادرات", "واردات", "انرژی", "نفت", "گاز",
    "معیشت", "گمرک", "سپرده", "اقساط", "درآمد", "افزایش نرخ",
)


def get_settings(preview=False):
    token = os.getenv("BALE_BOT_TOKEN", "").strip()
    channel = os.getenv("BALE_CHANNEL", "").strip()
    if not preview and (not token or not channel.startswith("@")):
        raise ValueError("Set BALE_BOT_TOKEN and BALE_CHANNEL (@username) in GitHub settings.")
    try:
        max_age = float(os.getenv("MAX_AGE_HOURS", "3"))
    except ValueError as exc:
        raise ValueError("MAX_AGE_HOURS must be a number") from exc
    if max_age <= 0:
        raise ValueError("MAX_AGE_HOURS must be positive")
    return {
        "bot_token": token,
        "channel": channel,
        "max_age_hours": max_age,
        "preview": preview,
    }
