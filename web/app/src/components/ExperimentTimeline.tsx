import { useEffect, useRef, useCallback } from "react";
import { useStore } from "../state/useStore";

export function ExperimentTimeline() {
  const { neuralData, replayFrame, setReplayFrame, isPlaying, setIsPlaying } = useStore();
  const totalFrames = neuralData?.[0]?.values.length ?? 0;
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const togglePlay = useCallback(() => {
    if (totalFrames === 0) return;
    setIsPlaying(!isPlaying);
  }, [isPlaying, setIsPlaying, totalFrames]);

  useEffect(() => {
    if (isPlaying && totalFrames > 0) {
      timerRef.current = setInterval(() => {
        setReplayFrame((useStore.getState().replayFrame + 1) % totalFrames);
      }, 20);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [isPlaying, totalFrames, setReplayFrame]);

  if (totalFrames === 0) return null;

  const pct = totalFrames > 0 ? (replayFrame / totalFrames) * 100 : 0;

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-slate-700">Replay</h3>
        <span className="text-xs text-slate-400 font-mono">
          {replayFrame}/{totalFrames}
        </span>
      </div>
      <div className="flex items-center gap-3">
        <button
          onClick={togglePlay}
          className="w-8 h-8 rounded bg-slate-900 text-white flex items-center justify-center text-sm hover:bg-slate-700"
        >
          {isPlaying ? "⏸" : "▶"}
        </button>
        <input
          type="range"
          min={0}
          max={totalFrames - 1}
          value={replayFrame}
          onChange={(e) => setReplayFrame(Number(e.target.value))}
          className="flex-1 h-1.5 rounded bg-slate-200 cursor-pointer"
        />
      </div>
      <div className="h-1 rounded bg-slate-100 overflow-hidden">
        <div className="h-full bg-slate-900 rounded transition-all" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
