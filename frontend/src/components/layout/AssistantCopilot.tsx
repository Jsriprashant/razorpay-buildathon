import { useEffect, useMemo, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Bot,
  BrainCircuit,
  Check,
  CheckCircle2,
  ChevronDown,
  Grip,
  CircleStop,
  Clipboard,
  ExternalLink,
  Loader2,
  RotateCcw,
  Send,
  Sparkles,
  Wrench,
  X,
  XCircle,
} from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { api, ApiError, streamApi } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import type {
  AssistantActionResult,
  AssistantConfig,
  AssistantMessage,
  AssistantToolState,
  PendingAssistantAction,
  ReasoningEffort,
} from "@/types";

interface ToolProgress {
  name: string;
  label: string;
  state: AssistantToolState;
}

interface ChatItem extends AssistantMessage {
  id: string;
  tools?: ToolProgress[];
  progress?: string;
  modelUsed?: string;
  streaming?: boolean;
  incomplete?: boolean;
  pendingAction?: PendingAssistantAction;
  actionState?: "pending" | "running" | "complete" | "cancelled";
  link?: string | null;
}

const WELCOME: ChatItem = {
  id: "welcome",
  role: "assistant",
  content:
    "## How can I help?\n\nI can analyze live headcount and budget data, compare forecast scenarios, review hiring requests, and prepare changes for your confirmation.",
};

const STARTERS = [
  "Summarize our current headcount and budget position",
  "Show the biggest forecast risks in a table",
  "Compare a 2-month hiring delay with the baseline",
];

const REASONING_OPTIONS: Array<{ id: ReasoningEffort; label: string }> = [
  { id: "none", label: "Fast" },
  { id: "low", label: "Light" },
  { id: "medium", label: "Balanced" },
  { id: "high", label: "Deep" },
  { id: "max", label: "Maximum" },
];

function newId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function errorMessage(error: unknown) {
  if (error instanceof DOMException && error.name === "AbortError") return "Response stopped.";
  return error instanceof ApiError ? error.message : "Something went wrong. Please try again.";
}

function friendlyModelName(config: AssistantConfig | undefined, id: string) {
  return config?.models.find((option) => option.id === id)?.label ?? id;
}

function formatActionValue(key: string, value: unknown) {
  if (value === null || value === undefined || value === "") return "Not set";
  if (key.endsWith("_cents") && typeof value === "number") {
    return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value / 100);
  }
  return String(value);
}

function MarkdownAnswer({ children }: { children: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children: content }) => (
          <h1 className="mb-2 mt-4 text-lg font-semibold leading-tight first:mt-0">{content}</h1>
        ),
        h2: ({ children: content }) => (
          <h2 className="mb-2 mt-4 text-base font-semibold leading-tight first:mt-0">{content}</h2>
        ),
        h3: ({ children: content }) => (
          <h3 className="mb-1.5 mt-3 text-sm font-semibold first:mt-0">{content}</h3>
        ),
        p: ({ children: content }) => <p className="my-2 leading-6 first:mt-0 last:mb-0">{content}</p>,
        ul: ({ children: content }) => <ul className="my-2 list-disc space-y-1 pl-5">{content}</ul>,
        ol: ({ children: content }) => <ol className="my-2 list-decimal space-y-1 pl-5">{content}</ol>,
        li: ({ children: content }) => <li className="pl-0.5 leading-5">{content}</li>,
        strong: ({ children: content }) => <strong className="font-semibold text-foreground">{content}</strong>,
        blockquote: ({ children: content }) => (
          <blockquote className="my-3 border-l-2 border-primary pl-3 text-muted-foreground">{content}</blockquote>
        ),
        table: ({ children: content }) => (
          <div className="my-3 max-w-full overflow-x-auto rounded-xl border border-border bg-background">
            <table className="w-full min-w-[420px] border-collapse text-left text-xs">{content}</table>
          </div>
        ),
        thead: ({ children: content }) => <thead className="bg-muted/70">{content}</thead>,
        th: ({ children: content }) => (
          <th className="border-b border-border px-3 py-2 font-semibold text-foreground">{content}</th>
        ),
        td: ({ children: content }) => (
          <td className="border-b border-border/70 px-3 py-2 align-top last:border-b-0">{content}</td>
        ),
        code: ({ className, children: content }) =>
          className ? (
            <code className="block overflow-x-auto rounded-xl bg-foreground p-3 text-xs text-background">{content}</code>
          ) : (
            <code className="rounded bg-primary/10 px-1.5 py-0.5 text-[0.9em] text-primary">{content}</code>
          ),
        a: ({ href, children: content }) => (
          <a href={href} target="_blank" rel="noreferrer" className="font-medium text-primary underline underline-offset-2">
            {content}
          </a>
        ),
        hr: () => <hr className="my-4 border-border" />,
      }}
    >
      {children}
    </ReactMarkdown>
  );
}

