import { useStore } from "../state/useStore";

export function StimulusControls() {
  const { runs, currentRunId, currentStimulus, selectStimulus } = useStore();
  const run = runs.find((r) => r.run_id === currentRunId);
  const stimuli = run?.stimuli ?? [];

  if (runs.length === 0) return null;

  return (
    <div className="space-y-1.5">
      <p className="text-[11px] font-medium tracking-wide text-slate-400 uppercase">Stimulus</p>
      <div className="flex rounded-lg border border-slate-200 overflow-hidden text-sm">
        {stimuli.map((s) => (
          <button
            key={s}
            onClick={() => selectStimulus(s)}
            className={`flex-1 px-3 py-1.5 transition-colors ${
              currentStimulus === s
                ? "bg-slate-900 text-white"
                : "bg-white text-slate-600 hover:bg-slate-50"
            }`}
          >
            {s.replace("_", " ")}
          </button>
        ))}
      </div>
      {stimuli.length === 0 && <p className="text-xs text-slate-400">No stimuli available for this run</p>}
    </div>
  );
}