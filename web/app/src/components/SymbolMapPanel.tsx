import { useStore } from "../state/useStore";

export function SymbolMapPanel() {
  const { symbolSet } = useStore();
  if (!symbolSet || !Array.isArray(symbolSet.classes) || symbolSet.classes.length === 0) return null;

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-slate-700">Symbol Map</h3>
        <span className="text-xs bg-violet-100 text-violet-700 rounded-full px-2.5 py-0.5 font-medium">
          DESIGNED UX
        </span>
      </div>
      <p className="text-xs text-slate-400">{symbolSet.note}</p>
      <div className="space-y-2">
        {symbolSet.classes.map((cls) => (
          <div key={cls.class} className="rounded-lg border border-slate-100 p-3 flex items-center gap-3">
            <span className="text-2xl w-8 text-center">{cls.symbol}</span>
            <div className="min-w-0">
              <div className="text-sm font-medium text-slate-800">{cls.label}</div>
              <div className="text-xs text-slate-400 truncate">{cls.evidence}</div>
            </div>
            {cls.baseline_accuracy != null && cls.baseline_accuracy !== undefined && (
              <span className="ml-auto text-xs bg-slate-100 text-slate-600 rounded-full px-2 py-0.5">
                acc {Number(cls.baseline_accuracy).toFixed(2)}
              </span>
            )}
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-400 italic">
        Grounded in the decoder's real escape/no-escape split — the symbols are a
        game layer, not discovered biology.
      </p>
    </div>
  );
}