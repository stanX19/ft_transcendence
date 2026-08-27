import { cleanup, render, screen } from "@testing-library/react";
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

const member = {
  id: 9,
  email: "member@example.test",
  display_name: "Member",
  bio: "",
  role: "MEMBER",
  is_online: true,
};

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  window.history.replaceState({}, "", "/");
});

describe("friends, admin, and upload application flows", () => {
  it("renders the friend list and online state", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const path = requestPath(input);
      if (path.endsWith("/api/auth/me")) return Promise.resolve(jsonResponse({ user: member }));
      if (path.endsWith("/api/friends")) return Promise.resolve(jsonResponse({ items: [{ id: 10, display_name: "A Friend", bio: "", is_online: false }] }));
      if (path.includes("/api/users")) return Promise.resolve(jsonResponse({ items: [] }));
      return Promise.resolve(jsonResponse({}));
    }));

    await renderAt("/friends");

    expect(await screen.findByRole("heading", { name: "Friends", level: 1 })).toBeInTheDocument();
    expect(await screen.findByText("A Friend")).toBeInTheDocument();
    expect(screen.getByText("Offline")).toBeInTheDocument();
  });

  it("renders admin user controls only for an admin account", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const path = requestPath(input);
      if (path.endsWith("/api/auth/me")) return Promise.resolve(jsonResponse({ user: { ...member, role: "ADMIN" } }));
      if (path.startsWith("/api/admin/users")) return Promise.resolve(jsonResponse({ items: [{ ...member, id: 11, email: "target@example.test", role: "MEMBER", created_at: "2025-01-01T00:00:00Z" }], page: 1, page_size: 20, total: 1 }));
      return Promise.resolve(jsonResponse({}));
    }));

    await renderAt("/admin/users");

    expect(await screen.findByRole("heading", { name: /manage users/i })).toBeInTheDocument();
    expect(await screen.findByText("target@example.test")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /delete/i })).toBeInTheDocument();
  });
});
