import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "../../shared/i18n";
import { FileUpload, type UploadedFile } from "./FileUpload";

class FakeUpload {
  private progressHandler: ((event: { lengthComputable: boolean; loaded: number; total: number }) => void) | null = null;

  addEventListener(_event: string, handler: (event: { lengthComputable: boolean; loaded: number; total: number }) => void) {
    this.progressHandler = handler;
  }

  emitProgress() {
    this.progressHandler?.({ lengthComputable: true, loaded: 1, total: 1 });
  }
}

class FakeXMLHttpRequest {
  static lastRequest: FakeXMLHttpRequest | null = null;
  readonly upload = new FakeUpload();
  readonly listeners = new Map<string, () => void>();
  status = 201;
  responseText = JSON.stringify({
    file: {
      id: 12,
      owner_user_id: 9,
      book_id: null,
      kind: "AVATAR",
      original_filename: "avatar.png",
      stored_filename: "server-name.png",
      mime_type: "image/png",
      size_bytes: 4,
      created_at: "2025-01-01T00:00:00Z",
      url: "/api/files/12",
    } satisfies UploadedFile,
  });
  withCredentials = false;
  method = "";
  endpoint = "";

  constructor() {
    FakeXMLHttpRequest.lastRequest = this;
  }

  open(method: string, endpoint: string) {
    this.method = method;
    this.endpoint = endpoint;
  }

  addEventListener(event: string, handler: () => void) {
    this.listeners.set(event, handler);
  }

  send() {
    this.upload.emitProgress();
    this.listeners.get("load")?.();
  }
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("FileUpload", () => {
  it("uses credentialed XHR upload progress and reports the server asset", async () => {
    vi.stubGlobal("XMLHttpRequest", FakeXMLHttpRequest);
    const onUploaded = vi.fn();
    const { container } = render(
      <I18nProvider>
        <FileUpload
          accept="image/png"
          endpoint="/api/users/me/avatar"
          helper="PNG only"
          label="Avatar"
          onUploaded={onUploaded}
        />
      </I18nProvider>,
    );
    const fileInput = container.querySelector('input[type="file"]');
    expect(fileInput).not.toBeNull();
    fireEvent.change(fileInput!, { target: { files: [new File(["data"], "avatar.png", { type: "image/png" })] } });
    fireEvent.click(screen.getByRole("button", { name: "Upload" }));

    expect(await screen.findByText("Upload complete")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveValue(100);
    expect(onUploaded).toHaveBeenCalledWith(expect.objectContaining({ id: 12 }));
    expect(FakeXMLHttpRequest.lastRequest?.method).toBe("POST");
    expect(FakeXMLHttpRequest.lastRequest?.endpoint).toBe("/api/users/me/avatar");
    expect(FakeXMLHttpRequest.lastRequest?.withCredentials).toBe(true);
  });
});
