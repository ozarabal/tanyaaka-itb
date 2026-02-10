import { useState } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled: boolean;
}

export default function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [input, setInput] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setInput("");
  };

  const canSend = input.trim().length > 0 && !disabled;

  return (
    <div className="bg-white/10 backdrop-blur-md border-t border-white/20 px-4 py-4">
      <form onSubmit={handleSubmit} className="max-w-4xl mx-auto flex gap-3 items-end">
        <div className="flex-1 relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ketik pertanyaan kamu..."
            disabled={disabled}
            className="w-full bg-white/10 border border-white/20 rounded-2xl px-5 py-3 text-sm text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-white/30 focus:border-white/30 disabled:opacity-40 transition-all font-medium"
          />
        </div>
        <button
          type="submit"
          disabled={!canSend}
          className={`flex-shrink-0 w-11 h-11 rounded-2xl flex items-center justify-center transition-all cursor-pointer ${
            canSend
              ? "bg-white/25 hover:bg-white/35 shadow-lg text-white"
              : "bg-white/5 text-white/20 cursor-not-allowed"
          }`}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </button>
      </form>
    </div>
  );
}
