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

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  window.history.replaceState({}, "", "/");
});

describe("catalog import and export page", () => {
  it("shows all three export actions to a librarian", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const path = requestPath(input);
      if (path.endsWith("/api/auth/me")) return Promise.resolve(jsonResponse({ user: { id: 4, email: "librarian@example.test", display_name: "Librarian", bio: "", role: "LIBRARIAN", is_online: true } }));
      return Promise.resolve(new Response("id,title\n1,Example\n", { status: 200 }));
    }));
    await renderAt("/admin/import-export");

    expect(await screen.findByRole("heading", { name: "Import & export", level: 1 })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Export CSV" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Export JSON" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Export XML" })).toBeInTheDocument();
  });

  it("submits the selected format and renders import counts", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = requestPath(input);
      if (path.endsWith("/api/auth/me")) return Promise.resolve(jsonResponse({ user: { id: 4, email: "admin@example.test", display_name: "Admin", bio: "", role: "ADMIN", is_online: true } }));
      if (path.endsWith("/api/admin/import-export/import")) return Promise.resolve(jsonResponse({ format: "json", inserted: 2, updated: 1, rejected: 0, errors: [], summary: { inserted: 2, updated: 1, rejected: 0 } }));
      return Promise.resolve(jsonResponse({}, 404));
    });
    vi.stubGlobal("fetch", fetchMock);

    await renderAt("/admin/import-export");
    await screen.findByRole("heading", { name: "Import & export", level: 1 });
    const file = new File(["[]"], "catalog.json", { type: "application/json" });
    fireEvent.change(screen.getByLabelText("Catalog file"), { target: { files: [file] } });
    fireEvent.change(screen.getByLabelText("File format"), { target: { value: "json" } });
    fireEvent.click(screen.getByRole("button", { name: "Import catalog" }));

    expect(await screen.findByText("Catalog import completed.")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/admin/import-export/import", expect.objectContaining({ method: "POST" }));
    const request = fetchMock.mock.calls.find(([input]) => requestPath(input).endsWith("/api/admin/import-export/import"));
    expect(request?.[1]?.body).toBeInstanceOf(FormData);
  });
});
