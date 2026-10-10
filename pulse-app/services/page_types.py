from __future__ import annotations

from urllib.parse import urlsplit

PAGE_TYPES = {"homepage", "service", "product", "blog_post", "blog_index", "contact", "application", "thank_you", "privacy_legal", "utility", "unknown"}

def classify_page_type(url: str) -> tuple[str, str]:
    path = (urlsplit(url).path or "/").strip("/").lower()
    if not path: return "homepage", "high"
    segments = set(path.split("/"))
    if segments & {"privacy", "terms", "legal", "cookies", "gdpr"}: return "privacy_legal", "high"
    if segments & {"thanks", "thank-you", "confirmation", "success"}: return "thank_you", "high"
    if segments & {"apply", "application", "careers", "signup", "sign-up"}: return "application", "medium"
    if segments & {"contact", "contact-us"}: return "contact", "high"
    if segments & {"blog", "news", "articles", "posts"}: return ("blog_index", "medium") if path in {"blog", "news", "articles", "posts"} else ("blog_post", "medium")
    if segments & {"services", "service", "solutions"}: return "service", "medium"
    if segments & {"products", "product"}: return "product", "medium"
    if segments & {"login", "account", "cart", "checkout", "search", "feed", "feeds"}: return "utility", "high"
    return "unknown", "low"

def applicability(page_type: str) -> dict[str, str]:
    optional = {"comparison": "unknown", "faq": "unknown", "procedural": "unknown", "external_supporting_sources": "unknown"}
    if page_type in {"privacy_legal", "thank_you", "utility"}:
        optional = {key: "not_applicable" for key in optional}
    return optional
