import { useState } from "react";
import type { SSEEvent } from "../types";
import { startRefine } from "../api";

interface Props {
  runId: string;
  onEvents: (events: SSEEvent[]) => void;
}

export default function RefinePanel({ runId, onEvents }: Props) {
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleRefine() {
    if (!message.trim()) return;
    setLoading(true);
    const events: SSEEvent[] = [];

    try {
      await startRefine(runId, message);
      setMessage("");

      await new Promise<void>((resolve, reject) => {
        const es = new EventSource(`/api/runs/${runId}/refine/stream`);
        es.onmessage = (e) => {
          const event: SSEEvent = JSON.parse(e.data);
          events.push(event);
          onEvents([...events]);
          if (event.type === "done" || event.type === "error") {
            es.close();
            resolve();
          }
        };
        es.onerror = () => { es.close(); reject(new Error("SSE error")); };
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700">Refine output</label>
      <textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        rows={3}
        placeholder="Make the AI section twice as long. Add an Editor's Note at the top."
        className="w-full border rounded-lg px-3 py-2 text-sm resize-none"
      />
      <button
        onClick={handleRefine}
        disabled={loading || !message.trim()}
        className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors"
      >
        {loading ? "Refining…" : "Refine"}
      </button>
    </div>
  );
}
