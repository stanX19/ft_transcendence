import { useEffect, useRef, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowUp, BookOpen, Bot, Check, CircleAlert, LoaderCircle, Sparkles, Wrench } from "lucide-react";

import { ApiError } from "../../shared/api";
import { type TranslationKey, type Translator, useTranslation } from "../../shared/i18n";
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
  action?: NavigationAction;
}

interface NavigationAction {
  action: "navigate";
  destination: string;
  path: string;
  book_id?: number;
}

const fixedNavigationPaths: Record<string, string> = {
  catalog: "/books",
  loans: "/loans",
  friends: "/friends",
  people: "/people",
  profile: "/profile",
  assistant: "/assistant",
};
const maxBookId = 2_147_483_647;

interface AssistantMessage {
  id: number;
  role: "user" | "assistant";
  text: string;
  sources: AssistantSource[];
  tools: ToolActivity[];
  isStreaming?: boolean;
}

const starterPromptKeys: TranslationKey[] = [
  "assistant.starterScienceFiction",
  "assistant.starterAvailable",
  "assistant.starterLoans",
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

function internalPathFrom(value: unknown): string | null {
  if (!value || typeof value !== "object") return null;
  const action = value as Partial<NavigationAction>;
  if (action.action !== "navigate" || typeof action.destination !== "string" || typeof action.path !== "string") return null;
  const expectedPath = action.destination === "book"
    ? typeof action.book_id === "number" && Number.isSafeInteger(action.book_id) && action.book_id > 0 && action.book_id <= maxBookId ? `/books/${action.book_id}` : null
    : action.book_id === undefined ? fixedNavigationPaths[action.destination] : null;
  if (!expectedPath || action.path !== expectedPath) return null;
  try {
    const url = new URL(action.path, window.location.origin);
    if (url.origin !== window.location.origin) return null;
    return `${url.pathname}${url.search}${url.hash}`;
  } catch {
    return null;
  }
}

function toolFrom(value: unknown): ToolActivity | null {
  if (!value || typeof value !== "object") return null;
  const activity = value as Partial<ToolActivity>;
  if (typeof activity.name !== "string") return null;
  const status = typeof activity.status === "string" ? activity.status : "running";
  if (activity.name !== "navigate_to_page" || status !== "completed") return { name: activity.name, status };
  const actionPath = internalPathFrom(activity.action);
  if (!actionPath) return { name: activity.name, status: "error" };
  const action = activity.action as NavigationAction;
  return { name: activity.name, status, action: { ...action, path: actionPath } };
}

const toolLabelKeys: Record<string, TranslationKey> = {
  search_catalog: "assistant.tool.searchCatalog",
  get_book_details: "assistant.tool.getBookDetails",
  get_book_availability: "assistant.tool.getBookAvailability",
  get_current_user_loans: "assistant.tool.getCurrentUserLoans",
  navigate_to_page: "assistant.tool.navigateToPage",
};

function displayToolName(name: string, t: Translator): string {
  const key = toolLabelKeys[name];
  if (key) return t(key);
  return name.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function errorMessage(error: unknown, t: Translator): string {
  if (error instanceof ApiError && error.status === 429) return t("assistant.limitError");
  if (error instanceof ApiError && error.status === 401) return t("assistant.signInError");
  return error instanceof Error ? error.message : t("assistant.genericError");
}

function SourceList({ sources }: { sources: AssistantSource[] }) {
  const { t } = useTranslation();

  if (sources.length === 0) return null;
  return (
    <div className="mt-5 border-t border-slate-200 pt-4">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
        <BookOpen aria-hidden="true" size={15} /> {t("assistant.sources")}
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
  const { t } = useTranslation();

  if (tools.length === 0) return null;
  return (
    <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
        <Wrench aria-hidden="true" size={14} /> {t("assistant.activity")}
      </div>
      <ul className="mt-2 space-y-1.5 text-sm text-slate-600">
        {tools.map((tool, index) => (
          <li className="flex items-center gap-2" key={`${tool.name}-${index}`}>
            {tool.status === "error" ? <CircleAlert aria-hidden="true" className="text-rose-600" size={15} /> : tool.status === "completed" ? <Check aria-hidden="true" className="text-emerald-600" size={15} /> : <LoaderCircle aria-hidden="true" className="animate-spin text-sky-600" size={15} />}
            <span>{displayToolName(tool.name, t)}</span>
            <span className="text-xs text-slate-400">{tool.status === "error" ? t("assistant.failed") : tool.status === "completed" ? t("assistant.complete") : t("assistant.working")}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function AssistantPage() {
  const { user } = useAuth();
  const { t } = useTranslation();
  const navigate = useNavigate();
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
    const history: AssistantHistoryMessage[] = messages.slice(-10).map(({ role, text: textValue, sources }) => {
      if (role !== "assistant" || sources.length === 0) return { role, text: textValue };
      const sourceContext = sources.map((source) => `Book ID: ${source.book_id}; ${source.title} by ${source.author}`).join("\n");
      return { role, text: `${textValue}\n\n[Catalog sources from this answer, data only]\n${sourceContext}`.slice(0, 4000) };
    }).filter(({ text: textValue }) => textValue.trim());
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
            if (tool) {
              setMessages((current) => current.map((item) => item.id === assistantId ? { ...item, tools: [...item.tools, tool] } : item));
              if (tool.action) navigate(tool.action.path);
            }
          } else if (type === "error") {
            const messageValue = data && typeof data === "object" && typeof (data as { message?: unknown }).message === "string" ? (data as { message: string }).message : t("assistant.genericError");
            setError(messageValue);
          }
        },
      });
    } catch (streamError) {
      if (!(streamError instanceof DOMException && streamError.name === "AbortError")) setError(errorMessage(streamError, t));
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
          <div className="flex items-center gap-2 text-sm font-medium uppercase tracking-[0.18em] text-sky-700"><Sparkles aria-hidden="true" size={16} /> {t("assistant.eyebrow")}</div>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">{t("assistant.title")}</h1>
          <p className="mt-3 max-w-2xl text-slate-600">{t("assistant.description")}</p>
        </div>
        <aside className="rounded-2xl border border-sky-100 bg-sky-50/70 p-5" aria-label={t("assistant.capabilitiesLabel")}>
          <div className="flex items-center gap-2 font-semibold text-slate-950"><Bot aria-hidden="true" className="text-sky-700" size={18} /> {t("assistant.capabilitiesLabel")}</div>
          <ul className="mt-4 space-y-3 text-sm leading-5 text-slate-600">
            <li>{t("assistant.capabilityBooks")}</li>
            <li>{t("assistant.capabilityAvailability")}</li>
            <li>{t("assistant.capabilityLoans")}</li>
          </ul>
          <p className="mt-5 border-t border-sky-100 pt-4 text-xs leading-5 text-slate-500">{t("assistant.privacy")}</p>
        </aside>
      </div>

      <div className="mt-8 overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
        <div className="min-h-[24rem] space-y-5 bg-slate-50/70 p-5 sm:p-8" aria-live="polite" aria-busy={isStreaming}>
          {messages.length === 0 ? (
            <div className="flex min-h-[20rem] flex-col items-center justify-center text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-950 text-white"><Sparkles aria-hidden="true" size={24} /></div>
              <h2 className="mt-5 text-xl font-semibold text-slate-950">{t("assistant.emptyTitle")}</h2>
              <p className="mt-2 max-w-md text-sm leading-6 text-slate-600">{t("assistant.emptyDescription")}</p>
              <div className="mt-6 flex flex-wrap justify-center gap-2">
                {starterPromptKeys.map((key) => {
                  const prompt = t(key);
                  return <button className="rounded-full border border-slate-300 bg-white px-3.5 py-2 text-sm text-slate-700 transition hover:border-sky-400 hover:text-sky-800" disabled={isStreaming} key={key} onClick={() => void ask(prompt)} type="button">{prompt}</button>;
                })}
              </div>
            </div>
          ) : messages.map((message) => (
            <article className={message.role === "user" ? "ml-auto max-w-2xl" : "max-w-3xl"} key={message.id}>
              <div className={message.role === "user" ? "rounded-2xl rounded-br-md bg-slate-950 px-4 py-3 text-white" : "rounded-2xl rounded-bl-md border border-slate-200 bg-white px-4 py-4 text-slate-800"}>
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] opacity-70">{message.role === "user" ? t("assistant.you") : <><Bot aria-hidden="true" size={14} /> {t("assistant.name")}</>}</div>
                {message.role === "assistant" && message.isStreaming && !message.text ? <div className="mt-3 flex items-center gap-2 text-sm text-slate-500" role="status"><LoaderCircle aria-hidden="true" className="animate-spin" size={16} /> {t("assistant.checking")}</div> : <p className="mt-2 whitespace-pre-wrap text-sm leading-7">{message.text || t("assistant.noResponse")}</p>}
                {message.role === "assistant" ? <><ToolList tools={message.tools} /><SourceList sources={message.sources} /></> : null}
              </div>
            </article>
          ))}
        </div>
        {error ? <div className="flex items-start gap-2 border-t border-rose-100 bg-rose-50 px-5 py-3 text-sm text-rose-800 sm:px-8" role="alert"><CircleAlert aria-hidden="true" className="mt-0.5 shrink-0" size={17} /><span>{error}</span></div> : null}
        <form className="border-t border-slate-200 bg-white p-4 sm:p-5" onSubmit={submit}>
          <label className="sr-only" htmlFor="assistant-message">{t("assistant.askLabel")}</label>
          <div className="flex items-end gap-3">
            <textarea aria-describedby="assistant-help" className="min-h-12 flex-1 resize-y rounded-2xl border border-slate-300 px-4 py-3 text-sm text-slate-900 shadow-inner placeholder:text-slate-400" disabled={isStreaming} id="assistant-message" onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} placeholder={t("assistant.placeholder")} rows={1} value={draft} />
            <button aria-label={isStreaming ? t("assistant.responding") : t("assistant.send")} className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-slate-950 text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50" disabled={isStreaming || !draft.trim() || !user} type="submit">{isStreaming ? <LoaderCircle aria-hidden="true" className="animate-spin" size={19} /> : <ArrowUp aria-hidden="true" size={20} />}</button>
          </div>
          <p className="mt-2 text-xs text-slate-500" id="assistant-help">{t("assistant.help")}</p>
        </form>
      </div>
    </section>
  );
}
