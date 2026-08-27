"""Catalog-grounded assistant service."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.features.ai.provider import ChatProvider, GeminiProvider
from app.features.ai.rag import (
    DEFAULT_RETRIEVAL_LIMIT,
    RAGContextAssembler,
    RAGContext,
    assemble_context,
    retrieve_books,
)
from app.features.ai.schemas import RAGAnswer


GROUNDING_INSTRUCTION = (
    "You are LibraryOS's catalog assistant. Answer catalog questions using "
    "the supplied catalog records only. If the records do not support an "
    "answer, say that the catalog does not provide enough information. Do "
    "not invent inventory, book IDs, authors, or other catalog facts. "
    "Account-specific facts must come from authorized application tools."
)


def build_rag_prompt(question: str, context: RAGContext) -> str:
    """Build a bounded prompt with explicit grounding boundaries."""

    catalog_context = context.prompt_context or "No matching catalog records were found."
    return (
        "Catalog context:\n"
        f"{catalog_context}\n\n"
        "User question:\n"
        f"{question.strip()}\n\n"
        "Give a concise, helpful answer. Do not cite records that are not in "
        "the catalog context."
    )


def answer_question(
    db: Session,
    question: str,
    *,
    provider: ChatProvider | None = None,
    history: Sequence[dict[str, str]] = (),
) -> RAGAnswer:
    """Retrieve local context before asking Gemini for a grounded answer."""

    normalized_question = question.strip()
    if not normalized_question:
        raise ValueError("A question is required.")

    retrieved = retrieve_books(
        db,
        normalized_question,
        limit=DEFAULT_RETRIEVAL_LIMIT,
    )
    context = assemble_context(retrieved)
    answer = (provider or GeminiProvider()).generate(
        prompt=build_rag_prompt(normalized_question, context),
        system_instruction=GROUNDING_INSTRUCTION,
        history=history,
    )
    return RAGAnswer(answer=answer, sources=context.sources)


def generate_grounded_answer(
    db: Session,
    question: str,
    *,
    provider: ChatProvider | None = None,
    history: Sequence[dict[str, str]] = (),
) -> RAGAnswer:
    """Descriptive alias for service callers and contract tests."""

    return answer_question(db, question, provider=provider, history=history)


class RAGService:
    """Small injectable facade for route and orchestration code."""

    def __init__(self, db: Session, provider: ChatProvider | None = None) -> None:
        self.db = db
        self.provider = provider

    def answer(
        self,
        question: str,
        *,
        history: Sequence[dict[str, str]] = (),
    ) -> RAGAnswer:
        return answer_question(
            self.db,
            question,
            provider=self.provider,
            history=history,
        )


class GroundedRAGService:
    """Compose an injectable local retriever with a provider boundary."""

    def __init__(self, *, retriever, provider: ChatProvider) -> None:
        self.retriever = retriever
        self.provider = provider

    def answer(self, question: str) -> RAGAnswer:
        normalized_question = question.strip()
        if not normalized_question:
            raise ValueError("A question is required.")

        retrieved = self.retriever.retrieve(normalized_question)
        context = RAGContextAssembler().assemble(retrieved)
        answer = self.provider.generate(
            build_rag_prompt(normalized_question, context)
        )
        return RAGAnswer(answer=answer, sources=context.sources)
