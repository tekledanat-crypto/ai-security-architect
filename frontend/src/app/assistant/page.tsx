import { ChatPanel } from "@/components/chat-panel";

export default function AssistantPage() {
  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border px-6 py-4">
        <h1 className="font-display text-lg font-semibold text-ink">AI Assistant</h1>
        <p className="text-sm text-ink-muted">
          Interview-driven secure architecture design, grounded in live MCP tools.
        </p>
      </div>
      <div className="flex-1 overflow-hidden">
        <ChatPanel />
      </div>
    </div>
  );
}
