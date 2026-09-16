import { useStore } from "../state/useStore";

export function MotorGatePanel() {
  const { neuralData } = useStore();
  if (!neuralData) return null;

  const lc4 = neuralData.find((c) => c.key === "LC4");
  const lplc2 = neuralData.find((c) => c.key === "LPLC2");
  const lc4Peak = lc4 ? Math.max(...lc4.values) : 0;
  const lplc2Peak = lplc2 ? Math.max(...lplc2.values) : 0;

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-2">
      <h3 className="text-sm font-medium text-slate-700">Motor Gate State</h3>
      <p className="text-xs text-slate-400">Model-inferred gating (not validated)</p>
      <div className="grid grid-cols-2 gap-3">
        <GateCard label="LC4" peak={lc4Peak} color="amber" />
        <GateCard label="LPLC2" peak={lplc2Peak} color="cyan" />
      </div>
      <p className="text-xs text-slate-400 italic">Not a validated motor command — display aid only</p>
    </div>
  );
}

function GateCard({ label, peak, color }: { label: string; peak: number; color: string }) {
  const bg = color === "amber" ? "bg-amber-50" : "bg-cyan-50";
  const border = color === "amber" ? "border-amber-200" : "border-cyan-200";
  const text = color === "amber" ? "text-amber-800" : "text-cyan-800";
  return (
    <div className={`rounded-lg border p-3 ${bg} ${border}`}>
      <div className="text-xs font-medium text-slate-600">{label}</div>
      <div className={`text-xl font-bold ${text}`}>{peak.toFixed(3)}</div>
      <div className="text-xs text-slate-400">peak receptor</div>
    </div>
  );
}
