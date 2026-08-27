import { ApiError } from "../../shared/api";

export interface AssistantHistoryMessage {
  role: "user" | "assistant";
  text: string;
}

export interface AssistantStreamEvent {
  type: string;
  data: unknown;
}

interface StreamOptions {
  signal?: AbortSignal;
  onEvent: (event: AssistantStreamEvent) => void;
}

function parseErrorBody(text: string): { code?: string; message?: string } {
  try {
    const body = JSON.parse(text) as { error?: { code?: string; message?: string } };
    return body.error ?? {};
  } catch {
    return {};
  }
}

function emitRecord(record: string, onEvent: (event: AssistantStreamEvent) => void): void {
  let type = "message";
  const dataLines: string[] = [];
  for (const line of record.split(/\r?\n/)) {
    if (line.startsWith("event:")) type = line.slice(6).trim();
    if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
  }
  if (dataLines.length === 0) return;
  const rawData = dataLines.join("\n");
  let data: unknown = rawData;
  try {
    data = JSON.parse(rawData) as unknown;
  } catch {
    // Keep non-JSON event data usable for a future provider implementation.
  }
  onEvent({ type, data });
}

export async function streamAssistant(
  message: string,
  history: AssistantHistoryMessage[],
  { signal, onEvent }: StreamOptions,
): Promise<void> {
  const response = await fetch("/api/ai/chat/stream", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ message, history }),
    signal,
  });

  if (!response.ok) {
    const body = parseErrorBody(await response.text());
    throw new ApiError(
      response.status,
      body.code ?? "assistant_request_failed",
      body.message ?? "The assistant could not start this request.",
    );
  }
  if (!response.body) {
    throw new Error("The assistant stream was unavailable.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
    const records = buffer.split(/\r?\n\r?\n/);
    buffer = records.pop() ?? "";
    records.forEach((record) => emitRecord(record, onEvent));
    if (done) break;
  }
  if (buffer.trim()) emitRecord(buffer, onEvent);
}
