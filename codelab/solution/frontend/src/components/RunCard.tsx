import { Link } from "react-router-dom";
import type { RunRecord } from "../types";
import { getPdfUrl } from "../api";

const STATUS_COLOR: Record<string, string> = {
  running: "bg-yellow-100 text-yellow-800",
  completed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
};

export default function RunCard({ run }: { run: RunRecord }) {
  const date = new Date(run.started_at).toLocaleString();
  return (
    <div className="border rounded-lg p-4 bg-white flex items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLOR[run.status]}`}>
          {run.status}
        </span>
        <span className="text-sm text-gray-500">{date}</span>
        {run.agent_id && (
          <span className="text-xs text-gray-400 font-mono">{run.agent_id}</span>
        )}
      </div>
      <div className="flex gap-3">
        <Link to={`/runs/${run.id}`} className="text-sm text-indigo-600 hover:underline">
          View
        </Link>
        {run.pdf_available && (
          <a href={getPdfUrl(run.id)} download className="text-sm text-green-600 hover:underline">
            PDF
          </a>
        )}
      </div>
    </div>
  );
}