function ActivityTrail({ progress, tools }: { progress?: string; tools?: ToolProgress[] }) {
  if (!progress && !tools?.length) return null;
  return (
    <div className="mb-3 overflow-hidden rounded-xl border border-border bg-background/80">
      {progress && (
        <div className="flex items-center gap-2 border-b border-border px-3 py-2 text-xs text-muted-foreground last:border-b-0">
          <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
          {progress}
        </div>
      )}
      {tools?.map((tool) => (
        <div key={tool.name} className="flex items-center gap-2 border-b border-border px-3 py-2 text-xs last:border-b-0">
          {tool.state === "running" && <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />}
          {tool.state === "complete" && <CheckCircle2 className="h-3.5 w-3.5 text-success" />}
          {tool.state === "error" && <XCircle className="h-3.5 w-3.5 text-destructive" />}
          <span className={tool.state === "error" ? "text-destructive" : "text-muted-foreground"}>{tool.label}</span>
        </div>
      ))}
    </div>
  );
}

function ActionCard({
  message,
  onConfirm,
  onCancel,
}: {
  message: ChatItem;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!message.pendingAction) return null;
  const action = message.pendingAction;
  const detailRows = Object.entries(action.payload).filter(([, value]) => value !== null && value !== "");
  return (
    <div className="mt-4 overflow-hidden rounded-2xl border border-primary/25 bg-background shadow-card">
      <div className="border-b border-border bg-primary/5 px-4 py-3">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-primary">
          <Wrench className="h-3.5 w-3.5" />
          Review action
        </div>
        <p className="mt-1.5 font-semibold text-foreground">{action.title}</p>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">{action.description}</p>
      </div>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 px-4 py-3 text-xs">
        {detailRows.map(([key, value]) => (
          <div key={key} className="min-w-0">
            <dt className="truncate text-muted-foreground">{key.replace(/_/g, " ")}</dt>
            <dd className="mt-0.5 break-words font-medium text-foreground">{formatActionValue(key, value)}</dd>
          </div>
        ))}
      </dl>
      <div className="border-t border-border px-4 py-3">
        {message.actionState === "pending" && (
          <div className="flex gap-2">
            <Button size="sm" onClick={onConfirm}>
              <Check className="h-3.5 w-3.5" />
              Confirm action
            </Button>
            <Button size="sm" variant="ghost" onClick={onCancel}>
              Cancel
            </Button>
          </div>
        )}
        {message.actionState === "running" && (
          <p className="flex items-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="h-3.5 w-3.5 animate-spin" /> Applying confirmed change…
          </p>
        )}
        {message.actionState === "complete" && (
          <div className="flex items-center justify-between text-xs text-success">
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="h-4 w-4" /> Change completed
            </span>
            {message.link && (
              <Link className="flex items-center gap-1 font-medium hover:underline" to={message.link}>
                Open result <ExternalLink className="h-3 w-3" />
              </Link>
            )}
          </div>
        )}
        {message.actionState === "cancelled" && (
          <p className="text-xs text-muted-foreground">Cancelled. No data was changed.</p>
        )}
      </div>
    </div>
  );
}

