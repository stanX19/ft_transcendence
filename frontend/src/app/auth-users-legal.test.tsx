import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

type FetchHandler = (
  input: RequestInfo | URL,
  init?: RequestInit,
) => Response | Promise<Response>;

const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

function mockFetch(handler: FetchHandler) {
  const fetchMock = vi.fn(handler);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function requestPath(input: RequestInfo | URL): string {
  return typeof input === "string" ? input : input.toString();
}

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

describe("auth, privacy, and legal application flows", () => {
  it("derives anonymous state from /api/auth/me and exposes legal footer links", async () => {
    const fetchMock = mockFetch((input) => {
      if (requestPath(input).endsWith("/api/auth/me")) {
        return jsonResponse({ error: { code: "unauthenticated" } }, 401);
      }
      return jsonResponse({});
    });
    const localStorageSet = vi.spyOn(Storage.prototype, "setItem");
    const sessionStorageSet = vi.spyOn(Storage.prototype, "setItem");

    await renderAt("/");

    expect(await screen.findByText(/find your next good read/i)).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /privacy policy/i }),
    ).toHaveAttribute("href", "/privacy");
    expect(screen.getByRole("link", { name: /terms/i })).toHaveAttribute(
      "href",
      "/terms",
    );
    expect(
      fetchMock.mock.calls.some(([input]) => requestPath(input).endsWith("/api/auth/me")),
    ).toBe(true);
    expect(localStorageSet).not.toHaveBeenCalled();
    expect(sessionStorageSet).not.toHaveBeenCalled();
  });

  it("renders project-specific privacy content including Gemini processing", async () => {
    mockFetch((input) => {
      if (requestPath(input).endsWith("/api/auth/me")) {
        return jsonResponse({ error: { code: "unauthenticated" } }, 401);
      }
      return jsonResponse({});
    });

    await renderAt("/privacy");

    expect(
      await screen.findByRole("heading", { name: /privacy policy/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/account|profile data/i)).toBeInTheDocument();
    expect(screen.getByText(/loan records/i)).toBeInTheDocument();
    expect(screen.getByText(/uploaded assets/i)).toBeInTheDocument();
    expect(screen.getByText(/Gemini/i)).toBeInTheDocument();
  });

  it("renders project-specific terms content", async () => {
    mockFetch((input) => {
      if (requestPath(input).endsWith("/api/auth/me")) {
        return jsonResponse({ error: { code: "unauthenticated" } }, 401);
      }
      return jsonResponse({});
    });

    await renderAt("/terms");

    expect(
      await screen.findByRole("heading", { name: /terms of service/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/educational|demo purpose/i)).toBeInTheDocument();
    expect(screen.getByText(/account responsibility/i)).toBeInTheDocument();
    expect(screen.getByText(/acceptable use/i)).toBeInTheDocument();
    expect(screen.getByText(/AI response limitations/i)).toBeInTheDocument();
    expect(screen.getByText(/service availability/i)).toBeInTheDocument();
  });

  it("validates the login form and posts credentials without browser token storage", async () => {
    const fetchMock = mockFetch((input, init) => {
      const path = requestPath(input);
      if (path.endsWith("/api/auth/me")) {
        return jsonResponse({ error: { code: "unauthenticated" } }, 401);
      }
      if (path.endsWith("/api/auth/login")) {
        return jsonResponse({
          id: 7,
          email: "reader@example.test",
          display_name: "Reader",
          role: "MEMBER",
        });
      }
      return jsonResponse({}, 204);
    });
    const localStorageSet = vi.spyOn(Storage.prototype, "setItem");
    const sessionStorageSet = vi.spyOn(Storage.prototype, "setItem");

    await renderAt("/login");
    const email = await screen.findByLabelText(/email/i);
    const password = screen.getByLabelText(/password/i);
    const submit = screen.getByRole("button", { name: /log in|sign in/i });

    fireEvent.click(submit);
    expect(email).toBeInvalid();
    expect(password).toBeInvalid();

    fireEvent.change(email, { target: { value: "reader@example.test" } });
    fireEvent.change(password, { target: { value: "correct-horse-battery-staple" } });
    fireEvent.click(submit);

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([input]) =>
          requestPath(input).endsWith("/api/auth/login"),
        ),
      ).toBe(true);
    });
    const loginCall = fetchMock.mock.calls.find(([input]) =>
      requestPath(input).endsWith("/api/auth/login"),
    );
    expect(loginCall).toBeDefined();
    const requestInit = loginCall?.[1] as RequestInit;
    expect(requestInit.credentials).not.toBe("omit");
    expect(requestInit.headers).toMatchObject({ "Content-Type": "application/json" });
    expect(JSON.parse(requestInit.body as string)).toEqual({
      email: "reader@example.test",
      password: "correct-horse-battery-staple",
    });
    expect(requestInit.headers).not.toHaveProperty("Authorization");
    expect(localStorageSet).not.toHaveBeenCalled();
    expect(sessionStorageSet).not.toHaveBeenCalled();
  });

  it("validates the registration form before sending a request", async () => {
    const fetchMock = mockFetch((input) => {
      if (requestPath(input).endsWith("/api/auth/me")) {
        return jsonResponse({ error: { code: "unauthenticated" } }, 401);
      }
      return jsonResponse({});
    });

    await renderAt("/register");
    const displayName = await screen.findByLabelText(/display name|name/i);
    const email = screen.getByLabelText(/email/i);
    const password = screen.getByLabelText(/password/i);
    fireEvent.click(screen.getByRole("button", { name: /register|create account|sign up/i }));

    expect(displayName).toBeInvalid();
    expect(email).toBeInvalid();
    expect(password).toBeInvalid();
    expect(
      fetchMock.mock.calls.some(([input]) =>
        requestPath(input).endsWith("/api/auth/register"),
      ),
    ).toBe(false);
  });

  it("redirects an unauthenticated visitor away from protected profile routes", async () => {
    mockFetch((input) => {
      if (requestPath(input).endsWith("/api/auth/me")) {
        return jsonResponse({ error: { code: "unauthenticated" } }, 401);
      }
      return jsonResponse({});
    });

    await renderAt("/profile");

    expect(
      await screen.findByRole("heading", { name: /log in|sign in/i }),
    ).toBeInTheDocument();
    await waitFor(() => expect(window.location.pathname).toBe("/login"));
  });
});
