"""RSS sources and deployment settings; secrets are read from environment variables."""

import os

FEEDS = {
    "مهر": "https://www.mehrnews.com/rss/tp/25",
    "ایسنا": "https://www.isna.ir/rss",
    "ایرنا": "https://www.irna.ir/rss",
    "باشگاه خبرنگاران": "https://www.yjc.ir/fa/rss/allnews",
}

ECONOMIC_WORDS = (
    "اقتصاد", "تورم", "دلار", "ارز", "طلا", "سکه", "بورس", "بانک", "وام",
    "تسهیلات", "مسکن", "اجاره", "حقوق", "دستمزد", "یارانه", "کالابرگ",
    "خودرو", "بنزین", "مالیات", "بودجه", "بیمه", "بازنشسته", "قیمت",
    "بازار", "تجارت", "صادرات", "واردات", "انرژی", "نفت", "گاز",
    "معیشت", "گمرک", "سپرده", "اقساط", "درآمد", "افزایش نرخ",
)


def get_settings(preview=False):
    """Read secrets only for real delivery, never from committed source files."""
    token = os.getenv("BALE_BOT_TOKEN", "").strip()
    channel = os.getenv("BALE_CHANNEL", "").strip()

    if not preview and (not token or not channel.startswith("@")):
        raise ValueError("Set BALE_BOT_TOKEN and BALE_CHANNEL (@channel_username) in GitHub settings.")

    try:
        max_age = float(os.getenv("MAX_AGE_HOURS", "3"))
    except ValueError as exc:
        raise ValueError("MAX_AGE_HOURS must be a number") from exc
    if max_age <= 0:
        raise ValueError("MAX_AGE_HOURS must be positive")

    economy_only = os.getenv("ECONOMY_ONLY", "true").lower() not in ("false", "0", "no")
    return {
        "bot_token": token,
        "channel": channel,
        "max_age_hours": max_age,
        "economy_only": economy_only,
        "preview": preview,
    }
