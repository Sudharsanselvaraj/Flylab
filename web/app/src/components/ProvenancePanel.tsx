import { useStore } from "../state/useStore";
import { statusColor } from "../utils/labels";

export function ProvenancePanel() {
  const { provenance } = useStore();
  if (!provenance) return <EmptyState />;

  const { layers, flags, dataset, mapping, topology } = provenance;
  const mappingLabel = typeof mapping === "string" ? mapping : mapping.mode;

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-3">
      <h3 className="text-sm font-medium text-slate-700">Provenance &amp; Honesty</h3>
      <div className="flex flex-wrap gap-2 text-xs">
        <Pill label="dataset" value={dataset} />
        <Pill label="mapping" value={mappingLabel} />
        <Pill label="topology" value={topology} />
      </div>
      <div className="grid grid-cols-3 gap-2 text-xs">
        <FlagBadge label="dynamics_validated" value={flags.dynamics_validated} />
        <FlagBadge label="connectome_edges_verified" value={flags.connectome_edges_verified} />
        <FlagBadge label="topology_validated" value={flags.topology_validated} />
      </div>
      <div className="space-y-1.5">
        {layers.map((layer, i) => (
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
        {flags.dynamics_validated ? "Dynamics validated" : "Dynamics NOT validated — wheel only, no motor recordable"}
      </p>
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

function EmptyState() {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4">
      <h3 className="text-sm font-medium text-slate-700">Provenance &amp; Honesty</h3>
      <p className="text-sm text-slate-400 mt-2">Select a run to view provenance</p>
    </div>
  );
}
