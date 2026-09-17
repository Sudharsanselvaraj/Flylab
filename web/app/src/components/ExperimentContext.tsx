import { useStore } from "../state/useStore";

const ROWS = [
  {
    tag: "OBSERVED",
    color: "text-cyan-700 border-cyan-200 bg-cyan-50",
    title: "Upstream neural activity",
    detail: "flyvis drive onto MaleCNS premotor relays — the only signal the decoder may see.",
  },
  {
    tag: "BLOCKED",
    color: "text-red-700 border-red-200 bg-red-50",
    title: "Motor output withheld",
    detail: "the recorded experiment held back DNp01 motor output — nothing is recorded past the gate.",
  },
  {
    tag: "GROUND TRUTH",
    color: "text-emerald-700 border-emerald-200 bg-emerald-50",
    title: "DNp01 command output",
    detail: "recorded but withheld; used only to score the decoder, never shown to it.",
  },
  {
    tag: "INFERRED",
    color: "text-amber-700 border-amber-200 bg-amber-50",
    title: "Model-inferred decode",
    detail: "any downstream decode is a model estimate — never the fly's intent or a validated motor signal.",
  },
] as const;

export function ExperimentContext() {
  const { decoder } = useStore();
  const decoderAvailable = decoder?.mapping_type !== undefined;
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-3">
      <div>
        <h3 className="text-sm font-medium text-slate-700">Experiment</h3>
        <p className="text-xs text-slate-400">“Can upstream neural activity reveal a blocked motor command?”</p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {ROWS.map((r) => (
          <div key={r.tag} className="rounded-lg border border-slate-100 p-2.5">
            <span className={`inline-block rounded border px-1.5 py-0.5 text-[10px] font-semibold tracking-wide ${r.color}`}>
              {r.tag}
            </span>
            <p className="text-xs font-medium text-slate-700 mt-1">{r.title}</p>
            <p className="text-[11px] text-slate-400 leading-snug">{r.detail}</p>
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-400">
        Decoder study:{" "}
        {decoderAvailable ? (
          <span className="text-amber-700 font-medium">proxy/infrastructure — results labeled model-inferred, not validated</span>
        ) : (
          <span className="text-slate-400">no decoder artifacts for this run — nothing inferred</span>
        )}
      </p>
    </div>
  );
}