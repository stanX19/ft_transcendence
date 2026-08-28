"""Local PostgreSQL full-text retrieval and bounded RAG context assembly."""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from sqlalchemy import Float, cast, func, select
from sqlalchemy.orm import Session

from app.features.ai.schemas import SourceBook
from app.features.books.models import Book


DEFAULT_RETRIEVAL_LIMIT = 5
DEFAULT_CONTEXT_MAX_CHARS = 6000
DEFAULT_BOOK_MAX_CHARS = 1400


@dataclass(frozen=True, init=False)
class RetrievedBook:
    """A ranked, provider-neutral catalog result.

    Keeping plain metadata here means context assembly and UI transport do
    not need to retain a live SQLAlchemy object. ``book`` remains an optional
    internal reference for callers that need it after database retrieval.
    """

    book_id: int
    title: str
    author: str
    description: str
    category: str
    score: float
    isbn: str | None = None
    book: Book | None = field(default=None, repr=False, compare=False)

    def __init__(
        self,
        book_id: int | None = None,
        title: str | None = None,
        author: str | None = None,
        description: str | None = None,
        category: str | None = None,
        score: float | None = None,
        *,
        isbn: str | None = None,
        book: Book | None = None,
        rank: float | None = None,
    ) -> None:
        """Accept both plain metadata and a catalog model for easy injection."""

        if book is not None:
            book_id = book.id if book_id is None else book_id
            title = book.title if title is None else title
            author = book.author if author is None else author
            description = book.description if description is None else description
            category = book.category if category is None else category
            isbn = book.isbn if isbn is None else isbn
        if book_id is None or title is None or author is None:
            raise TypeError("RetrievedBook requires book metadata.")
        if description is None or category is None:
            raise TypeError("RetrievedBook requires description and category.")
        if score is None:
            score = rank if rank is not None else 0.0
        object.__setattr__(self, "book_id", book_id)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "author", author)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "category", category)
        object.__setattr__(self, "score", float(score))
        object.__setattr__(self, "isbn", isbn)
        object.__setattr__(self, "book", book)

    @property
    def rank(self) -> float:
        """Compatibility alias for callers that call relevance a rank."""

        return self.score

    @property
    def source(self) -> SourceBook:
        return SourceBook(
            book_id=self.book_id,
            title=self.title,
            author=self.author,
            category=self.category,
            isbn=self.isbn,
        )

    @property
    def source_metadata(self) -> dict[str, object]:
        return self.source.model_dump()


@dataclass(frozen=True)
class RAGContext:
    """Bounded model context with source metadata kept separately."""

    context: str
    sources: list[SourceBook]

    @property
    def prompt_context(self) -> str:
        """Descriptive alias used by the service prompt builder."""

        return self.context

    @property
    def text(self) -> str:
        """Convenient alias for providers and simple test fakes."""

        return self.context


def _safe_limit(limit: int) -> int:
    return max(1, min(int(limit), 20))


def _fallback_match(book: Book, question: str) -> bool:
    terms = [term.casefold() for term in question.split() if term.strip()]
    haystack = " ".join(
        (getattr(book, field, "") or "")
        for field in ("title", "author", "description", "category")
    ).casefold()
    return bool(terms) and all(term in haystack for term in terms)


def _result(book: Book, score: float) -> RetrievedBook:
    return RetrievedBook(
        book_id=book.id,
        title=book.title,
        author=book.author,
        description=book.description,
        category=book.category,
        score=score,
        isbn=book.isbn,
        book=book,
    )


