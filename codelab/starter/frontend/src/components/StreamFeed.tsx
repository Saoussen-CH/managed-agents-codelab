import { useEffect, useRef } from "react";
import type { SSEEvent } from "../types";

interface Props {
  events: SSEEvent[];
  running: boolean;
}

export default function StreamFeed({ events, running }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events.length]);

  return (
    <div className="h-full overflow-auto bg-gray-900 rounded-lg p-4 font-mono text-xs text-gray-300 space-y-1">
      {events.map((e, i) => {
        if (e.type === "step")
          return <p key={i} className="text-gray-400">{e.content}</p>;
        if (e.type === "output")
          return (
            <p key={i} className="text-green-400 whitespace-pre-wrap">
              {e.content}
            </p>
          );
        if (e.type === "error")
          return <p key={i} className="text-red-400">Error: {e.message}</p>;
        if (e.type === "done")
          return <p key={i} className="text-indigo-400">✓ Done</p>;
        return null;
      })}
      {running && (
        <p className="text-yellow-400 animate-pulse">Agent is working…</p>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
