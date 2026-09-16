import { useStore } from "../state/useStore";

export function Header() {
  const { mode, currentRunId, currentStimulus } = useStore();
  return (
    <header className="bg-slate-900 text-white px-6 py-3 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="text-lg font-semibold tracking-tight">Hawking Fly</div>
        <span className="text-xs bg-slate-700 rounded px-2 py-0.5">Phase 0D</span>
        <span className="text-xs text-slate-400">replay-only · no live simulation</span>
      </div>
      <div className="flex items-center gap-4 text-sm text-slate-300">
        {currentRunId && (
          <>
            <span className="font-mono text-xs">{currentRunId}</span>
            <span className="text-slate-500">·</span>
            <span>{currentStimulus ?? "—"}</span>
          </>
        )}
        <span className={`text-xs rounded px-2 py-0.5 ${mode === "running" ? "bg-emerald-800 text-emerald-200" : "bg-slate-700 text-slate-300"}`}>
          {mode}
        </span>
      </div>
    </header>
  );
}

export function StatusBadge({ label, active }: { label: string; active: boolean }) {
  return (
    <span className={`text-xs rounded-full px-2.5 py-0.5 font-medium ${active ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-500"}`}>
      {label}
    </span>
  );
}
