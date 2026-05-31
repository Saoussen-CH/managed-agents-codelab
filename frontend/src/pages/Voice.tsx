import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getConfig, updateConfig } from "../api";

export default function Voice() {
  const qc = useQueryClient();
  const { data: config } = useQuery({ queryKey: ["config"], queryFn: getConfig });
  const [voice, setVoice] = useState("");

  useEffect(() => { if (config) setVoice(config.voice); }, [config]);

  const mutation = useMutation({
    mutationFn: (voice: string) => updateConfig({ voice }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["config"] }),
  });

  return (
    <div className="max-w-xl space-y-4">
      <h1 className="text-2xl font-bold text-gray-900">Voice</h1>
      <p className="text-sm text-gray-500">The system instruction that shapes the agent's editorial persona.</p>
      <textarea
        value={voice}
        onChange={(e) => setVoice(e.target.value)}
        rows={10}
        placeholder="You are the editor of a sharp, slightly skeptical tech newsletter.
Short sentences. Funny but never silly.
Highlight what matters. Call out hype.
Always finish with a 'Skip This' callout — one story that's just noise."
        className="w-full border rounded-lg px-3 py-2 text-sm font-mono resize-y"
      />
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-400">{voice.length} characters</span>
        <button
          onClick={() => mutation.mutate(voice)}
          disabled={mutation.isPending}
          className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors"
        >
          {mutation.isPending ? "Saving…" : "Save"}
        </button>
      </div>
    </div>
  );
}
