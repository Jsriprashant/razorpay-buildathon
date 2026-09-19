import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, Check, ExternalLink, Loader2, Send, Settings2, Sparkles, X } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type {
  AssistantActionResult,
  AssistantChatResponse,
  AssistantConfig,
  AssistantMessage,
  PendingAssistantAction,
  ReasoningEffort,
} from "@/types";

interface ChatItem extends AssistantMessage {
  id: string;
  tools?: string[];
  pendingAction?: PendingAssistantAction;
  actionState?: "pending" | "running" | "complete" | "cancelled";
  link?: string | null;
}

const WELCOME: ChatItem = {
  id: "welcome",
  role: "assistant",
  content:
    "Ask me about headcount, hiring requests, costs, or forecast scenarios. I can also prepare actions for your approval.",
};

const STARTERS = [
  "Summarize our current headcount and budget position",
  "What are the biggest forecast risks?",
  "Compare a 2-month hiring delay with the baseline",
];

function newId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function errorMessage(error: unknown) {
  return error instanceof ApiError ? error.message : "Something went wrong. Please try again.";
}

export function AssistantCopilot() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatItem[]>([WELCOME]);
  const [model, setModel] = useState("auto");
  const [reasoningEffort, setReasoningEffort] = useState<ReasoningEffort>("medium");

  const { data: config } = useQuery<AssistantConfig>({
    queryKey: ["assistant", "config"],
    queryFn: () => api.get<AssistantConfig>("/assistant/config"),
    enabled: open,
    staleTime: Infinity,
  });

  const history = useMemo<AssistantMessage[]>(
    () =>
      messages
        .filter((message) => message.id !== "welcome")
        .map(({ role, content }) => ({ role, content }))
        .slice(-20),
    [messages],
  );

  const chatMutation = useMutation({
    mutationFn: (message: string) =>
      api.post<AssistantChatResponse>("/assistant/chat", {
        message,
        history,
        model,
        reasoning_effort: reasoningEffort,
      }),
    onSuccess: (result) => {
      setMessages((current) => [
        ...current,
        {
          id: newId(),
          role: "assistant",
          content: result.answer,
          tools: result.tool_activity.map((activity) => activity.label),
          pendingAction: result.pending_action ?? undefined,
          actionState: result.pending_action ? "pending" : undefined,
        },
      ]);
    },
    onError: (error) => {
      setMessages((current) => [
        ...current,
        { id: newId(), role: "assistant", content: errorMessage(error) },
      ]);
    },
  });

  const actionMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: PendingAssistantAction }) =>
      api
        .post<AssistantActionResult>("/assistant/actions/confirm", { action })
        .then((result) => ({ id, result })),
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
                content: `${message.content}\n\n${result.message}`,
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
            ? { ...message, actionState: "pending", content: `${message.content}\n\n${errorMessage(error)}` }
            : message,
        ),
      );
    },
  });

  function send(message = input) {
    const trimmed = message.trim();
    if (!trimmed || chatMutation.isPending) return;
    setMessages((current) => [...current, { id: newId(), role: "user", content: trimmed }]);
    setInput("");
    chatMutation.mutate(trimmed);
  }

  function cancelAction(id: string) {
    setMessages((current) =>
      current.map((message) => (message.id === id ? { ...message, actionState: "cancelled" } : message)),
    );
  }

  const selectedModel = config?.models.find((option) => option.id === model);
  const reasoningDisabled = selectedModel ? !selectedModel.supports_reasoning : false;

  if (!user) return null;

  return (
    <>
      {!open && (
        <Button
          className="fixed bottom-5 right-5 z-50 h-12 rounded-full px-5 shadow-card-hover"
          onClick={() => setOpen(true)}
          aria-label="Open Headcount Copilot"
        >
          <Sparkles className="h-4 w-4" />
          Ask Copilot
        </Button>
      )}

      {open && (
        <section
           className="fixed inset-x-3 bottom-3 z-50 flex h-[min(720px,calc(100vh-24px))] flex-col overflow-hidden rounded-2xl border border-border bg-card shadow-popover sm:left-auto sm:right-5 sm:w-[430px]"
          aria-label="Headcount Copilot"
        >
           <header className="flex items-center justify-between border-b border-border bg-accent/30 px-4 py-3">
            <div className="flex items-center gap-3">
               <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-primary">
                <Bot className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground">Headcount Copilot</p>
                <p className="text-xs text-muted-foreground">Live data · confirmed actions</p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <Button
                size="icon"
                variant={showSettings ? "secondary" : "ghost"}
                onClick={() => setShowSettings((value) => !value)}
                aria-label="Copilot settings"
              >
                <Settings2 className="h-4 w-4" />
              </Button>
              <Button size="icon" variant="ghost" onClick={() => setOpen(false)} aria-label="Close copilot">
                <X className="h-4 w-4" />
              </Button>
            </div>
          </header>

          {showSettings && (
            <div className="grid grid-cols-2 gap-3 border-b border-border bg-muted/40 p-3">
              <label className="space-y-1 text-xs font-medium text-foreground">
                Model
                <select
                  className="h-9 w-full rounded-md border border-input bg-background px-2 text-sm"
                  value={model}
                  onChange={(event) => setModel(event.target.value)}
                >
                  {(config?.models ?? [{ id: "auto", label: "Auto", supports_reasoning: true }]).map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="space-y-1 text-xs font-medium text-foreground">
                Reasoning
                <select
                  className="h-9 w-full rounded-md border border-input bg-background px-2 text-sm disabled:opacity-50"
                  value={reasoningEffort}
                  disabled={reasoningDisabled}
                  onChange={(event) => setReasoningEffort(event.target.value as ReasoningEffort)}
                >
                  <option value="none">None</option>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="max">Max</option>
                </select>
              </label>
              <p className="col-span-2 text-[11px] leading-relaxed text-muted-foreground">
                Auto balances speed and depth. Copilot shows conclusions and tool activity, not hidden reasoning.
              </p>
            </div>
          )}

          <div className="flex-1 space-y-4 overflow-y-auto p-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={message.role === "user" ? "ml-10 flex justify-end" : "mr-5"}
              >
                <div
                  className={
                    message.role === "user"
                      ? "max-w-full rounded-2xl rounded-br-md bg-primary px-3 py-2 text-sm text-primary-foreground"
                      : "max-w-full rounded-2xl rounded-bl-md bg-muted px-3 py-2 text-sm text-foreground"
                  }
                >
                  {message.tools && message.tools.length > 0 && (
                    <div className="mb-2 flex flex-wrap gap-1">
                      {message.tools.map((tool) => (
                        <span
                          key={tool}
                          className="rounded-full border border-border bg-background/70 px-2 py-0.5 text-[10px] text-muted-foreground"
                        >
                          {tool}
                        </span>
                      ))}
                    </div>
                  )}
                  <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>

                  {message.pendingAction && (
                    <div className="mt-3 rounded-lg border border-border bg-background p-3 text-foreground">
                      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        Confirmation required
                      </p>
                      <p className="mt-1 text-sm font-semibold">{message.pendingAction.title}</p>
                      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                        {message.pendingAction.description}
                      </p>
                      {message.actionState === "pending" && (
                        <div className="mt-3 flex gap-2">
                          <Button
                            size="sm"
                            onClick={() =>
                              actionMutation.mutate({ id: message.id, action: message.pendingAction! })
                            }
                          >
                            Confirm action
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => cancelAction(message.id)}>
                            Cancel
                          </Button>
                        </div>
                      )}
                      {message.actionState === "running" && (
                        <p className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
                          <Loader2 className="h-3.5 w-3.5 animate-spin" /> Running action…
                        </p>
                      )}
                      {message.actionState === "complete" && (
                        <div className="mt-3 flex items-center justify-between text-xs text-success">
                          <span className="flex items-center gap-1">
                            <Check className="h-3.5 w-3.5" /> Completed
                          </span>
                          {message.link && (
                            <Link className="flex items-center gap-1 font-medium hover:underline" to={message.link}>
                              Open <ExternalLink className="h-3 w-3" />
                            </Link>
                          )}
                        </div>
                      )}
                      {message.actionState === "cancelled" && (
                        <p className="mt-3 text-xs text-muted-foreground">Action cancelled. No data was changed.</p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {messages.length === 1 && (
              <div className="space-y-2">
                {STARTERS.map((starter) => (
                  <button
                    key={starter}
                    type="button"
                     className="w-full rounded-xl border border-border bg-card px-3 py-2 text-left text-xs text-foreground transition-colors hover:border-primary/30 hover:bg-accent"
                    onClick={() => send(starter)}
                  >
                    {starter}
                  </button>
                ))}
              </div>
            )}

            {chatMutation.isPending && (
              <div className="mr-16 flex items-center gap-2 rounded-2xl rounded-bl-md bg-muted px-3 py-2 text-xs text-muted-foreground">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Reviewing your workspace…
              </div>
            )}
          </div>

          <form
            className="border-t border-border p-3"
            onSubmit={(event) => {
              event.preventDefault();
              send();
            }}
          >
             <div className="flex items-end gap-2 rounded-2xl border border-input bg-background p-2 focus-within:ring-2 focus-within:ring-ring">
              <textarea
                rows={2}
                className="max-h-28 min-h-10 flex-1 resize-none bg-transparent px-1 py-1 text-sm outline-none placeholder:text-muted-foreground"
                placeholder="Ask about headcount or run a scenario…"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    send();
                  }
                }}
              />
              <Button size="icon" type="submit" disabled={!input.trim() || chatMutation.isPending}>
                {chatMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
            <p className="mt-2 text-center text-[10px] text-muted-foreground">
              Check important decisions. Data changes always require confirmation.
            </p>
          </form>
        </section>
      )}
    </>
  );
}
