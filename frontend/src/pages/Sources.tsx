import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getConfig, updateConfig } from "../api";

export default function Sources() {
  const qc = useQueryClient();
  const { data: config } = useQuery({ queryKey: ["config"], queryFn: getConfig });
  const [newUrl, setNewUrl] = useState("");

  const mutation = useMutation({
    mutationFn: (sources: string[]) => updateConfig({ sources }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["config"] }),
  });

  const sources = config?.sources ?? [];

  function add() {
    if (!newUrl.trim()) return;
    mutation.mutate([...sources, newUrl.trim()]);
    setNewUrl("");
  }

  return (
    <div className="max-w-xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Sources</h1>
      <p className="text-sm text-gray-500">
        News URLs the agent fetches on every run. Defaults match the workshop.
      </p>
      <div className="space-y-2">
        {sources.map((url) => (
          <div key={url} className="flex items-center justify-between bg-white border rounded-lg px-4 py-2 gap-3">
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-mono text-indigo-600 hover:underline truncate"
            >
              {url}
            </a>
            <button
              onClick={() => mutation.mutate(sources.filter((s) => s !== url))}
              className="text-red-400 hover:text-red-600 text-sm shrink-0"
            >
              Remove
            </button>
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          value={newUrl}
          onChange={(e) => setNewUrl(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && add()}
          placeholder="https://news.ycombinator.com"
          className="flex-1 border rounded-lg px-3 py-2 text-sm"
        />
        <button
          onClick={add}
          className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors"
        >
          Add
        </button>
      </div>
    </div>
  );
}
