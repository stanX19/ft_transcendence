"""AI tool orchestration contracts."""

from __future__ import annotations

import pytest


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
        "navigate_to_page",
    }
    availability = agent.execute_tool("get_book_availability", {"book_id": book.id})
    assert availability["book_id"] == book.id
    assert agent.answer("Tell me about Orchestration source").answer == "Grounded response"


def test_navigation_requires_explicit_and_unambiguous_book_context(
    db_session,
    create_ai_book,
) -> None:
    from app.features.ai.rag import RAGContext
    from app.features.ai.schemas import SourceBook
    from app.features.ai.service import AssistantOrchestrator
    from app.features.ai.tools import ToolInputError
    from app.features.users.models import User, UserRole
    from uuid import uuid4

    user = User(
        email=f"navigation-{uuid4().hex}@example.test",
        password_hash="test-only-hash",
        display_name="Navigation User",
        bio="",
        role=UserRole.MEMBER,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    first = create_ai_book(title="First navigation book")
    second = create_ai_book(title="Second navigation book")

    class FakeProvider:
        def generate(self, prompt: str, **kwargs) -> str:
            del prompt, kwargs
            return "Grounded response"

    agent = AssistantOrchestrator(db_session, user, provider=FakeProvider())
    context = RAGContext(
        context="",
        sources=[
            SourceBook(book_id=first.id, title=first.title, author=first.author, category=first.category),
            SourceBook(book_id=second.id, title=second.title, author=second.author, category=second.category),
        ],
    )

    with pytest.raises(ToolInputError):
        agent._execute_chat_tool(
            "navigate_to_page",
            {"destination": "book", "book_id": first.id},
            question="Bring me to this book",
            history=[
                {
                    "role": "assistant",
                    "text": f"Book ID: {first.id}\nBook ID: {second.id}",
                }
            ],
            context=context,
        )

    navigation = agent._execute_chat_tool(
        "navigate_to_page",
        {"destination": " BOOK ", "book_id": first.id},
        question=f"Take me to book {first.id}",
        history=(),
        context=context,
    )
    assert navigation["path"] == f"/books/{first.id}"

    with pytest.raises(ToolInputError):
        agent._execute_chat_tool(
            "navigate_to_page",
            {"destination": "book", "book_id": first.id},
            question=f"Do not take me to book {first.id}",
            history=(),
            context=context,
        )


def test_navigation_does_not_use_stale_history_over_current_context(
    db_session,
    create_ai_book,
) -> None:
    from app.features.ai.rag import RAGContext
    from app.features.ai.schemas import SourceBook
    from app.features.ai.service import AssistantOrchestrator
    from app.features.ai.tools import ToolInputError
    from app.features.users.models import User, UserRole
    from uuid import uuid4

    user = User(
        email=f"navigation-context-{uuid4().hex}@example.test",
        password_hash="test-only-hash",
        display_name="Navigation Context User",
        bio="",
        role=UserRole.MEMBER,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    current = create_ai_book(title="Current navigation book")
    stale = create_ai_book(title="Stale navigation book")

    class FakeProvider:
        def generate(self, prompt: str, **kwargs) -> str:
            del prompt, kwargs
            return "Grounded response"

    agent = AssistantOrchestrator(db_session, user, provider=FakeProvider())
    context = RAGContext(
        context="",
        sources=[
            SourceBook(
                book_id=current.id,
                title=current.title,
                author=current.author,
                category=current.category,
            )
        ],
    )

    with pytest.raises(ToolInputError):
        agent._execute_chat_tool(
            "navigate_to_page",
            {"destination": "book", "book_id": stale.id},
            question="Bring me to this book",
            history=[
                {
                    "role": "assistant",
                    "text": f"Book ID: {stale.id}",
                }
            ],
            context=context,
        )
