import { useState, useCallback } from "react";
import type { ChatMessage } from "./types";
import { sendMessage } from "./api";
import Header from "./components/Header";
import ChatWindow from "./components/ChatWindow";
import ChatInput from "./components/ChatInput";

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = useCallback(async (question: string) => {
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: question,
    };

    const loadingMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      isLoading: true,
    };

    setMessages((prev) => [...prev, userMessage, loadingMessage]);
    setIsLoading(true);

    try {
      const response = await sendMessage(question);

      const assistantMessage: ChatMessage = {
        id: loadingMessage.id,
        role: "assistant",
        content: response.answer,
        sources: response.sources,
      };

      setMessages((prev) =>
        prev.map((msg) => (msg.id === loadingMessage.id ? assistantMessage : msg))
      );
    } catch {
      const errorMessage: ChatMessage = {
        id: loadingMessage.id,
        role: "assistant",
        content: "Gagal mengirim pertanyaan. Silakan coba lagi.",
        isError: true,
      };

      setMessages((prev) =>
        prev.map((msg) => (msg.id === loadingMessage.id ? errorMessage : msg))
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  return (
    <div className="flex flex-col h-screen font-poppins">
      <Header />
      <ChatWindow messages={messages} onSuggestedQuestion={handleSend} />
      <ChatInput onSend={handleSend} disabled={isLoading} />
    </div>
  );
}
