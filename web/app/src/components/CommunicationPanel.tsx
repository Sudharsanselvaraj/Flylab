import { useStore } from "../state/useStore";

export function CommunicationPanel() {
  const { communication, currentStimulus } = useStore();
  if (!communication) return <EmptyState />;

  const confidence = communication.confidence;
  const pct = confidence != null ? Math.round(confidence * 100) : null;

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-3">
      <h3 className="text-sm font-medium text-slate-700">Communication Panel</h3>
      <div className="flex items-center gap-3">
        <span className="text-4xl">{communication.symbol}</span>
        <div>
          <div className="text-lg font-semibold text-slate-800">{communication.decoded_label}</div>
          <div className="text-xs text-slate-400">
            on {communication.stimulus ?? currentStimulus ?? "—"} ·{" "}
            <span className="text-amber-600 font-medium">model-inferred</span>
          </div>
        </div>
      </div>

      <div>
        <div className="flex justify-between text-xs text-slate-500 mb-1">
          <span>confidence</span>
          <span className="font-mono">{pct != null ? `${pct}%` : "n/a"}</span>
        </div>
        <div className="h-2.5 rounded bg-slate-100 overflow-hidden">
          <div
            className={confidence != null && confidence > 0.5 ? "bg-emerald-500" : "bg-slate-400"}
            style={{ width: `${confidence != null ? Math.max(0, Math.min(100, pct!)) : 4}%` }}
          />
        </div>
        <div className="text-xs text-slate-400 mt-1">{communication.confidence_source}</div>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-xs text-amber-800">
        {communication.note}
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4">
      <h3 className="text-sm font-medium text-slate-700">Communication Panel</h3>
      <p className="text-sm text-slate-400 mt-2">Select a stimulus to see the decoded symbol.</p>
    </div>
  );
}