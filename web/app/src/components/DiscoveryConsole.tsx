import { useStore } from "../state/useStore";

export function DiscoveryConsole() {
  const { symbolSet, logTestAction, testLog, currentStimulus } = useStore();
  if (!symbolSet || !currentStimulus) return null;

  const table = testLog?.table ?? {};

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-slate-700">DISCOVERY</h3>
        <span className="text-xs bg-violet-100 text-violet-700 rounded-full px-2.5 py-0.5 font-medium">
          IN-SESSION
        </span>
      </div>
      <p className="text-xs text-slate-400">
        Learn by experimenting: pick the stimulus that creates each symbol. Actions are
        logged for an in-session correlation table.
      </p>
      <div className="flex flex-wrap gap-2">
        {symbolSet.classes.map((cls) => (
          <button
            key={cls.class}
            onClick={() => void logTestAction(cls.symbol)}
            className="text-sm rounded-lg px-3 py-1.5 border bg-white text-slate-700 border-slate-200 hover:border-violet-300 hover:bg-violet-50 transition-colors"
            title={`log a TEST with ${cls.symbol} on ${currentStimulus}`}
          >
            {cls.symbol} test
          </button>
        ))}
      </div>

      <div className="text-xs text-slate-500">
        <div className="font-medium text-slate-600 mb-1">
          Session correlation · {testLog?.n_actions ?? 0} action(s)
        </div>
        {Object.keys(table).length === 0 && <div className="text-slate-400">No actions yet.</div>}
        {Object.entries(table).map(([stim, row]) => (
          <div key={stim} className="flex items-center gap-2 py-0.5">
            <span className="font-mono w-24">{stim}</span>
            <span className="text-slate-400">{row.n_actions}×</span>
            <span className="flex gap-1">
              {Object.entries(row.symbols).map(([sym, n]) => (
                <span key={sym} className="bg-slate-100 rounded px-1.5">
                  {sym} {n}
                </span>
              ))}
            </span>
          </div>
        ))}
      </div>
      {testLog && <p className="text-xs text-slate-400">{testLog.note}</p>}
    </div>
  );
}