import { useEffect } from "react";
import { useStore } from "../state/useStore";

export function RunSelector() {
  const { runs, fetchRuns, selectRun, currentRunId } = useStore();

  useEffect(() => {
    if (runs.length === 0) void fetchRuns();
  }, [fetchRuns, runs.length]);

  if (runs.length === 0) return <LoadingSkeleton />;

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-3">
      <h3 className="text-sm font-medium text-slate-700">Available Experiments</h3>
      <div className="space-y-2">
        {runs.map((run) => (
          <button
            key={run.run_id}
            onClick={() => selectRun(run.run_id)}
            className={`w-full text-left rounded-lg border p-3 transition-colors ${
              currentRunId === run.run_id
                ? "border-slate-900 bg-slate-50"
                : "border-slate-200 bg-white hover:border-slate-400"
            }`}
          >
            <div className="font-mono text-sm text-slate-800">{run.run_id}</div>
            <div className="text-xs text-slate-400 mt-1">
              {run.stimuli.length} stimuli: {run.stimuli.join(", ")}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4">
      <div className="h-4 bg-slate-100 rounded w-40 animate-pulse" />
      <div className="h-3 bg-slate-50 rounded w-60 mt-2 animate-pulse" />
    </div>
  );
}