export interface Source {
  document: string;
  page: number | null;
  content_snippet: string;
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
  model: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  isLoading?: boolean;
  isError?: boolean;
}
