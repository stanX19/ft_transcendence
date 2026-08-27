"""Catalog-grounded assistant service."""

from __future__ import annotations

from collections.abc import Iterator
from collections.abc import Sequence
import inspect

from sqlalchemy.orm import Session

from app.features.ai.provider import ChatProvider, GeminiProvider
from app.features.ai.rag import (
    DEFAULT_RETRIEVAL_LIMIT,
    RAGContextAssembler,
    RAGContext,
    assemble_context,
    retrieve_books,
)
from app.features.ai.schemas import AssistantAnswer, RAGAnswer
from app.features.ai.tools import ToolContext, execute_tool, tool_definitions
from app.features.users.models import User


GROUNDING_INSTRUCTION = (
    "You are LibraryOS's catalog assistant. Answer catalog questions using "
    "the supplied catalog records only. If the records do not support an "
    "answer, say that the catalog does not provide enough information. Do "
    "not invent inventory, book IDs, authors, or other catalog facts. "
    "Account-specific facts must come from authorized application tools."
)

ASSISTANT_INSTRUCTION = (
    f"{GROUNDING_INSTRUCTION} Safe application tools are available only "
    "through the server request context: search_catalog, get_book_details, "
    "get_book_availability, and get_current_user_loans. Never invent a user "
    "id or request private data for another account."
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


def _provider_kwargs(
    method,
    *,
    system_instruction: str,
    history: Sequence[dict[str, str]],
) -> dict[str, object]:
    """Pass optional context only when a small test/provider double accepts it."""

    try:
        parameters = inspect.signature(method).parameters
    except (TypeError, ValueError):
        return {"system_instruction": system_instruction, "history": history}
    accepts_any = any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    )
    values: dict[str, object] = {}
    if accepts_any or "system_instruction" in parameters:
        values["system_instruction"] = system_instruction
    if accepts_any or "history" in parameters:
        values["history"] = history
    return values


def _generate_with_context(
    provider: ChatProvider,
    prompt: str,
    *,
    system_instruction: str,
    history: Sequence[dict[str, str]],
) -> str:
    return provider.generate(
        prompt=prompt,
        **_provider_kwargs(
            provider.generate,
            system_instruction=system_instruction,
            history=history,
        ),
    )


def _stream_with_context(
    provider: ChatProvider,
    prompt: str,
    *,
    system_instruction: str,
    history: Sequence[dict[str, str]],
):
    return provider.stream(
        prompt=prompt,
        **_provider_kwargs(
            provider.stream,
            system_instruction=system_instruction,
            history=history,
        ),
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
    answer = _generate_with_context(
        provider or GeminiProvider(),
        build_rag_prompt(normalized_question, context),
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


class AssistantOrchestrator:
    """Compose local RAG, authenticated tools, and the provider boundary."""

    def __init__(
        self,
        db: Session,
        current_user: User,
        provider: ChatProvider | None = None,
    ) -> None:
        self.db = db
        self.current_user = current_user
        self.provider = provider or GeminiProvider()
        self.tool_context = ToolContext(db=db, current_user=current_user)

    @property
    def tools(self) -> list[dict[str, object]]:
        """Return only the allowlisted, request-safe tool declarations."""

        return tool_definitions()

    def execute_tool(
        self,
        name: str,
        arguments: dict[str, object] | None = None,
    ) -> object:
        """Run one tool with the authenticated request context."""

        return execute_tool(name, arguments, self.tool_context)

    def _context(self, question: str) -> RAGContext:
        retrieved = retrieve_books(
            self.db,
            question,
            limit=DEFAULT_RETRIEVAL_LIMIT,
        )
        return assemble_context(retrieved)

    def answer(
        self,
        question: str,
        *,
        history: Sequence[dict[str, str]] = (),
    ) -> AssistantAnswer:
        """Generate a grounded answer after retrieving local catalog context."""

        normalized_question = question.strip()
        if not normalized_question:
            raise ValueError("A question is required.")
        context = self._context(normalized_question)
        prompt = build_rag_prompt(normalized_question, context)
        tool_events: list[dict[str, object]] = []
        generate_with_tools = getattr(self.provider, "generate_with_tools", None)
        if callable(generate_with_tools):
            result = generate_with_tools(
                prompt,
                tool_definitions=self.tools,
                tool_executor=self.execute_tool,
                system_instruction=ASSISTANT_INSTRUCTION,
                history=history,
            )
            answer = result.text if hasattr(result, "text") else str(result)
            if hasattr(result, "tool_events"):
                tool_events = list(result.tool_events)
        else:
            answer = _generate_with_context(
                self.provider,
                prompt,
                system_instruction=ASSISTANT_INSTRUCTION,
                history=history,
            )
        return AssistantAnswer(
            answer=answer,
            sources=context.sources,
            tool_events=tool_events,
        )

    def stream(
        self,
        question: str,
        *,
        history: Sequence[dict[str, str]] = (),
    ) -> Iterator[tuple[str, object]]:
        """Yield SSE-ready events with sources before provider token chunks."""

        normalized_question = question.strip()
        if not normalized_question:
            raise ValueError("A question is required.")
        context = self._context(normalized_question)
        for source in context.sources:
            yield "source", source.model_dump()
        for chunk in _stream_with_context(
            self.provider,
            build_rag_prompt(normalized_question, context),
            system_instruction=ASSISTANT_INSTRUCTION,
            history=history,
        ):
            if chunk:
                yield "token", {"text": chunk}
        yield "done", {}


AssistantAgent = AssistantOrchestrator
AIOrchestrator = AssistantOrchestrator
