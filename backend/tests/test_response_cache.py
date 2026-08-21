from app.services.response_cache import response_cache_key


def test_cache_key_normalizes_persian_and_sorts_versions() -> None:
    first = response_cache_key(
        query="  كیفیت  ۱۲  ",
        intent="troubleshoot",
        corpus_versions=["v2", "v1"],
        locale="fa-IR",
    )
    second = response_cache_key(
        query="کیفیت 12",
        intent="troubleshoot",
        corpus_versions=["v1", "v2"],
        locale="fa-IR",
    )

    assert first == second
