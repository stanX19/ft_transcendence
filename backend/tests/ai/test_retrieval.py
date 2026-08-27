"""Local ranked PostgreSQL retrieval contracts."""

from __future__ import annotations

from collections.abc import Mapping
from uuid import uuid4


def _field(value: object, name: str) -> object:
    if isinstance(value, Mapping):
        return value[name]
    return getattr(value, name)


def _rank(value: object) -> float:
    """Read the relevance field while keeping the assertion result-focused."""

    try:
        return float(_field(value, "rank"))
    except (AttributeError, KeyError):
        return float(_field(value, "score"))


def _source(value: object) -> object:
    """Read the UI-facing source record from a retrieval result."""

    try:
        return _field(value, "source")
    except (AttributeError, KeyError):
        return value


def test_retriever_searches_all_catalog_text_fields_without_gemini(
    db_session,
    create_ai_book,
    monkeypatch,
) -> None:
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "gemini_api_key", "")

    # If retrieval reaches out to Gemini, this test must fail. RAG retrieval is
    # deliberately local and should not construct a provider at all.
    import google.genai

    monkeypatch.setattr(
        google.genai,
        "Client",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("retrieval must not construct a Gemini client")
        ),
    )

    from app.features.ai.rag import retrieve_books

    marker = uuid4().hex
    field_books = {
        "title": create_ai_book(title=f"Title marker {marker}"),
        "author": create_ai_book(author=f"Author marker {marker}"),
        "description": create_ai_book(description=f"Description marker {marker}"),
        "category": create_ai_book(category=f"Category marker {marker}"),
    }
    for field, book in field_books.items():
        results = retrieve_books(db_session, f"{field} marker {marker}")
        result_ids = {_field(result, "book_id") for result in results}
        assert book.id in result_ids, (field, results)


def test_retriever_returns_relevance_ranked_results_and_caps_default_limit(
    db_session,
    create_ai_book,
) -> None:
    from app.features.ai.rag import retrieve_books

    marker = uuid4().hex
    strongest = create_ai_book(
        title=f"{marker} {marker} astronomy handbook",
        description=f"{marker} {marker} practical astronomy reference",
    )
    weaker = create_ai_book(
        title=f"Introduction to {marker}",
        description="A general catalog description.",
    )
    for index in range(6):
        create_ai_book(
            title=f"{marker} astronomy supporting title {index}",
            description="A supporting catalog record.",
        )

    results = retrieve_books(db_session, f"{marker} astronomy")

    assert len(results) <= 5
    assert results
    assert _field(results[0], "book_id") == strongest.id
    assert len(results) == 5
    ranks = [_rank(result) for result in results]
    assert ranks == sorted(ranks, reverse=True)


def test_retrieval_result_exposes_source_book_metadata(
    db_session,
    create_ai_book,
) -> None:
    from app.features.ai.rag import retrieve_books

    marker = uuid4().hex
    book = create_ai_book(
        title=f"Source title {marker}",
        author=f"Source author {marker}",
        description=f"Source description {marker}",
        category=f"Source category {marker}",
    )

    results = retrieve_books(db_session, marker)

    assert results
    result = next(
        result
        for result in results
        if _field(result, "book_id") == book.id
    )
    assert _field(_source(result), "title") == book.title
    assert _field(_source(result), "author") == book.author
    assert isinstance(_rank(result), float)
