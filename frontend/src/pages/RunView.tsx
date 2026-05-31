import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import StreamFeed from "../components/StreamFeed";
import RefinePanel from "../components/RefinePanel";
import type { SSEEvent } from "../types";
import { getPdfUrl } from "../api";

export default function RunView() {
  const { id } = useParams<{ id: string }>();
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [streaming, setStreaming] = useState(true);
  const [outputText, setOutputText] = useState<string | null>(null);
  const [pdfAvailable, setPdfAvailable] = useState(false);
  const [refineOutput, setRefineOutput] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    const es = new EventSource(`/api/runs/${id}/stream`);

    es.onmessage = (e) => {
      const event: SSEEvent = JSON.parse(e.data);
      setEvents((prev) => [...prev, event]);

      if (event.type === "output" && event.content) {
        setOutputText(event.content);
      }
      if (event.type === "done") {
        setPdfAvailable(event.pdf_available ?? false);
        setStreaming(false);
        es.close();
      }
      if (event.type === "error") {
        setStreaming(false);
        es.close();
      }
    };

    es.onerror = () => {
      setStreaming(false);
      es.close();
    };

    return () => es.close();
  }, [id]);

  const displayText = refineOutput ?? outputText;

  return (
    <div className="h-full flex flex-col gap-4">
      <h1 className="text-xl font-bold text-gray-900 shrink-0">
        Run <span className="font-mono text-sm text-gray-500">{id?.slice(0, 8)}</span>
      </h1>

      <div className="flex-1 grid grid-cols-2 gap-6 min-h-0">
        {/* Left — live agent stream */}
        <StreamFeed events={events} running={streaming} />

        {/* Right — result + actions */}
        <div className="flex flex-col gap-4 overflow-auto">
          {displayText ? (
            <div className="bg-white border rounded-lg p-4 text-sm text-gray-800 whitespace-pre-wrap flex-1 overflow-auto">
              {displayText}
            </div>
          ) : streaming ? (
            <div className="flex-1 flex items-center justify-center text-sm text-gray-400">
              Waiting for output…
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-sm text-red-400">
              No output returned.
            </div>
          )}

          {pdfAvailable && id && (
            <a
              href={getPdfUrl(id)}
              download
              className="inline-block bg-green-600 hover:bg-green-700 text-white text-sm font-medium rounded-lg px-4 py-2 text-center transition-colors shrink-0"
            >
              Download PDF
            </a>
          )}

          {!streaming && id && (
            <RefinePanel
              runId={id}
              onEvents={(refineEvents) => {
                setEvents((prev) => [...prev, ...refineEvents]);
                const out = refineEvents.findLast((e) => e.type === "output");
                if (out?.content) setRefineOutput(out.content);
                const done = refineEvents.find((e) => e.type === "done");
                if (done?.pdf_available) setPdfAvailable(true);
              }}
            />
          )}
        </div>
      </div>
    </div>
  );
}
