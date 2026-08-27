"""Bounded RAG context and UI-visible source contracts."""

from __future__ import annotations

from collections.abc import Mapping


def _retrieved_book(index: int, description: str):
    from app.features.ai.rag import RetrievedBook
    from app.features.books.models import Book

    return RetrievedBook(
        book=Book(
            id=index,
            title=f"Source title {index}",
            author=f"Source author {index}",
            description=description,
            category="RAG QA",
            total_copies=1,
            available_copies=1,
        ),
        rank=float(10 - index),
    )


def _field(value: object, name: str) -> object:
    if isinstance(value, Mapping):
        return value[name]
    return getattr(value, name)


def test_context_assembler_bounds_prompt_context_and_preserves_sources() -> None:
    books = [
        _retrieved_book(
            index,
            f"Book {index} " + "long catalog text " * 100,
        )
        for index in range(1, 8)
    ]

    from app.features.ai.rag import assemble_context

    assembled = assemble_context(
        books,
        max_books=5,
        max_chars=800,
    )

    context = _field(assembled, "prompt_context")
    sources = _field(assembled, "sources")

    assert isinstance(context, str)
    assert len(context) <= 800
    assert isinstance(sources, list)
    assert 0 < len(sources) <= 5
    assert all(_field(source, "book_id") in range(1, 8) for source in sources)
    assert all(_field(source, "title").startswith("Source title") for source in sources)
    assert all(_field(source, "author").startswith("Source author") for source in sources)


def test_context_sources_are_separate_structured_metadata() -> None:
    book = _retrieved_book(42, "A short description.")
    from app.features.ai.rag import assemble_context

    assembled = assemble_context([book], max_books=5, max_chars=500)

    context = _field(assembled, "prompt_context")
    sources = _field(assembled, "sources")
    assert isinstance(context, str)
    assert isinstance(sources, list)
    assert context
    assert len(sources) == 1
    assert _field(sources[0], "book_id") == 42
    assert _field(sources[0], "title") == "Source title 42"
    assert _field(sources[0], "author") == "Source author 42"
    # UI metadata is returned as records, not serialized into the prompt as
    # the sole source of truth.
    assert not isinstance(sources[0], str)
