from app.core.config import Settings
from app.services.sessions import RedisSessionStore
from app.sessions.models import SessionState, SessionTurn


def test_session_compaction_summarizes_only_user_turns() -> None:
    store = RedisSessionStore(
        Settings(session_summary_after_turns=4, session_max_turns=12)
    )
    state = SessionState(
        turns=[
            SessionTurn(role="user", text="برنامه من Next.js است."),
            SessionTurn(role="assistant", text="ادعای تأییدنشده مدل"),
            SessionTurn(role="user", text="مرحله build انجام شد."),
            SessionTurn(role="assistant", text="مرحله بعدی"),
        ]
    )

    compacted = store._append_to_state(
        state,
        [
            SessionTurn(role="user", text="حالا deploy کنم؟"),
            SessionTurn(role="assistant", text="پاسخ"),
        ],
    )

    assert "برنامه من Next.js است" in compacted.summary
    assert "ادعای تأییدنشده مدل" not in compacted.summary
    assert len(compacted.turns) == 4
