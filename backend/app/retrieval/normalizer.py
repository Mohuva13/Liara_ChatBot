import re
import unicodedata

ARABIC_TO_PERSIAN = str.maketrans(
    {
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "ۀ": "هٔ",
        "ة": "ه",
        "ؤ": "و",
        "إ": "ا",
        "أ": "ا",
    }
)
PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
WHITESPACE = re.compile(r"[\s\u200c]+")
SEARCH_TERM = re.compile(r"[\w\u0600-\u06ff.+#-]+", re.UNICODE)
SEARCH_STOP_WORDS = {
    "از",
    "است",
    "با",
    "برای",
    "به",
    "چه",
    "چطور",
    "چطوریه",
    "چجوری",
    "چجوریه",
    "در",
    "را",
    "روی",
    "توی",
    "و",
    "یا",
}
SEARCH_ALIASES = {
    "node": "nodejs",
    "node.js": "nodejs",
    "next": "nextjs",
    "next.js": "nextjs",
    "postgres": "postgresql",
    "پستگرس": "postgresql",
    "پستگرسکیوال": "postgresql",
    "پایتون": "python",
    "ردیس": "redis",
}


def normalize_persian(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    normalized = normalized.translate(ARABIC_TO_PERSIAN)
    normalized = normalized.translate(PERSIAN_DIGITS).translate(ARABIC_DIGITS)
    return WHITESPACE.sub(" ", normalized).strip().casefold()


def retrieval_terms(value: str) -> tuple[str, ...]:
    """Return stable, low-noise terms shared by SQL search and relevance gates."""
    terms: list[str] = []
    seen: set[str] = set()
    for raw_term in SEARCH_TERM.findall(normalize_persian(value)):
        term = SEARCH_ALIASES.get(raw_term, raw_term)
        if len(term) <= 1 or term in SEARCH_STOP_WORDS or term in seen:
            continue
        seen.add(term)
        terms.append(term)
    return tuple(terms)


def normalize_search_query(value: str) -> str:
    return " ".join(retrieval_terms(value)) or normalize_persian(value)
