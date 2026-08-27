import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const book = {
  id: 42,
  isbn: null,
  slug: "loan-book",
  title: "The Borrowable Book",
  author: "A. Reader",
  description: "A book available for a loan flow.",
  category: "Testing",
  publication_year: 2025,
  total_copies: 2,
  available_copies: 1,
  created_at: "2025-01-01T00:00:00Z",
  updated_at: "2025-01-01T00:00:00Z",
};

const loan = {
  id: 7,
  user_id: 9,
  book_id: 42,
  book_title: book.title,
  book_author: book.author,
  borrowed_at: "2025-01-01T00:00:00Z",
  due_at: "2025-01-15T00:00:00Z",
  returned_at: null,
};

function requestPath(input: RequestInfo | URL): string {
  return typeof input === "string" ? input : input.toString();
}

const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

async function renderAt(path: string) {
  window.history.replaceState({}, "", path);
  vi.resetModules();
  const { default: App } = await import("./App");
  return render(<App />);
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  window.history.replaceState({}, "", "/");
});

describe("loan application flows", () => {
  it("borrows a book from its detail page and refreshes availability", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const path = requestPath(input);
      if (path.endsWith("/api/auth/me")) {
        return Promise.resolve(
          jsonResponse({
            user: {
              id: 9,
              email: "reader@example.test",
              display_name: "Reader",
              bio: "",
              role: "MEMBER",
              is_online: true,
            },
          }),
        );
      }
      if (path.endsWith("/api/books/42")) {
        return Promise.resolve(jsonResponse({ book }));
      }
      if (path.endsWith("/api/books/42/borrow")) {
        return Promise.resolve(jsonResponse({ loan }, 201));
      }
      return Promise.resolve(jsonResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    await renderAt("/books/42");

    const borrowButton = await screen.findByRole("button", { name: /borrow/i });
    fireEvent.click(borrowButton);
    expect(await screen.findByText(/loan recorded|borrowed/i)).toBeInTheDocument();
    expect(
      fetchMock.mock.calls.some(([input, init]) =>
        requestPath(input).endsWith("/api/books/42/borrow") &&
        (init as RequestInit).method === "POST",
      ),
    ).toBe(true);
  });

  it("renders active and returned loans on the My Loans page", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const path = requestPath(input);
        if (path.endsWith("/api/auth/me")) {
          return Promise.resolve(
            jsonResponse({
              user: {
                id: 9,
                email: "reader@example.test",
                display_name: "Reader",
                bio: "",
                role: "MEMBER",
                is_online: true,
              },
            }),
          );
        }
        if (path.endsWith("/api/loans/me")) {
          return Promise.resolve(jsonResponse({ active: [loan], history: [] }));
        }
        return Promise.resolve(jsonResponse({}));
      }),
    );

    await renderAt("/loans");

    expect(await screen.findByRole("heading", { name: /my loans/i })).toBeInTheDocument();
    expect(screen.getByText(book.title)).toBeInTheDocument();
    expect(screen.getByText(/active/i)).toBeInTheDocument();
  });
});
