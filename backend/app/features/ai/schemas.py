"""Small, provider-neutral contracts for catalog-grounded answers."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceBook(BaseModel):
    """Catalog metadata that can be displayed beside an assistant answer."""

    book_id: int = Field(gt=0)
    title: str
    author: str
    category: str
    isbn: str | None = None

    model_config = ConfigDict(extra="forbid")


class RAGAnswer(BaseModel):
    """A generated answer and the records that grounded its context."""

    answer: str
    sources: list[SourceBook]

    model_config = ConfigDict(extra="forbid")


class ChatHistoryMessage(BaseModel):
    """One bounded prior message sent with a streaming chat request."""

    role: Literal["user", "assistant"]
    text: str = Field(min_length=1, max_length=4000)

    model_config = ConfigDict(extra="forbid")


class ChatRequest(BaseModel):
    """Accepted request body for the POST streaming endpoint."""

    message: str | None = Field(default=None, max_length=4000)
    prompt: str | None = Field(default=None, max_length=4000)
    question: str | None = Field(default=None, max_length=4000)
    history: list[ChatHistoryMessage] = Field(default_factory=list, max_length=20)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def require_message(self) -> "ChatRequest":
        if not self.text:
            raise ValueError("A chat message is required.")
        return self

    @property
    def text(self) -> str:
        for value in (self.message, self.prompt, self.question):
            if value and value.strip():
                return value.strip()
        return ""

    def history_payload(self) -> list[dict[str, str]]:
        return [message.model_dump() for message in self.history]


class AssistantAnswer(RAGAnswer):
    """Answer shape used by non-streaming orchestration and tests."""

    tool_events: list[dict[str, object]] = Field(default_factory=list)
