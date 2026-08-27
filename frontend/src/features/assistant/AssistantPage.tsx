import { useEffect, useRef, useState, type FormEvent } from "react";
import { ArrowUp, BookOpen, Bot, Check, CircleAlert, LoaderCircle, Sparkles, Wrench } from "lucide-react";

import { ApiError } from "../../shared/api";
import { useAuth } from "../auth";
import { streamAssistant, type AssistantHistoryMessage } from "./stream";

interface AssistantSource {
  book_id: number;
  title: string;
  author: string;
  category?: string;
  isbn?: string | null;
}

interface ToolActivity {
  name: string;
  status: string;
}

interface AssistantMessage {
  id: number;
  role: "user" | "assistant";
  text: string;
  sources: AssistantSource[];
  tools: ToolActivity[];
  isStreaming?: boolean;
}

const starterPrompts = [
  "Find a thoughtful science-fiction book for me.",
  "What books are available right now?",
  "Show me my current loans and due dates.",
];

function createMessage(
  id: number,
  role: AssistantMessage["role"],
  text: string,
  isStreaming = false,
): AssistantMessage {
  return { id, role, text, sources: [], tools: [], isStreaming };
}

function sourceFrom(value: unknown): AssistantSource | null {
  if (!value || typeof value !== "object") return null;
  const source = value as Partial<AssistantSource>;
  if (typeof source.book_id !== "number" || typeof source.title !== "string" || typeof source.author !== "string") return null;
  return source as AssistantSource;
}

function toolFrom(value: unknown): ToolActivity | null {
  if (!value || typeof value !== "object") return null;
  const activity = value as Partial<ToolActivity>;
  if (typeof activity.name !== "string") return null;
  return { name: activity.name, status: typeof activity.status === "string" ? activity.status : "running" };
}

function displayToolName(name: string): string {
  return name.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError && error.status === 429) return "You have reached the assistant limit for this minute. Please try again shortly.";
  if (error instanceof ApiError && error.status === 401) return "Sign in again to use the assistant.";
  return error instanceof Error ? error.message : "The assistant could not complete this request.";
}

