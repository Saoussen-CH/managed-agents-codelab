import { useQuery } from "@tanstack/react-query";
import { listRuns } from "../api";
import RunCard from "../components/RunCard";

export default function History() {
  const { data: runs = [] } = useQuery({ queryKey: ["runs"], queryFn: listRuns });

  return (
    <div className="max-w-2xl space-y-4">
      <h1 className="text-2xl font-bold text-gray-900">History</h1>
      {runs.length === 0 && (
        <p className="text-sm text-gray-400">No runs yet. Go to Dashboard to start one.</p>
      )}
      {runs.map((r) => <RunCard key={r.id} run={r} />)}
    </div>
  );
}
