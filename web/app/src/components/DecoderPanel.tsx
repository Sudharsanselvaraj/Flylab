import { useStore } from "../state/useStore";

export function DecoderPanel() {
  const { decoder } = useStore();
  if (!decoder) return <EmptyState />;

  const { regression, mapping_verified, mapping_type, caveat, caveats } = decoder;
  const profileR2 = regression?.profile?.r2;
  const channelR2 = regression?.channel?.r2;
  const dynN = regression?.design?.dyn_N;
  const ccSize = decoder.run_connectome?.connected_component_size;

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-3">
      <h3 className="text-sm font-medium text-slate-700">Decoder Results</h3>
      <div className="flex items-center gap-2">
        <span className={`text-xs rounded-full px-2.5 py-0.5 ${mapping_verified ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
          {mapping_verified ? "connectome-grounded" : "legacy proxy"}
        </span>
        {mapping_type && <span className="text-xs text-slate-400">{mapping_type}</span>}
      </div>
      {caveat && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-xs text-amber-800">
          {caveat}
        </div>
      )}
      <div className="grid grid-cols-2 gap-3">
        <MetricCard label="Profile R²" value={profileR2?.toFixed(4) ?? "—"} desc="inter-cell correlation" />
        <MetricCard label="Channel R²" value={channelR2?.toFixed(4) ?? "—"} desc="cell-level decoding" />
        <MetricCard label="Run CC size" value={String(ccSize ?? "—")} desc="connected premotor nodes" />
        <MetricCard label="dyn_N" value={String(dynN ?? "—")} desc="temporal delay embedding" />
      </div>
      {caveats && caveats.length > 0 && (
        <ul className="text-xs text-slate-500 space-y-1">
          {caveats.slice(0, 3).map((c: string, i: number) => (
            <li key={i} className="before:content-['·'] before:mr-1">{c}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function MetricCard({ label, value, desc }: { label: string; value: string; desc: string }) {
  return (
    <div className="rounded-lg border border-slate-100 p-3">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-lg font-semibold text-slate-800">{value}</div>
      <div className="text-xs text-slate-400">{desc}</div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4">
      <h3 className="text-sm font-medium text-slate-700">Decoder Results</h3>
      <p className="text-sm text-slate-400 mt-2">Select a run to view decoder results</p>
    </div>
  );
}
