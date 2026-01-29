import type { MessageEntry } from "../hooks/useGameState";

const KIND_CLASSES: Record<MessageEntry["kind"], string> = {
  info: "text-soft",
  error: "text-alert",
  accent: "tone-tactical"
};

export default function MessageLog({ messages }: { messages: MessageEntry[] }) {
  return (
    <div className="panel panel-live p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-lg">Message Log</h2>
        <span className="glass-chip">Live</span>
      </div>
      <div className="space-y-2 max-h-56 overflow-y-auto pr-2">
        {messages.length === 0 && <p className="text-xs text-soft">No tactical messages yet.</p>}
        {messages.map((msg) => (
          <div key={msg.id} className="text-xs">
            <p className={`font-semibold ${KIND_CLASSES[msg.kind]}`}>{msg.text}</p>
            <p className="text-[10px] text-soft">{msg.timestamp}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
