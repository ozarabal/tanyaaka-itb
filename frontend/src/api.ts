import type { ChatResponse } from "./types";

const BASE_URL = "/api/v1";

export async function sendMessage(question: string): Promise<ChatResponse> {
  const response = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Gagal mengirim pertanyaan");
  }

  return response.json();
}
