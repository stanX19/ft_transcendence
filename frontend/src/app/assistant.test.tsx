import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

function requestPath(input: RequestInfo | URL): string {
  return typeof input === "string" ? input : input.toString();
}

async function renderAt(path: string) {
  window.history.replaceState({}, "", path);
  vi.resetModules();
  const { default: App } = await import("./App");
  return render(<App />);
}

function streamResponse(): Response {
  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(encoder.encode('event: source\ndata: {"book_id":8,"title":"The source book","author":"Local author"}\n\n'));
      controller.enqueue(encoder.encode('event: token\ndata: {"text":"A grounded "}\n\n'));
      controller.enqueue(encoder.encode('event: token\ndata: {"text":"answer."}\n\n'));
      controller.enqueue(encoder.encode("event: done\ndata: {}\n\n"));
      controller.close();
    },
  });
  return new Response(body, { status: 200, headers: { "Content-Type": "text/event-stream" } });
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  window.history.replaceState({}, "", "/");
});

describe("assistant page", () => {
  it("streams a response and renders its catalog sources", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const path = requestPath(input);
      if (path.endsWith("/api/auth/me")) {
        return Promise.resolve(jsonResponse({ user: { id: 5, email: "reader@example.test", display_name: "Reader", bio: "", role: "MEMBER", is_online: true } }));
      }
      if (path.endsWith("/api/ai/chat/stream")) return Promise.resolve(streamResponse());
      return Promise.resolve(jsonResponse({}, 404));
    });
    vi.stubGlobal("fetch", fetchMock);

    await renderAt("/assistant");
    expect(await screen.findByRole("heading", { name: "A helpful guide to your library." })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Ask the LibraryOS assistant"), { target: { value: "Tell me about the source book" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByText("A grounded answer.")).toBeInTheDocument();
    expect(screen.getByText("The source book")).toBeInTheDocument();
    expect(screen.getByText("Sources from your catalog")).toBeInTheDocument();
    const request = fetchMock.mock.calls.find(([input]) => requestPath(input).endsWith("/api/ai/chat/stream"));
    expect(request?.[1]?.method).toBe("POST");
    expect(request?.[1]?.body).toContain("Tell me about the source book");
  });

  it("shows a safe stream error", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const path = requestPath(input);
      if (path.endsWith("/api/auth/me")) {
        return Promise.resolve(jsonResponse({ user: { id: 5, email: "reader@example.test", display_name: "Reader", bio: "", role: "MEMBER", is_online: true } }));
      }
      if (path.endsWith("/api/ai/chat/stream")) {
        const encoder = new TextEncoder();
        const body = new ReadableStream<Uint8Array>({
          start(controller) {
            controller.enqueue(encoder.encode('event: error\ndata: {"code":"provider_error","message":"The Gemini provider is temporarily unavailable."}\n\n'));
            controller.close();
          },
        });
        return Promise.resolve(new Response(body, { status: 200, headers: { "Content-Type": "text/event-stream" } }));
      }
      return Promise.resolve(jsonResponse({}, 404));
    });
    vi.stubGlobal("fetch", fetchMock);

    await renderAt("/assistant");
    await screen.findByRole("heading", { name: "A helpful guide to your library." });
    fireEvent.change(screen.getByLabelText("Ask the LibraryOS assistant"), { target: { value: "Hello" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Gemini provider is temporarily unavailable.");
  });
});