def retrieve_books(
    db: Session,
    question: str,
    *,
    limit: int = DEFAULT_RETRIEVAL_LIMIT,
) -> list[RetrievedBook]:
    """Return ranked catalog records using PostgreSQL full-text search only.

    The query is intentionally lexical and local. OR semantics keep records
    matching a distinctive part of a natural-language question useful while
    PostgreSQL's rank still puts multi-term matches first.
    """

    normalized_question = question.strip()
    if not normalized_question:
        return []

    bounded_limit = _safe_limit(limit)
    search_terms = [
        term for term in re.findall(r"[\w-]+", normalized_question) if term
    ]
    query_text = " OR ".join(search_terms) or normalized_question
    query = func.websearch_to_tsquery("simple", query_text)
    rank = cast(func.ts_rank_cd(Book.search_document, query), Float).label("rank")
    rows = db.execute(
        select(Book, rank)
        .where(Book.search_document.op("@@")(query))
        .order_by(rank.desc(), Book.id.asc())
        .limit(bounded_limit)
    ).all()
    results = [_result(book, float(score or 0.0)) for book, score in rows]
    if results:
        return results

    # A query made entirely of stop words may be rejected by websearch_to_tsquery.
    # This bounded fallback preserves useful local retrieval without weakening
    # the indexed path used for ordinary questions.
    books = list(db.scalars(select(Book).order_by(Book.id.asc())).all())
    return [
        _result(book, 0.0)
        for book in books
        if _fallback_match(book, normalized_question)
    ][:bounded_limit]


def retrieve_catalog(
    db: Session,
    question: str,
    *,
    limit: int = DEFAULT_RETRIEVAL_LIMIT,
) -> list[RetrievedBook]:
    """Named function alias for catalog retrieval callers."""

    return retrieve_books(db, question, limit=limit)


class CatalogRetriever:
    """Injectable facade for the local PostgreSQL catalog retriever."""

    def __init__(
        self,
        db: Session,
        *,
        default_limit: int = DEFAULT_RETRIEVAL_LIMIT,
    ) -> None:
        self.db = db
        self.default_limit = default_limit

    def retrieve(
        self,
        question: str,
        *,
        limit: int | None = None,
    ) -> list[RetrievedBook]:
        return retrieve_books(
            self.db,
            question,
            limit=self.default_limit if limit is None else limit,
        )


def _trim(value: str, limit: int) -> str:
    value = " ".join(value.split())
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 1)].rstrip() + "…"


def assemble_context(
    retrieved: list[RetrievedBook],
    *,
    max_books: int = DEFAULT_RETRIEVAL_LIMIT,
    max_chars: int = DEFAULT_CONTEXT_MAX_CHARS,
    per_book_chars: int = DEFAULT_BOOK_MAX_CHARS,
) -> RAGContext:
    """Format at most a few records while preserving source cards separately."""

    bounded_book_count = max(0, min(int(max_books), DEFAULT_RETRIEVAL_LIMIT))
    bounded_books = retrieved[:bounded_book_count]
    context_parts: list[str] = []
    sources: list[SourceBook] = []
    used_chars = 0

    for position, result in enumerate(bounded_books, start=1):
        source = result.source
        block = (
            f"[{position}] {result.title}\n"
            f"Book ID: {result.book_id}\n"
            f"Author: {result.author}\n"
            f"Category: {result.category}\n"
            f"Description: {_trim(result.description, per_book_chars)}"
        )
        remaining = max_chars - used_chars
        if remaining <= 0:
            break
        if len(block) > remaining:
            block = _trim(block, remaining)
        context_parts.append(block)
        sources.append(source)
        used_chars += len(block) + 2

    return RAGContext(context="\n\n".join(context_parts), sources=sources)


def build_context(
    retrieved: list[RetrievedBook],
    *,
    max_books: int = DEFAULT_RETRIEVAL_LIMIT,
    max_chars: int = DEFAULT_CONTEXT_MAX_CHARS,
    per_book_chars: int = DEFAULT_BOOK_MAX_CHARS,
) -> RAGContext:
    """Function alias for the context assembler."""

    return assemble_context(
        retrieved,
        max_books=max_books,
        max_chars=max_chars,
        per_book_chars=per_book_chars,
    )


class RAGContextAssembler:
    """Configurable facade for building bounded model context."""

    def __init__(
        self,
        *,
        max_books: int = DEFAULT_RETRIEVAL_LIMIT,
        max_chars: int = DEFAULT_CONTEXT_MAX_CHARS,
        per_book_chars: int = DEFAULT_BOOK_MAX_CHARS,
    ) -> None:
        self.max_books = max_books
        self.max_chars = max_chars
        self.per_book_chars = per_book_chars

    def assemble(self, retrieved: list[RetrievedBook]) -> RAGContext:
        return assemble_context(
            retrieved,
            max_books=self.max_books,
            max_chars=self.max_chars,
            per_book_chars=self.per_book_chars,
        )
