"""Emrooz Chi Shod — newsworthiness and topical hashtags.

Editorial scope: economy/markets and politics/war (including consequential world news).
Allowed tags (ONLY): #اقتصاد #دلار #طلا #بورس #بانک #مسکن #خودرو #سیاست #جنگ #جهان.
At most 2 relevant tags per published post. No daily quota or enforced post spacing.
"""

import re

ALLOWED_TAGS = (
    "#اقتصاد", "#دلار", "#طلا", "#بورس", "#بانک", "#مسکن", "#خودرو",
    "#سیاست", "#جنگ", "#جهان",
)

NORMALIZE_MAP = str.maketrans({
    "ي": "ی", "ك": "ک", "أ": "ا", "إ": "ا", "آ": "ا",
    "‌": " ", "ـ": "", "ۀ": "ه", "ة": "ه",
})


def norm(value):
    text = (value or "").translate(NORMALIZE_MAP).lower()
    text = re.sub(r"[^\w\s\u0600-\u06ff]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def has(text, phrase):
    """Match whole normalized phrase; avoid e.g. 'وام' in unrelated words."""
    phrase = norm(phrase)
    return bool(phrase and f" {phrase} " in f" {text} ")


def matches(text, terms):
    return any(has(text, term) for term in terms)


# These lists are for the *headline* so unrelated body/sidebar terms do not
# accidentally cause sports, celebrity, or general-interest stories to pass.
WAR = (
    "جنگ", "اتش بس", "حمله موشکی", "حملات موشکی", "حمله پهپادی",
    "حملات پهپادی", "حمله هوایی", "حملات هوایی", "حمله نظامی",
    "تهاجم نظامی", "درگیری نظامی", "درگیری مرزی", "شلیک موشک",
    "بمباران", "تبادل اتش", "عملیات نظامی", "نبرد", "پدافند هوایی",
    "حمله اسرائیل", "حمله امریکا", "حمله ایران", "حمله روسیه",
    "حمله اوکراین", "توقف درگیری", "تلفات جنگ", "تحرکات نظامی",
    "رهگیری موشک", "عملیات ارتش", "تهاجم", "حملات اسرائیل",
)
WAR_METAPHORS = (
    "جنگ با تورم", "جنگ با گرانی", "جنگ با فساد", "جنگ با قاچاق",
    "جنگ قیمت", "جنگ رسانه ای", "جنگ روانی", "جنگ اقتصادی",
    "جنگ نرم", "جنگ فرهنگی", "جنگ با بیماری", "جنگ با سرطان",
    "جنگ تجاری", "جنگ تعرفه ای", "جنگ تعرفه ها",
)

DOLLAR = (
    "دلار", "یورو", "نرخ ارز", "قیمت ارز", "بازار ارز", "ارز ازاد",
    "ارز دولتی", "نرخ حواله", "درهم", "پوند", "نرخ دلار", "قیمت دلار",
)
GOLD = ("طلا", "سکه", "اونس", "طلای جهانی", "انس جهانی", "قیمت سکه", "بهای طلا")
STOCKS = (
    "بورس", "فرابورس", "شاخص کل", "شاخص هم وزن", "سهام", "بازار سرمایه",
    "بورسی", "صف خرید", "صف فروش", "عرضه اولیه", "صندوق سرمایه گذاری",
)
BANK = (
    "بانک", "بانکی", "بانک مرکزی", "وام", "تسهیلات", "سپرده", "نرخ بهره",
    "نرخ سود", "سود سپرده", "چک بانکی", "نرخ سود بانکی", "بانکداری",
)
HOUSING = (
    "مسکن", "اجاره", "ودیعه", "بازار ملک", "بازار مسکن", "قیمت خانه",
    "ساخت و ساز مسکن", "نهضت ملی مسکن", "رهن", "قیمت آپارتمان", "قیمت اجاره",
)
CARS = (
    "خودرو", "ایران خودرو", "سایپا", "قیمت ماشین", "فروش خودرو",
    "ثبت نام خودرو", "پیش فروش خودرو", "بازار خودرو", "واردات خودرو",
    "قیمت خودرو", "خودروسازان", "تعرفه خودرو", "خودروسازی",
)
ECONOMY = (
    "اقتصاد", "اقتصادی", "تورم", "رکود", "معیشت", "یارانه", "کالابرگ",
    "مالیات", "بودجه", "کسری بودجه", "حقوق کارگران", "افزایش حقوق",
    "دستمزد", "حداقل دستمزد", "بازنشستگان", "حقوق بازنشستگان",
    "تامین اجتماعی", "بیمه بیکاری", "تجارت", "صادرات", "واردات",
    "گمرک", "تعرفه واردات", "تولید ناخالص", "خصوصی سازی",
    "سرمایه گذاری", "نفت", "گاز", "بنزین", "سوخت", "پتروشیمی",
    "تولید صنعتی", "تولید خودرو", "قیمت گذاری", "افزایش قیمت",
    "کاهش قیمت", "بازار کار", "اشتغال", "بیکاری", "تامین مالی",
    "ناترازی انرژی", "قیمت نفت", "بهای نفت", "قیمت بنزین",
    "قیمت مرغ", "قیمت گوشت", "قیمت برنج", "هزینه زندگی", "قدرت خرید",
    "بازار", "درآمد خانوار", "حقوق کارمندان",
)
POLITICS = (
    "سیاست", "سیاسی", "انتخابات ریاست جمهوری", "انتخابات مجلس",
    "نتایج انتخابات", "نتیجه انتخابات", "رئیس جمهور", "رییس جمهور",
    "نخست وزیر", "مجلس شورای اسلامی", "مجلس", "هیات دولت", "دولت",
    "دیپلماسی", "مذاکرات", "مذاکره", "توافق هسته ای", "برجام",
    "تحریم", "قطعنامه", "سازمان ملل", "شورای امنیت", "شورای نگهبان",
    "وزارت خارجه", "وزیر امور خارجه", "وزیر خارجه", "سفارت",
    "روابط ایران و", "روابط دیپلماتیک", "پارلمان", "استیضاح",
    "رای اعتماد", "سخنگوی دولت", "فرمان اجرایی", "ترامپ",
    "پزشکیان", "پوتین", "نتانیاهو", "رهبر انقلاب", "کاخ سفید",
    "کنگره امریکا", "دولت امریکا", "اتحادیه اروپا",
)
WORLD = (
    "امریکا", "ایالات متحده", "اروپا", "اتحادیه اروپا", "روسیه", "اوکراین",
    "اسرائیل", "غزه", "لبنان", "سوریه", "چین", "فرانسه", "انگلیس",
    "بریتانیا", "عراق", "ترکیه", "افغانستان", "پاکستان", "یمن",
    "کاخ سفید", "سازمان ملل", "شورای امنیت", "بین المللی", "خاورمیانه",
)

ROUTINE = (
    "دیدار و گفت و گو", "دیدار و گفتگو", "دیدار با", "بازدید از",
    "دیدار دوستانه", "تجلیل از", "قدردانی از", "پیام تبریک",
    "پیام تسلیت", "نشست صمیمانه", "نشست هم اندیشی", "همایش",
    "مراسم تقدیر", "گزارش تصویری", "حواشی", "تیتر روزنامه",
    "برگزاری جلسه", "برگزاری نشست", "اظهار امیدواری", "عکس های",
)
SIGNIFICANT = (
    "افزایش", "کاهش", "تصویب", "ابلاغ", "اجرا", "اجرایی", "لغو",
    "ممنوع", "اغاز", "توقف", "متوقف", "توافق", "تعلیق", "اعلام",
    "واریز", "پرداخت", "سقوط", "جهش", "رکورد", "تغییر", "رشد",
    "افت", "هشدار", "بحران", "نتیجه", "نرخ", "قیمت", "شاخص",
    "تحریم", "انتخابات", "استیضاح", "برکنار", "استعفا", "حمله",
    "بمباران", "شلیک", "درگیری", "اتش بس", "تلفات", "کشته",
    "مجروح", "جنگ", "قطعنامه", "مذاکرات", "مذاکره", "ورود",
    "خروج", "مصوبه", "ازادسازی", "عرضه", "تصمیم", "تعرفه",
    "افزایش یافت", "کاهش یافت", "رسید", "صعود", "نزول",
)
WEAK_ONLY = (
    "گفت", "تاکید کرد", "خواستار", "امیدواریم", "اظهار کرد",
    "به گفته", "در دیدار", "پیشنهاد کرد", "اظهار نظر",
)


def category(article):
    """Scope eligibility: economy/markets or consequential politics/war."""
    title = norm(article.get("title", ""))
    if not title:
        return None
    war = matches(title, WAR) and not matches(title, WAR_METAPHORS)
    economy = matches(title, ECONOMY)
    market = any(matches(title, terms) for terms in (DOLLAR, GOLD, STOCKS, BANK, HOUSING, CARS))
    politics = matches(title, POLITICS)

    if war:
        return "war"
    if market or economy:
        return "economy"
    if politics:
        return "politics"
    return None


def topic_tags(article, max_tags=2):
    """Choose 1–2 accurate hashtags strictly from the user-approved list."""
    title = norm(article.get("title", ""))
    subject = category(article)
    if not subject:
        return []

    if subject == "war":
        tags = ["#جنگ"]
        if matches(title, WORLD):
            tags.append("#جهان")
        elif matches(title, ECONOMY) or any(matches(title, t) for t in (DOLLAR, GOLD, STOCKS, BANK, HOUSING, CARS)):
            tags.append("#اقتصاد")
        elif matches(title, POLITICS):
            tags.append("#سیاست")
        return tags[:max(0, min(max_tags, 2))]

    if subject == "politics":
        tags = ["#سیاست"]
        if matches(title, WORLD):
            tags.append("#جهان")
        return tags[:max(0, min(max_tags, 2))]

    # Finance: specific headline topic first, general #اقتصاد if appropriate.
    specific = [
        ("#دلار", DOLLAR), ("#طلا", GOLD), ("#بورس", STOCKS),
        ("#بانک", BANK), ("#مسکن", HOUSING), ("#خودرو", CARS),
    ]
    ranked = []
    for i, (tag, keywords) in enumerate(specific):
        hits = sum(1 for keyword in keywords if has(title, keyword))
        if hits:
            ranked.append((-hits, i, tag))
    ranked.sort()
    tags = [item[2] for item in ranked[:2]]
    if not tags:
        tags = ["#اقتصاد"]
    elif len(tags) == 1:
        tags.append("#اقتصاد")
    return tags[:max(0, min(max_tags, 2))]


def importance(article):
    """Return (importance score, eligible); no posting quota/spacing rules."""
    title = norm(article.get("title", ""))
    subject = category(article)
    if not subject or len(title) < 14:
        return 0, False

    impact = sum(1 for word in SIGNIFICANT if has(title, word))
    ceremonial = matches(title, ROUTINE)
    standout = matches(title, (
        "حمله موشکی", "حملات موشکی", "حمله پهپادی", "بمباران",
        "عملیات نظامی", "اتش بس", "درگیری نظامی", "شلیک موشک",
        "قیمت دلار", "قیمت طلا", "قیمت سکه", "شاخص کل", "تورم",
        "کالابرگ", "یارانه", "انتخابات ریاست جمهوری", "قطعنامه",
        "تحریم جدید", "توافق هسته ای", "قیمت خودرو", "قیمت مسکن",
    ))
    score = 2 + min(impact, 4) * 2 + (2 if standout else 0)
    if re.search(r"\d", title) and subject == "economy":
        score += 1
    if matches(title, ("سراسری", "کشوری", "کل کشور", "ملی", "فوری")):
        score += 1

    if ceremonial and not standout:
        return score - 5, False
    if impact == 0 and not standout:
        return score - 2, False
    if matches(title, WEAK_ONLY) and impact <= 1 and not standout:
        return score - 2, False
    return score, True
