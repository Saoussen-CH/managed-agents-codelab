import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { listAgents, listRuns, startRun, getConfig } from "../api";
import RunCard from "../components/RunCard";

export default function Dashboard() {
  const navigate = useNavigate();
  const [agentId, setAgentId] = useState("");
  const [loading, setLoading] = useState(false);

  const { data: config } = useQuery({ queryKey: ["config"], queryFn: getConfig });
  const { data: agents = [] } = useQuery({ queryKey: ["agents"], queryFn: listAgents });
  const { data: runs = [] } = useQuery({ queryKey: ["runs"], queryFn: listRuns });

  async function handleRun() {
    setLoading(true);
    try {
      const { run_id } = await startRun(agentId || undefined);
      navigate(`/runs/${run_id}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-2xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Daily Digest</h1>
        {config && (
          <p className="text-sm text-gray-500">
            {config.sources.length} sources · "{config.voice.slice(0, 60)}…"
          </p>
        )}
      </div>

      <div className="bg-white border rounded-xl p-6 space-y-4">
        <label className="block text-sm font-medium text-gray-700">
          Agent <span className="text-gray-400 font-normal">(optional — runs base Antigravity agent with your current Voice & Skills if blank)</span>
        </label>
        <select
          value={agentId}
          onChange={(e) => setAgentId(e.target.value)}
          className="w-full border rounded-lg px-3 py-2 text-sm"
        >
          <option value="">Base Antigravity agent (remote sandbox)</option>
          {agents.map((a) => (
            <option key={a.id} value={a.id}>{a.id}</option>
          ))}
        </select>
        <button
          onClick={handleRun}
          disabled={loading}
          className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-medium rounded-lg px-4 py-2 transition-colors"
        >
          {loading ? "Starting…" : "Run Digest"}
        </button>
      </div>

      {runs.slice(0, 3).length > 0 && (
        <div className="space-y-2">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Recent runs</h2>
          {runs.slice(0, 3).map((r) => <RunCard key={r.id} run={r} />)}
        </div>
      )}
    </div>
  );
}