export function AssistantCopilot() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatItem[]>([WELCOME]);
  const [model, setModel] = useState("auto");
  const [reasoningEffort, setReasoningEffort] = useState<ReasoningEffort>("medium");
  const [openSelector, setOpenSelector] = useState<"model" | "reasoning" | null>(null);
  const [windowSize, setWindowSize] = useState({ width: 620, height: 780 });
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const selectorRef = useRef<HTMLDivElement>(null);

  const { data: config } = useQuery<AssistantConfig>({
    queryKey: ["assistant", "config"],
    queryFn: () => api.get<AssistantConfig>("/assistant/config"),
    enabled: open,
    staleTime: Infinity,
  });

  const history = useMemo<AssistantMessage[]>(
    () =>
      messages
        .filter((message) => message.id !== "welcome" && !message.streaming && message.content.trim())
        .filter((message) => !message.incomplete)
        .map(({ role, content }) => ({ role, content }))
        .slice(-20),
    [messages],
  );

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  useEffect(() => () => abortRef.current?.abort(), []);

  useEffect(() => {
    function closeSelectors(event: MouseEvent) {
      if (!selectorRef.current?.contains(event.target as Node)) setOpenSelector(null);
    }
    document.addEventListener("mousedown", closeSelectors);
    return () => document.removeEventListener("mousedown", closeSelectors);
  }, []);

  function startResize(event: ReactPointerEvent<HTMLButtonElement>) {
    if (window.innerWidth < 640) return;
    event.preventDefault();
    const startX = event.clientX;
    const startY = event.clientY;
    const startWidth = windowSize.width;
    const startHeight = windowSize.height;

    function resize(moveEvent: PointerEvent) {
      const maxWidth = Math.max(420, window.innerWidth - 40);
      const maxHeight = Math.max(520, window.innerHeight - 24);
      setWindowSize({
        width: Math.min(maxWidth, Math.max(420, startWidth + startX - moveEvent.clientX)),
        height: Math.min(maxHeight, Math.max(520, startHeight + startY - moveEvent.clientY)),
      });
    }

    function stopResize() {
      document.removeEventListener("pointermove", resize);
      document.removeEventListener("pointerup", stopResize);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    }

    document.body.style.cursor = "nwse-resize";
    document.body.style.userSelect = "none";
    document.addEventListener("pointermove", resize);
    document.addEventListener("pointerup", stopResize);
  }

  const actionMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: PendingAssistantAction }) =>
      api.post<AssistantActionResult>("/assistant/actions/confirm", { action }).then((result) => ({ id, result })),
    onMutate: ({ id }) => {
      setMessages((current) =>
        current.map((message) => (message.id === id ? { ...message, actionState: "running" } : message)),
      );
    },
    onSuccess: ({ id, result }) => {
      setMessages((current) =>
        current.map((message) =>
          message.id === id
            ? {
                ...message,
                actionState: "complete",
                content: `${message.content}\n\n> ${result.message}`,
                link: result.link,
              }
            : message,
        ),
      );
      queryClient.invalidateQueries();
    },
    onError: (error, { id }) => {
      setMessages((current) =>
        current.map((message) =>
          message.id === id
            ? { ...message, actionState: "pending", content: `${message.content}\n\n> ${errorMessage(error)}` }
            : message,
        ),
      );
    },
  });

  const selectedModel = config?.models.find((option) => option.id === model);
  const reasoningDisabled = selectedModel ? !selectedModel.supports_reasoning : false;

  async function send(message = input) {
    const trimmed = message.trim();
    if (!trimmed || isStreaming) return;
    const assistantId = newId();
    setMessages((current) => [
      ...current,
      { id: newId(), role: "user", content: trimmed },
      {
        id: assistantId,
        role: "assistant",
        content: "",
        progress: "Connecting to live workspace data",
        streaming: true,
        tools: [],
      },
    ]);
    setInput("");
    setIsStreaming(true);
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await streamApi(
        "/assistant/chat/stream",
        {
          message: trimmed,
          history,
          model,
          reasoning_effort: reasoningDisabled ? "none" : reasoningEffort,
        },
        (event, data) => {
          if (abortRef.current !== controller) return;
          setMessages((current) =>
            current.map((item) => {
              if (item.id !== assistantId) return item;
              if (event === "status") {
                return {
                  ...item,
                  progress: String(data.label ?? "Working"),
                  modelUsed: data.model_used ? String(data.model_used) : item.modelUsed,
                };
              }
              if (event === "tool") {
                const tool: ToolProgress = {
                  name: String(data.name),
                  label: String(data.label),
                  state: data.state as AssistantToolState,
                };
                const existing = item.tools ?? [];
                return {
                  ...item,
                  progress: tool.state === "running" ? `Using ${tool.label.toLowerCase()}` : item.progress,
                  tools: existing.some((entry) => entry.name === tool.name)
                    ? existing.map((entry) => (entry.name === tool.name ? tool : entry))
                    : [...existing, tool],
                };
              }
              if (event === "answer_delta") {
                return {
                  ...item,
                  content: item.content + String(data.delta ?? ""),
                  progress: undefined,
                };
              }
              if (event === "done") {
                return {
                  ...item,
                  content: item.content || String(data.answer ?? ""),
                  progress: undefined,
                  streaming: false,
                  modelUsed: String(data.model_used ?? item.modelUsed ?? ""),
                  pendingAction: (data.pending_action as PendingAssistantAction | null) ?? undefined,
                  actionState: data.pending_action ? "pending" : undefined,
                };
              }
              if (event === "error") {
                return {
                  ...item,
                  content: item.content || `**I couldn't complete that request.**\n\n${String(data.message)}`,
                  progress: undefined,
                  streaming: false,
                  incomplete: true,
                };
              }
              return item;
            }),
          );
          if (event === "done" || event === "error") setIsStreaming(false);
        },
        controller.signal,
      );
    } catch (error) {
      if (abortRef.current !== controller) return;
      setMessages((current) =>
        current.map((item) =>
          item.id === assistantId
            ? {
                ...item,
                content:
                  error instanceof DOMException && error.name === "AbortError"
                    ? `${item.content}${item.content ? "\n\n" : ""}> Response stopped. Partial output was not added to conversation history.`
                    : item.content || `**I couldn't complete that request.**\n\n${errorMessage(error)}`,
                progress: undefined,
                streaming: false,
                incomplete: true,
              }
            : item,
        ),
      );
    } finally {
      if (abortRef.current === controller) {
        setIsStreaming(false);
        abortRef.current = null;
      }
    }
  }

  function stop() {
    abortRef.current?.abort();
  }

  function reset() {
    const active = abortRef.current;
    abortRef.current = null;
    active?.abort();
    setMessages([WELCOME]);
    setInput("");
    setIsStreaming(false);
  }

  function cancelAction(id: string) {
    setMessages((current) =>
      current.map((message) => (message.id === id ? { ...message, actionState: "cancelled" } : message)),
    );
  }

  if (!user) return null;

  return (
    <>
      {!open && (
        <Button
          className="fixed bottom-5 right-5 z-50 h-12 rounded-full px-5 shadow-card-hover"
          onClick={() => setOpen(true)}
          aria-label="Open CONTINUUM Copilot"
        >
          <Sparkles className="h-4 w-4" />
          Ask Copilot
        </Button>
      )}

      {open && (
        <section
          className="fixed inset-x-3 bottom-3 z-50 flex h-[calc(100vh-24px)] flex-col overflow-hidden rounded-2xl border border-border bg-card shadow-popover sm:left-auto sm:right-5"
          style={{
            width: `min(${windowSize.width}px, calc(100vw - 40px))`,
            height: `min(${windowSize.height}px, calc(100vh - 24px))`,
          }}
          aria-label="CONTINUUM Copilot"
        >
          <button
            type="button"
            onPointerDown={startResize}
            className="absolute left-0 top-0 z-20 hidden h-8 w-8 cursor-nwse-resize items-center justify-center rounded-br-xl text-muted-foreground/50 transition-colors hover:bg-accent hover:text-primary sm:flex"
            aria-label="Resize copilot window"
            title="Drag to resize"
          >
            <Grip className="h-3.5 w-3.5 rotate-90" />
          </button>
          <header className="flex items-center justify-between border-b border-border bg-card px-4 py-3">
              <div className="flex items-center gap-3 pl-2 sm:pl-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary">
                <Bot className="h-5 w-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold text-foreground">CONTINUUM Copilot</p>
                  <span className="flex items-center gap-1 rounded-full bg-success/10 px-2 py-0.5 text-[10px] font-medium text-success">
                    <span className="h-1.5 w-1.5 rounded-full bg-success" />
                    Live data
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">Analysis, scenarios, and confirmed actions</p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <Button size="icon" variant="ghost" onClick={reset} aria-label="Start a new conversation" title="New conversation">
                <RotateCcw className="h-4 w-4" />
              </Button>
              <Button size="icon" variant="ghost" onClick={() => setOpen(false)} aria-label="Close copilot">
                <X className="h-4 w-4" />
              </Button>
            </div>
          </header>

          <div ref={scrollRef} className="flex-1 space-y-5 overflow-y-auto bg-background/60 p-4">
            {messages.map((message) => (
              <div key={message.id} className={message.role === "user" ? "ml-12 flex justify-end" : "mr-2"}>
                <div
                  className={cn(
                    "max-w-full text-sm",
                    message.role === "user"
                      ? "rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-primary-foreground"
                      : "w-full rounded-2xl rounded-bl-md border border-border bg-card p-4 text-foreground shadow-card",
                  )}
                >
                  {message.role === "assistant" && (
                    <div className="mb-3 flex items-center justify-between">
                      <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                        <Sparkles className="h-3.5 w-3.5 text-primary" />
                        Copilot
                      </div>
                      {message.modelUsed && (
                        <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground">
                          {friendlyModelName(config, message.modelUsed)}
                        </span>
                      )}
                    </div>
                  )}

                  <ActivityTrail progress={message.progress} tools={message.tools} />
                  {message.role === "assistant" ? (
                    message.content ? (
                      <MarkdownAnswer>{message.content}</MarkdownAnswer>
                    ) : null
                  ) : (
                    <p className="whitespace-pre-wrap leading-6">{message.content}</p>
                  )}
                  {message.streaming && message.content && (
                    <span className="ml-1 inline-block h-4 w-1 animate-pulse rounded-full bg-primary align-middle" />
                  )}

                  <ActionCard
                    message={message}
                    onConfirm={() => actionMutation.mutate({ id: message.id, action: message.pendingAction! })}
                    onCancel={() => cancelAction(message.id)}
                  />

                  {message.role === "assistant" && message.content && !message.streaming && (
                    <div className="mt-3 flex items-center justify-end border-t border-border pt-2">
                      <button
                        type="button"
                        className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground"
                        onClick={() => navigator.clipboard.writeText(message.content)}
                      >
                        <Clipboard className="h-3 w-3" /> Copy
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {messages.length === 1 && (
              <div className="grid gap-2 sm:grid-cols-3">
                {STARTERS.map((starter) => (
                  <button
                    key={starter}
                    type="button"
                    className="rounded-xl border border-border bg-card px-3 py-3 text-left text-xs leading-5 text-foreground shadow-card transition-all hover:border-primary/30 hover:bg-accent hover:shadow-card-hover"
                    onClick={() => send(starter)}
                  >
                    {starter}
                  </button>
                ))}
              </div>
            )}
          </div>

          <form
            className="border-t border-border bg-card p-3"
            onSubmit={(event) => {
              event.preventDefault();
              send();
            }}
          >
            <div className="overflow-hidden rounded-2xl border border-input bg-background transition-shadow focus-within:ring-2 focus-within:ring-ring">
              <textarea
                rows={3}
                className="max-h-36 min-h-16 w-full resize-none bg-transparent px-4 pt-3 text-sm leading-5 outline-none placeholder:text-muted-foreground"
                placeholder="Ask a question, compare a scenario, or prepare an action…"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    send();
                  }
                }}
              />
              <div className="flex items-center justify-between gap-2 border-t border-border/70 px-2 py-2">
                <div ref={selectorRef} className="relative flex min-w-0 items-center gap-1.5">
                  <div className="relative">
                    <button
                      type="button"
                      onClick={() => setOpenSelector((current) => (current === "model" ? null : "model"))}
                      className={cn(
                        "flex h-8 max-w-40 items-center gap-1.5 rounded-full border px-2.5 text-xs font-medium transition-all",
                        openSelector === "model"
                          ? "border-primary/30 bg-gradient-blue-soft text-primary shadow-card"
                          : "border-border bg-card text-foreground hover:border-primary/20 hover:bg-accent",
                      )}
                      aria-label="Choose AI model"
                      aria-expanded={openSelector === "model"}
                    >
                      <Sparkles className="h-3.5 w-3.5 shrink-0 text-primary" />
                      <span className="truncate">{friendlyModelName(config, model)}</span>
                      <ChevronDown className={cn("h-3 w-3 shrink-0 text-muted-foreground transition-transform", openSelector === "model" && "rotate-180")} />
                    </button>
                    {openSelector === "model" && (
                      <div className="absolute bottom-10 left-0 z-30 w-56 overflow-hidden rounded-2xl border border-border bg-card p-1.5 shadow-popover">
                        <p className="px-2.5 pb-1.5 pt-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                          Choose model
                        </p>
                        {(config?.models ?? [{ id: "auto", label: "Auto", supports_reasoning: true }]).map((option) => (
                          <button
                            key={option.id}
                            type="button"
                            onClick={() => {
                              setModel(option.id);
                              setOpenSelector(null);
                            }}
                            className={cn(
                              "flex w-full items-center justify-between rounded-xl px-2.5 py-2 text-left text-xs transition-colors",
                              model === option.id ? "bg-gradient-blue-soft font-semibold text-primary" : "text-foreground hover:bg-accent",
                            )}
                          >
                            <span>{option.label}</span>
                            {model === option.id && <Check className="h-3.5 w-3.5" />}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="relative">
                    <button
                      type="button"
                      disabled={reasoningDisabled}
                      onClick={() => setOpenSelector((current) => (current === "reasoning" ? null : "reasoning"))}
                      className={cn(
                        "flex h-8 max-w-36 items-center gap-1.5 rounded-full border px-2.5 text-xs font-medium transition-all disabled:cursor-not-allowed disabled:opacity-50",
                        openSelector === "reasoning"
                          ? "border-primary/30 bg-gradient-blue-soft text-primary shadow-card"
                          : "border-border bg-card text-foreground hover:border-primary/20 hover:bg-accent",
                      )}
                      aria-label="Choose reasoning effort"
                      aria-expanded={openSelector === "reasoning"}
                    >
                      <BrainCircuit className="h-3.5 w-3.5 shrink-0 text-primary" />
                      <span className="truncate">
                        {REASONING_OPTIONS.find((option) => option.id === (reasoningDisabled ? "none" : reasoningEffort))?.label}
                      </span>
                      <ChevronDown className={cn("h-3 w-3 shrink-0 text-muted-foreground transition-transform", openSelector === "reasoning" && "rotate-180")} />
                    </button>
                    {openSelector === "reasoning" && (
                      <div className="absolute bottom-10 left-0 z-30 w-52 overflow-hidden rounded-2xl border border-border bg-card p-1.5 shadow-popover">
                        <p className="px-2.5 pb-1.5 pt-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                          Reasoning effort
                        </p>
                        {REASONING_OPTIONS.map((option) => (
                          <button
                            key={option.id}
                            type="button"
                            onClick={() => {
                              setReasoningEffort(option.id);
                              setOpenSelector(null);
                            }}
                            className={cn(
                              "flex w-full items-center justify-between rounded-xl px-2.5 py-2 text-left text-xs transition-colors",
                              reasoningEffort === option.id ? "bg-gradient-blue-soft font-semibold text-primary" : "text-foreground hover:bg-accent",
                            )}
                          >
                            <span>{option.label}</span>
                            {reasoningEffort === option.id && <Check className="h-3.5 w-3.5" />}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {isStreaming ? (
                  <Button size="sm" type="button" variant="outline" className="shrink-0" onClick={stop}>
                    <CircleStop className="h-3.5 w-3.5" />
                    Stop
                  </Button>
                ) : (
                  <Button size="icon" type="submit" className="h-9 w-9 shrink-0" disabled={!input.trim()}>
                    <Send className="h-4 w-4" />
                  </Button>
                )}
              </div>
            </div>
            <p className="mt-2 text-center text-[10px] text-muted-foreground">
              Live progress shows verified tool activity, not private hidden reasoning. Every data change requires confirmation.
            </p>
          </form>
        </section>
      )}
    </>
  );
}