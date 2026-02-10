import type { ChatMessage } from "../types";
import SourceCard from "./SourceCard";
import ElephantIcon from "./ElephantIcon";

interface MessageBubbleProps {
  message: ChatMessage;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  if (message.isLoading) {
    return (
      <div className="flex justify-start gap-3 message-enter">
        <div className="w-8 h-8 rounded-xl bg-white/20 backdrop-blur flex items-center justify-center flex-shrink-0 text-white shadow-md">
          <ElephantIcon className="w-4 h-4" />
        </div>
        <div className="bg-white/15 backdrop-blur border border-white/20 rounded-2xl rounded-tl-md px-4 py-3">
          <div className="flex items-center gap-2 text-sm text-white/60">
            <div className="flex gap-1.5">
              <span className="typing-dot w-2 h-2 bg-white rounded-full" />
              <span className="typing-dot w-2 h-2 bg-white rounded-full" />
              <span className="typing-dot w-2 h-2 bg-white rounded-full" />
            </div>
            <span className="text-xs font-medium">Sedang mencari jawaban...</span>
          </div>
        </div>
      </div>
    );
  }

  if (isUser) {
    return (
      <div className="flex justify-end message-enter">
        <div className="bg-white/20 backdrop-blur border border-white/25 rounded-2xl rounded-tr-md px-4 py-3 max-w-[75%] shadow-md">
          <p className="text-sm text-white whitespace-pre-wrap leading-relaxed font-medium">{message.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start gap-3 message-enter">
      <div className="w-8 h-8 rounded-xl bg-white/20 backdrop-blur flex items-center justify-center flex-shrink-0 text-white shadow-md">
        <ElephantIcon className="w-4 h-4" />
      </div>
      <div className="bg-white/15 backdrop-blur border border-white/20 rounded-2xl rounded-tl-md px-4 py-3 max-w-[75%]">
        {message.isError ? (
          <p className="text-sm text-red-200 font-medium">{message.content}</p>
        ) : (
          <>
            <p className="text-sm text-white whitespace-pre-wrap leading-relaxed">{message.content}</p>
            {message.sources && <SourceCard sources={message.sources} />}
          </>
        )}
      </div>
    </div>
  );
}
