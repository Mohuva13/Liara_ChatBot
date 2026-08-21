from dataclasses import dataclass
from enum import StrEnum

from app.retrieval.normalizer import normalize_persian


class Intent(StrEnum):
    DEPLOY = "deploy"
    CONFIGURE = "configure"
    CONNECT = "connect"
    TROUBLESHOOT = "troubleshoot"
    COMPARE = "compare"
    PLAN_OR_COST = "plan_or_cost"
    ACCOUNT_OR_TEAM = "account_or_team"
    EXPLAIN = "explain"
    LOCATE_DOCS = "locate_docs"
    OUT_OF_SCOPE = "out_of_scope"


@dataclass(frozen=True, slots=True)
class ScopeDecision:
    in_scope: bool
    intent: Intent
    reason: str


LIARA_TERMS = {
    "لیارا",
    "استقرار",
    "دیپلوی",
    "deploy",
    "دیتابیس",
    "postgresql",
    "mysql",
    "redis",
    "دامنه",
    "dns",
    "برنامه",
    "ابر",
    "شبکه خصوصی",
    "لاگ",
    "object storage",
    "فضای ابری",
    "کوبرنتیز",
    "docker",
}
OUT_OF_SCOPE_TERMS = {
    "آب و هوا",
    "فال",
    "نتیجه فوتبال",
    "فیلم سینمایی",
    "پزشکی",
    "نسخه دارویی",
    "بورس",
    "قیمت دلار",
    "آشپزی",
}
INTENT_TERMS: tuple[tuple[Intent, tuple[str, ...]], ...] = (
    (Intent.TROUBLESHOOT, ("خطا", "ارور", "کار نمی", "وصل نمی", "مشکل", "لاگ")),
    (Intent.DEPLOY, ("استقرار", "دیپلوی", "deploy", "راه اندازی برنامه")),
    (Intent.CONNECT, ("اتصال", "وصل", "connection", "شبکه خصوصی")),
    (Intent.COMPARE, ("مقایسه", "تفاوت", "بهتر است")),
    (Intent.PLAN_OR_COST, ("هزینه", "قیمت", "پلن", "plan")),
    (Intent.ACCOUNT_OR_TEAM, ("حساب", "تیم", "دسترسی کاربر")),
    (Intent.LOCATE_DOCS, ("مستند", "لینک", "صفحه راهنما")),
    (Intent.CONFIGURE, ("تنظیم", "کانفیگ", "config", "متغیر محیطی")),
)


def classify_scope(query: str) -> ScopeDecision:
    normalized = normalize_persian(query)
    has_liara_signal = any(term in normalized for term in LIARA_TERMS)
    if not has_liara_signal and any(term in normalized for term in OUT_OF_SCOPE_TERMS):
        return ScopeDecision(False, Intent.OUT_OF_SCOPE, "explicit_non_liara_topic")
    for intent, terms in INTENT_TERMS:
        if any(term in normalized for term in terms):
            return ScopeDecision(True, intent, "intent_keyword")
    if has_liara_signal:
        return ScopeDecision(True, Intent.EXPLAIN, "liara_keyword")
    return ScopeDecision(True, Intent.EXPLAIN, "domain_unverified")
