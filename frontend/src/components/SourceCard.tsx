import { useState } from "react";
import type { Source } from "../types";

interface SourceCardProps {
  sources: Source[];
}

export default function SourceCard({ sources }: SourceCardProps) {
  const [expanded, setExpanded] = useState(false);

  if (sources.length === 0) return null;

  return (
    <div className="mt-3 pt-3 border-t border-white/15">
      <button
        onClick={() => setExpanded(!expanded)}
        className="text-xs text-white/70 hover:text-white font-semibold flex items-center gap-1.5 cursor-pointer transition-colors"
      >
        <svg
          className={`w-3.5 h-3.5 transition-transform duration-200 ${expanded ? "rotate-90" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        Sumber Referensi ({sources.length})
      </button>

      {expanded && (
        <div className="mt-2.5 space-y-2">
          {sources.map((source, index) => (
            <div
              key={index}
              className="bg-white/10 border border-white/15 rounded-xl p-3 text-xs"
            >
              <div className="font-semibold text-white flex items-center gap-1.5">
                <svg className="w-3.5 h-3.5 text-white/70 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                {source.document}
                {source.page != null && (
                  <span className="text-white/40 font-medium ml-1">— Hal. {source.page + 1}</span>
                )}
              </div>
              <p className="text-white/50 mt-1.5 line-clamp-3 leading-relaxed">{source.content_snippet}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
