"""Grounded answer orchestration contracts."""

from __future__ import annotations

from collections.abc import Mapping
import json
import logging


def _field(value: object, name: str) -> object:
    if isinstance(value, Mapping):
        return value[name]
    return getattr(value, name)


def test_grounded_answer_retrieves_before_generation_and_returns_sources() -> None:
    from app.features.ai.rag import RetrievedBook
    from app.features.ai.service import answer_question
    from app.features.books.models import Book

    events: list[object] = []
    source = RetrievedBook(
        book=Book(
            id=7,
            title="Grounded source book",
            author="Local author",
            description="A local catalog description.",
            category="RAG QA",
            total_copies=1,
            available_copies=1,
        ),
        rank=2.0,
    )

    class RecordingProvider:
        def generate(
            self,
            *,
            prompt: str,
            system_instruction: str | None = None,
            history=(),
        ) -> str:
            events.append(("generate", prompt))
            return "Grounded fake answer."

    def retrieve(question: str) -> list[RetrievedBook]:
        events.append(("retrieve", question))
        return [source]

    import app.features.ai.service as service_module

    original_retrieve = service_module.retrieve_books
    service_module.retrieve_books = lambda db, question, *, limit: retrieve(question)
    try:
        result = answer_question(
            object(),
            "Which local book should I read?",
            provider=RecordingProvider(),
        )
    finally:
        service_module.retrieve_books = original_retrieve

    assert [event[0] for event in events] == ["retrieve", "generate"]
    assert events[0][1] == "Which local book should I read?"
    generation_prompt = events[1][1]
    assert "Grounded source book" in generation_prompt
    assert "Local author" in generation_prompt
    assert _field(result, "answer") == "Grounded fake answer."
    sources = _field(result, "sources")
    assert isinstance(sources, list)
    assert len(sources) == 1
    assert _field(sources[0], "book_id") == 7
    assert _field(sources[0], "title") == "Grounded source book"


def test_grounded_answer_can_use_a_fake_provider_without_gemini_configuration(
    monkeypatch,
) -> None:
    from app.core.config import get_settings
    from app.features.ai.rag import RetrievedBook
    from app.features.ai.service import answer_question
    from app.features.books.models import Book

    monkeypatch.setattr(get_settings(), "gemini_api_key", "")
    monkeypatch.setattr(get_settings(), "gemini_api_key_list", [])

    source = RetrievedBook(
        book=Book(
            id=9,
            title="Offline RAG source",
            author="Offline author",
            description="Local-only context.",
            category="RAG QA",
            total_copies=1,
            available_copies=1,
        ),
        rank=1.0,
    )

    class FakeProvider:
        def generate(
            self,
            *,
            prompt: str,
            system_instruction: str | None = None,
            history=(),
        ) -> str:
            assert "Offline RAG source" in prompt
            return "Generated entirely with the fake provider."

    import app.features.ai.service as service_module

    original_retrieve = service_module.retrieve_books
    service_module.retrieve_books = lambda db, question, *, limit: [source]
    try:
        result = answer_question(
            object(),
            "Tell me about the offline source.",
            provider=FakeProvider(),
        )
    finally:
        service_module.retrieve_books = original_retrieve

    assert _field(result, "answer") == "Generated entirely with the fake provider."
    assert _field(_field(result, "sources")[0], "book_id") == 9


def test_rag_logs_source_count_with_correlation_without_prompt_content(
    monkeypatch,
    caplog,
) -> None:
    from app.features.ai.rag import RetrievedBook
    from app.features.ai.service import answer_question
    from app.features.books.models import Book

    source = RetrievedBook(
        book=Book(
            id=11,
            title="Telemetry source book",
            author="Telemetry author",
            description="Catalog evidence for telemetry.",
            category="RAG QA",
            total_copies=1,
            available_copies=1,
        ),
        rank=1.0,
    )
    question = "private prompt marker must not be logged"

    class FakeProvider:
        def generate(
            self,
            *,
            prompt: str,
            system_instruction: str | None = None,
            history=(),
        ) -> str:
            del prompt, system_instruction, history
            return "Safe grounded answer."

    import app.features.ai.service as service_module

    monkeypatch.setattr(
        service_module,
        "retrieve_books",
        lambda db, normalized, *, limit: [source],
    )
    with caplog.at_level(logging.INFO, logger="app.features.ai.service"):
        answer_question(object(), question, provider=FakeProvider())

    events = [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.name == "app.features.ai.service"
    ]
    retrieval = next(
        event
        for event in events
        if event["event"] == "rag_retrieval_completed"
    )
    assert retrieval["source_count"] == 1
    assert retrieval["query_length"] == len(question)
    assert retrieval["request_id"]
    assert question not in " ".join(record.getMessage() for record in caplog.records)
