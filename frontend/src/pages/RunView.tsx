import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getRun, getPdfUrl } from "../api";
import StreamFeed from "../components/StreamFeed";
import RefinePanel from "../components/RefinePanel";
import type { SSEEvent, RunRecord } from "../types";

export default function RunView() {
  const { id } = useParams<{ id: string }>();
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [streaming, setStreaming] = useState(true);

  const { data: run, refetch } = useQuery<RunRecord>({
    queryKey: ["run", id],
    queryFn: () => getRun(id!),
    refetchInterval: streaming ? 2000 : false,
  });

  useEffect(() => {
    if (!id) return;
    const es = new EventSource(`/api/runs/${id}/stream`);
    es.onmessage = (e) => {
      const event: SSEEvent = JSON.parse(e.data);
      setEvents((prev) => [...prev, event]);
      if (event.type === "done" || event.type === "error") {
        setStreaming(false);
        es.close();
        refetch();
      }
    };
    es.onerror = () => { setStreaming(false); es.close(); };
    return () => es.close();
  }, [id]);

  const outputText = run?.refine_output_text ?? run?.output_text;

  return (
    <div className="h-full flex flex-col gap-4">
      <h1 className="text-xl font-bold text-gray-900 shrink-0">
        Run <span className="font-mono text-sm text-gray-500">{id?.slice(0, 8)}</span>
      </h1>
      <div className="flex-1 grid grid-cols-2 gap-6 min-h-0">
        <StreamFeed events={events} running={streaming} />
        <div className="flex flex-col gap-4 overflow-auto">
          {outputText && (
            <div className="bg-white border rounded-lg p-4 text-sm text-gray-800 whitespace-pre-wrap flex-1 overflow-auto">
              {outputText}
            </div>
          )}
          {run?.pdf_available && (
            <a
              href={getPdfUrl(id!)}
              download
              className="inline-block bg-green-600 hover:bg-green-700 text-white text-sm font-medium rounded-lg px-4 py-2 text-center transition-colors"
            >
              Download PDF
            </a>
          )}
          {!streaming && run && (
            <RefinePanel
              runId={id!}
              onEvents={(refineEvents) => setEvents((prev) => [...prev, ...refineEvents])}
            />
          )}
        </div>
      </div>
    </div>
  );
}
