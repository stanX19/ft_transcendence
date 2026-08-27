import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

function requestPath(input: RequestInfo | URL): string {
  return typeof input === "string" ? input : input.toString();
}

async function renderAt(path: string) {
  window.history.replaceState({}, "", path);
  vi.resetModules();
  const { default: App } = await import("./App");
  return render(<App />);
}

const book = {
  id: 42,
  title: "The Practical Catalog",
  author: "A. Reader",
  description: "A guide to finding and keeping good books.",
  category: "Testing",
  publication_year: 2025,
  total_copies: 3,
  available_copies: 2,
};

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  window.history.replaceState({}, "", "/");
});

describe("catalog application flows", () => {
  it("renders a real catalog list and links to book details", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const path = requestPath(input);
      if (path.endsWith("/api/auth/me")) {
        return Promise.resolve(jsonResponse({ error: { code: "unauthenticated" } }, 401));
      }
      if (path.startsWith("/api/books")) {
        return Promise.resolve(jsonResponse({ items: [book], page: 1, page_size: 20, total: 1 }));
      }
      return Promise.resolve(jsonResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);

    await renderAt("/books");

    expect(await screen.findByText("The Practical Catalog")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /the practical catalog/i })).toHaveAttribute(
      "href",
      "/books/42",
    );
    const catalogRequest = fetchMock.mock.calls.find(([input]) =>
      requestPath(input).startsWith("/api/books"),
    );
    expect(catalogRequest).toBeDefined();
    expect((catalogRequest?.[1] as RequestInit).credentials).not.toBe("omit");
  });

  it("renders book details and current availability", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const path = requestPath(input);
        if (path.endsWith("/api/auth/me")) {
          return Promise.resolve(jsonResponse({ error: { code: "unauthenticated" } }, 401));
        }
        if (path.endsWith("/api/books/42")) {
          return Promise.resolve(jsonResponse({ book }));
        }
        return Promise.resolve(jsonResponse({}));
      }),
    );

    await renderAt("/books/42");

    expect(await screen.findByRole("heading", { name: /the practical catalog/i })).toBeInTheDocument();
    expect(screen.getByText(/2 available/i)).toBeInTheDocument();
  });

  it("shows an intentional catalog error state when the API fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const path = requestPath(input);
        if (path.endsWith("/api/auth/me")) {
          return Promise.resolve(jsonResponse({ error: { code: "unauthenticated" } }, 401));
        }
        if (path.startsWith("/api/books")) {
          return Promise.resolve(jsonResponse({ error: { code: "internal_error" } }, 500));
        }
        return Promise.resolve(jsonResponse({}));
      }),
    );

    await renderAt("/books");

    expect(await screen.findByText(/catalog.*available|catalog.*try again/i)).toBeInTheDocument();
  });

  it("exposes catalog management controls only for a librarian account", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const path = requestPath(input);
        if (path.endsWith("/api/auth/me")) {
          return Promise.resolve(
            jsonResponse({
              user: {
                id: 9,
                email: "librarian@example.test",
                display_name: "Librarian",
                bio: "",
                role: "LIBRARIAN",
                is_online: true,
              },
            }),
          );
        }
        if (path.startsWith("/api/books")) {
          return Promise.resolve(jsonResponse({ items: [book], page: 1, page_size: 20, total: 1 }));
        }
        return Promise.resolve(jsonResponse({}));
      }),
    );

    await renderAt("/books");

    await waitFor(() => expect(screen.getByText("The Practical Catalog")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /add|new book|create book/i })).toBeInTheDocument();
  });
});
