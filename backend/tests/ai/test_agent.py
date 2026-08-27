"""AI tool orchestration contracts."""

from __future__ import annotations


def test_orchestrator_exposes_only_safe_tools_and_authenticated_context(
    db_session,
    create_ai_book,
) -> None:
    from app.features.ai.service import AssistantOrchestrator
    from app.features.users.models import User, UserRole
    from uuid import uuid4

    user = User(
        email=f"agent-{uuid4().hex}@example.test",
        password_hash="test-only-hash",
        display_name="Agent User",
        bio="",
        role=UserRole.MEMBER,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    book = create_ai_book(title="Orchestration source")

    class FakeProvider:
        def generate(self, prompt: str, **kwargs) -> str:
            assert "Orchestration source" in prompt
            return "Grounded response"

    agent = AssistantOrchestrator(db_session, user, provider=FakeProvider())

    assert {item["name"] for item in agent.tools} == {
        "search_catalog",
        "get_book_details",
        "get_book_availability",
        "get_current_user_loans",
    }
    availability = agent.execute_tool("get_book_availability", {"book_id": book.id})
    assert availability["book_id"] == book.id
    assert agent.answer("Tell me about Orchestration source").answer == "Grounded response"