function SourceList({ sources }: { sources: AssistantSource[] }) {
  if (sources.length === 0) return null;
  return (
    <div className="mt-5 border-t border-slate-200 pt-4">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
        <BookOpen aria-hidden="true" size={15} /> Sources from your catalog
      </div>
      <ul className="mt-3 grid gap-2 sm:grid-cols-2">
        {sources.map((source) => (
          <li className="rounded-xl border border-slate-200 bg-white px-3 py-2.5" key={source.book_id}>
            <a className="font-medium text-sky-800 hover:text-sky-950" href={`/books/${source.book_id}`}>
              {source.title}
            </a>
            <p className="mt-0.5 text-xs text-slate-500">{source.author}{source.category ? ` · ${source.category}` : ""}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ToolList({ tools }: { tools: ToolActivity[] }) {
  if (tools.length === 0) return null;
  return (
    <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
        <Wrench aria-hidden="true" size={14} /> Assistant activity
      </div>
      <ul className="mt-2 space-y-1.5 text-sm text-slate-600">
        {tools.map((tool, index) => (
          <li className="flex items-center gap-2" key={`${tool.name}-${index}`}>
            {tool.status === "completed" ? <Check aria-hidden="true" className="text-emerald-600" size={15} /> : <LoaderCircle aria-hidden="true" className="animate-spin text-sky-600" size={15} />}
            <span>{displayToolName(tool.name)}</span>
            <span className="text-xs text-slate-400">{tool.status === "completed" ? "complete" : "working"}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function AssistantPage() {
  const { user } = useAuth();
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messageId = useRef(0);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => () => abortRef.current?.abort(), []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await ask(draft);
  }

  async function ask(value: string) {
    const message = value.trim();
    if (!message || isStreaming) return;
    const history: AssistantHistoryMessage[] = messages.slice(-10).map(({ role, text: textValue }) => ({ role, text: textValue })).filter(({ text: textValue }) => textValue.trim());
    const userId = ++messageId.current;
    const assistantId = ++messageId.current;
    setMessages((current) => [...current, createMessage(userId, "user", message), createMessage(assistantId, "assistant", "", true)]);
    setDraft("");
    setError(null);
    setIsStreaming(true);
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await streamAssistant(message, history, {
        signal: controller.signal,
        onEvent: ({ type, data }) => {
          if (type === "token" && data && typeof data === "object" && typeof (data as { text?: unknown }).text === "string") {
            const textValue = (data as { text: string }).text;
            setMessages((current) => current.map((item) => item.id === assistantId ? { ...item, text: item.text + textValue } : item));
          } else if (type === "source") {
            const source = sourceFrom(data);
            if (source) setMessages((current) => current.map((item) => item.id === assistantId && !item.sources.some((existing) => existing.book_id === source.book_id) ? { ...item, sources: [...item.sources, source] } : item));
          } else if (type === "tool") {
            const tool = toolFrom(data);
            if (tool) setMessages((current) => current.map((item) => item.id === assistantId ? { ...item, tools: [...item.tools, tool] } : item));
          } else if (type === "error") {
            const messageValue = data && typeof data === "object" && typeof (data as { message?: unknown }).message === "string" ? (data as { message: string }).message : "The assistant could not complete this request.";
            setError(messageValue);
          }
        },
      });
    } catch (streamError) {
      if (!(streamError instanceof DOMException && streamError.name === "AbortError")) setError(errorMessage(streamError));
    } finally {
      setMessages((current) => current.map((item) => item.id === assistantId ? { ...item, isStreaming: false } : item));
      setIsStreaming(false);
      abortRef.current = null;
    }
  }

  return (
    <section className="mx-auto max-w-6xl">
      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <div>
          <div className="flex items-center gap-2 text-sm font-medium uppercase tracking-[0.18em] text-sky-700"><Sparkles aria-hidden="true" size={16} /> LibraryOS assistant</div>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">A helpful guide to your library.</h1>
          <p className="mt-3 max-w-2xl text-slate-600">Ask about the local catalog, current availability, or your loans. Answers are grounded in LibraryOS data and show the books used as sources.</p>
        </div>
        <aside className="rounded-2xl border border-sky-100 bg-sky-50/70 p-5" aria-label="Assistant capabilities">
          <div className="flex items-center gap-2 font-semibold text-slate-950"><Bot aria-hidden="true" className="text-sky-700" size={18} /> I can help with</div>
          <ul className="mt-4 space-y-3 text-sm leading-5 text-slate-600">
            <li>Finding books by mood, topic, or author</li>
            <li>Checking live copy availability</li>
            <li>Reviewing your active loans and due dates</li>
          </ul>
          <p className="mt-5 border-t border-sky-100 pt-4 text-xs leading-5 text-slate-500">Please avoid sharing sensitive information in prompts. Gemini may process your request to generate a response.</p>
        </aside>
      </div>

      <div className="mt-8 overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
        <div className="min-h-[24rem] space-y-5 bg-slate-50/70 p-5 sm:p-8" aria-live="polite" aria-busy={isStreaming}>
          {messages.length === 0 ? (
            <div className="flex min-h-[20rem] flex-col items-center justify-center text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-950 text-white"><Sparkles aria-hidden="true" size={24} /></div>
              <h2 className="mt-5 text-xl font-semibold text-slate-950">What would you like to discover?</h2>
              <p className="mt-2 max-w-md text-sm leading-6 text-slate-600">Start with a question below, or ask your own in plain language.</p>
              <div className="mt-6 flex flex-wrap justify-center gap-2">
                {starterPrompts.map((prompt) => <button className="rounded-full border border-slate-300 bg-white px-3.5 py-2 text-sm text-slate-700 transition hover:border-sky-400 hover:text-sky-800" disabled={isStreaming} key={prompt} onClick={() => void ask(prompt)} type="button">{prompt}</button>)}
              </div>
            </div>
          ) : messages.map((message) => (
            <article className={message.role === "user" ? "ml-auto max-w-2xl" : "max-w-3xl"} key={message.id}>
              <div className={message.role === "user" ? "rounded-2xl rounded-br-md bg-slate-950 px-4 py-3 text-white" : "rounded-2xl rounded-bl-md border border-slate-200 bg-white px-4 py-4 text-slate-800"}>
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] opacity-70">{message.role === "user" ? "You" : <><Bot aria-hidden="true" size={14} /> LibraryOS assistant</>}</div>
                {message.role === "assistant" && message.isStreaming && !message.text ? <div className="mt-3 flex items-center gap-2 text-sm text-slate-500" role="status"><LoaderCircle aria-hidden="true" className="animate-spin" size={16} /> Checking the local catalog…</div> : <p className="mt-2 whitespace-pre-wrap text-sm leading-7">{message.text || "I could not generate a response."}</p>}
                {message.role === "assistant" ? <><ToolList tools={message.tools} /><SourceList sources={message.sources} /></> : null}
              </div>
            </article>
          ))}
        </div>
        {error ? <div className="flex items-start gap-2 border-t border-rose-100 bg-rose-50 px-5 py-3 text-sm text-rose-800 sm:px-8" role="alert"><CircleAlert aria-hidden="true" className="mt-0.5 shrink-0" size={17} /><span>{error}</span></div> : null}
        <form className="border-t border-slate-200 bg-white p-4 sm:p-5" onSubmit={submit}>
          <label className="sr-only" htmlFor="assistant-message">Ask the LibraryOS assistant</label>
          <div className="flex items-end gap-3">
            <textarea aria-describedby="assistant-help" className="min-h-12 flex-1 resize-y rounded-2xl border border-slate-300 px-4 py-3 text-sm text-slate-900 shadow-inner placeholder:text-slate-400" disabled={isStreaming} id="assistant-message" onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} placeholder="Ask about your library…" rows={1} value={draft} />
            <button aria-label={isStreaming ? "Assistant is responding" : "Send message"} className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-slate-950 text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50" disabled={isStreaming || !draft.trim() || !user} type="submit">{isStreaming ? <LoaderCircle aria-hidden="true" className="animate-spin" size={19} /> : <ArrowUp aria-hidden="true" size={20} />}</button>
          </div>
          <p className="mt-2 text-xs text-slate-500" id="assistant-help">Press Enter to send · Shift + Enter for a new line</p>
        </form>
      </div>
    </section>
  );
}
