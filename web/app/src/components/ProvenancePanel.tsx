import { useStore } from "../state/useStore";
import { statusColor } from "../utils/labels";
import type { ProvenanceFlags } from "../types/experiment";

const FLAG_ORDER: Array<{ key: keyof ProvenanceFlags; label: string }> = [
  { key: "dynamics_validated", label: "dynamics_validated" },
  { key: "flyvis_to_malecns_mapping_verified", label: "flyvis→malecns mapping_verified" },
  { key: "connectome_edges_verified", label: "connectome_edges_verified" },
  { key: "cell_identity_verified", label: "cell_identity_verified" },
];

export function ProvenancePanel() {
  const { provenance, decoder, currentRunId, currentStimulus } = useStore();
  if (!provenance) return <EmptyState />;

  const { layers, flags, dataset, mapping } = provenance;
  const safeFlags = flags ?? {};
  const safeLayers = Array.isArray(layers) ? layers : [];
  const mappingLabel =
    typeof mapping === "string" ? mapping : mapping && "mode" in mapping ? mapping.mode : undefined;

  const vintage = decoder ? (decoder.mapping_verified ? "grounded premotor" : "legacy proxy") : undefined;

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-slate-700">Provenance &amp; Honesty</h3>
        <VintageBadge vintage={vintage} />
      </div>
      <div className="flex flex-wrap gap-2 text-xs">
        <Pill label="run" value={currentRunId ?? provenance.run_id} />
        <Pill label="stimulus" value={currentStimulus ?? "—"} />
        <Pill label="dataset" value={dataset} />
        <Pill label="mapping" value={mappingLabel ?? "n/a"} />
      </div>
      <div className="flex flex-wrap gap-2 text-xs">
        {FLAG_ORDER.filter(({ key }) => typeof safeFlags[key] === "boolean").map(({ key, label }) => (
          <FlagBadge key={key} label={label} value={safeFlags[key] as boolean} />
        ))}
      </div>
      <div className="space-y-1.5">
        {safeLayers.map((layer, i) => (
          <div key={i} className="flex items-center justify-between text-xs px-2 py-1 rounded bg-slate-50">
            <span className="text-slate-600">{layer.label}</span>
            <div className="flex items-center gap-2">
              <span className="text-slate-400">{layer.layer}</span>
              <span className={`rounded-full px-2 py-0.5 font-medium ${statusColor(layer.status)}`}>
                {layer.status}
              </span>
            </div>
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-400 italic">
        {safeFlags.dynamics_validated ? "Dynamics validated" : "Dynamics NOT validated — record only, no live motor"}
      </p>
      {provenance.mapping && typeof provenance.mapping === "object" && "note" in provenance.mapping && provenance.mapping.note && (
        <p className="text-[11px] text-slate-400 leading-snug">{provenance.mapping.note}</p>
      )}
    </div>
  );
}

function Pill({ label, value }: { label: string; value: string }) {
  return (
    <span className="bg-slate-100 rounded-full px-2.5 py-0.5 text-slate-700">
      <span className="text-slate-400">{label}:</span> {value}
    </span>
  );
}

function FlagBadge({ label, value }: { label: string; value: boolean }) {
  return (
    <span className={`rounded-full px-2.5 py-0.5 font-medium ${value ? "bg-emerald-100 text-emerald-800" : "bg-red-50 text-red-700"}`}>
      {label}: {value ? "yes" : "no"}
    </span>
  );
}

function VintageBadge({ vintage }: { vintage?: string }) {
  if (!vintage) return null;
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${vintage === "grounded premotor" ? "bg-emerald-50 text-emerald-800 border border-emerald-200" : "bg-slate-100 text-slate-600"}`}>
      {vintage}
    </span>
  );
}

function EmptyState() {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4">
      <h3 className="text-sm font-medium text-slate-700">Provenance &amp; Honesty</h3>
      <p className="text-sm text-slate-400 mt-2">Select a run to view provenance</p>
    </div>
  );
}