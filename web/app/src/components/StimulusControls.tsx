import { useStore } from "../state/useStore";

export function StimulusControls() {
  const { runs, currentRunId, currentStimulus, selectStimulus } = useStore();
  const run = runs.find((r) => r.run_id === currentRunId);
  const stimuli = run?.stimuli ?? [];

  if (runs.length === 0) return null;

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-3">
      <h3 className="text-sm font-medium text-slate-700">Stimulus</h3>
      {stimuli.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {stimuli.map((s) => (
            <button
              key={s}
              onClick={() => selectStimulus(s)}
              className={`text-sm rounded-lg px-3 py-1.5 border transition-colors ${
                currentStimulus === s
                  ? "bg-slate-900 text-white border-slate-900"
                  : "bg-white text-slate-700 border-slate-200 hover:border-slate-400"
              }`}
            >
              {s.replace("_", " ")}
            </button>
          ))}
        </div>
      )}
      {stimuli.length === 0 && <p className="text-sm text-slate-400">No stimuli available for this run</p>}
    </div>
  );
}
