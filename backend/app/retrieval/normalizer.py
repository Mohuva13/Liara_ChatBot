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


def normalize_persian(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    normalized = normalized.translate(ARABIC_TO_PERSIAN)
    normalized = normalized.translate(PERSIAN_DIGITS).translate(ARABIC_DIGITS)
    return WHITESPACE.sub(" ", normalized).strip().casefold()
