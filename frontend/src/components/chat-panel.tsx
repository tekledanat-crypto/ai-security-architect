"use client";

import { useEffect, useRef, useState } from "react";
import { SendHorizontal, ShieldHalf, Sparkles } from "lucide-react";
import { streamChat } from "@/lib/api";
import type { ChatMessage, ToolActivity } from "@/lib/types";
import { ToolActivityRail } from "./tool-activity";
import { cn } from "@/lib/utils";

const CONVERSATION_ID = "primary";

const SUGGESTIONS = [
  "I want to build an ecommerce website",
  "Design a secure internal HR app",
  "Validate my architecture",
  "Show me the STRIDE threats",
];

export function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function send(text: string) {
    const content = text.trim();
    if (!content || busy) return;
    setInput("");
    setBusy(true);

    setMessages((m) => [...m, { role: "user", content, toolActivity: [] }]);
    // Placeholder assistant message we stream into.
    setMessages((m) => [...m, { role: "assistant", content: "", toolActivity: [] }]);

    const updateAssistant = (fn: (msg: ChatMessage) => ChatMessage) =>
      setMessages((m) => {
        const copy = [...m];
        copy[copy.length - 1] = fn(copy[copy.length - 1]);
        return copy;
      });

    try {
      for await (const evt of streamChat(CONVERSATION_ID, content)) {
        switch (evt.event) {
          case "text":
            updateAssistant((msg) => ({ ...msg, content: msg.content + evt.data.text }));
            break;
          case "tool_call":
            updateAssistant((msg) => ({
              ...msg,
              toolActivity: [...msg.toolActivity, { tool: evt.data.tool, status: "running" }],
            }));
            break;
          case "tool_result":
            updateAssistant((msg) => ({
              ...msg,
              toolActivity: markDone(msg.toolActivity, evt.data.tool, evt.data.summary),
            }));
            break;
          case "guardrail":
            if (evt.data.ok === false || evt.data.suspicious) {
              updateAssistant((msg) => ({
                ...msg,
                toolActivity: [
                  ...msg.toolActivity,
                  {
                    tool: `guardrail:${evt.data.stage}`,
                    status: evt.data.ok === false ? "denied" : "done",
                    reason: evt.data.reasons?.[0],
                  },
                ],
              }));
            }
            break;
          case "error":
            updateAssistant((msg) => ({ ...msg, content: msg.content + `\n⚠ ${evt.data.message}` }));
            break;
          case "done":
            break;
        }
      }
    } finally {
      setBusy(false);
    }
  }

  const empty = messages.length === 0;

  return (
    <div className="flex h-full flex-col">
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-6">
        <div className="mx-auto max-w-3xl">
          {empty ? <EmptyState onPick={send} /> : messages.map((m, i) => <Bubble key={i} msg={m} />)}
        </div>
      </div>

      <div className="border-t border-border bg-surface/60 px-6 py-4 backdrop-blur">
        <div className="mx-auto flex max-w-3xl items-end gap-3">
          <div className="flex flex-1 items-end rounded-xl border border-border bg-surface-2 focus-within:border-azure/50">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send(input);
                }
              }}
              rows={1}
              placeholder="Describe your solution, or ask me to validate an architecture…"
              className="max-h-40 flex-1 resize-none bg-transparent px-4 py-3 text-sm text-ink placeholder:text-ink-faint focus:outline-none"
            />
          </div>
          <button
            onClick={() => send(input)}
            disabled={busy || !input.trim()}
            className="flex h-11 w-11 items-center justify-center rounded-xl bg-azure text-white transition-colors hover:bg-azure-bright disabled:opacity-40"
          >
            <SendHorizontal className="h-[18px] w-[18px]" />
          </button>
        </div>
        <p className="mx-auto mt-2 max-w-3xl font-mono text-[10px] text-ink-faint">
          Findings are produced by a deterministic engine over 137 controls — the assistant narrates, it doesn&apos;t invent.
        </p>
      </div>
    </div>
  );
}

function markDone(activity: ToolActivity[], tool: string, summary: string): ToolActivity[] {
  const copy = [...activity];
  for (let i = copy.length - 1; i >= 0; i--) {
    if (copy[i].tool === tool && copy[i].status === "running") {
      copy[i] = { ...copy[i], status: "done", summary };
      break;
    }
  }
  return copy;
}

function Bubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";
  return (
    <div className={cn("mb-6 flex gap-3", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
          isUser ? "bg-surface-3" : "bg-azure/15",
        )}
      >
        {isUser ? (
          <span className="font-mono text-xs text-ink-muted">You</span>
        ) : (
          <ShieldHalf className="h-4 w-4 text-azure" />
        )}
      </div>
      <div className={cn("max-w-[85%]", isUser && "text-right")}>
        {!isUser && <ToolActivityRail activity={msg.toolActivity} />}
        <div
          className={cn(
            "inline-block whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
            isUser ? "bg-azure/15 text-ink" : "bg-surface-2 text-ink",
          )}
        >
          {msg.content || <span className="text-ink-faint">▋</span>}
        </div>
      </div>
    </div>
  );
}

function EmptyState({ onPick }: { onPick: (s: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-azure/15 shadow-glow">
        <Sparkles className="h-7 w-7 text-azure" />
      </div>
      <h2 className="font-display text-2xl font-semibold text-ink">Design something secure</h2>
      <p className="mt-2 max-w-md text-sm text-ink-muted">
        Tell me what you&apos;re building on Azure. I&apos;ll interview you, propose an architecture, and
        validate it against 11 security and compliance frameworks in real time.
      </p>
      <div className="mt-8 grid w-full max-w-lg grid-cols-2 gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onPick(s)}
            className="rounded-lg border border-border bg-surface-2 px-4 py-3 text-left text-sm text-ink-muted transition-colors hover:border-azure/40 hover:text-ink"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
