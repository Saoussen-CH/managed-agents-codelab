import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listAgents, createAgent, deleteAgent } from "../api";

export default function Agents() {
  const qc = useQueryClient();
  const { data: agents = [] } = useQuery({ queryKey: ["agents"], queryFn: listAgents });
  const [id, setId] = useState("");
  const [description, setDescription] = useState("");

  const create = useMutation({
    mutationFn: () => createAgent({ id, description }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["agents"] }); setId(""); setDescription(""); },
  });

  const remove = useMutation({
    mutationFn: deleteAgent,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agents"] }),
  });

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Agents</h1>

      <div className="bg-white border rounded-xl p-5 space-y-3">
        <h2 className="text-sm font-semibold text-gray-700">Save current config as agent</h2>
        <div className="flex gap-3">
          <input value={id} onChange={(e) => setId(e.target.value)}
            placeholder="agent-id" className="flex-1 border rounded-lg px-3 py-2 text-sm" />
          <input value={description} onChange={(e) => setDescription(e.target.value)}
            placeholder="Description" className="flex-1 border rounded-lg px-3 py-2 text-sm" />
          <button
            onClick={() => create.mutate()}
            disabled={!id.trim() || create.isPending}
            className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors shrink-0"
          >
            {create.isPending ? "Saving…" : "Save"}
          </button>
        </div>
      </div>

      <div className="space-y-2">
        {agents.length === 0 && <p className="text-sm text-gray-400">No saved agents.</p>}
        {agents.map((a) => (
          <div key={a.id} className="bg-white border rounded-lg px-4 py-3 flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-900 font-mono">{a.id}</p>
              <p className="text-xs text-gray-400">{a.description || "No description"}</p>
            </div>
            <button onClick={() => remove.mutate(a.id)} className="text-red-400 hover:text-red-600 text-sm">
              Delete
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
