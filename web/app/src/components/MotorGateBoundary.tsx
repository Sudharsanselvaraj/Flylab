import { useStore } from "../state/useStore";

export function MotorGateBoundary() {
  const { neuralGate, wheelchair, neuralData, currentStimulus } = useStore();

  const gate = neuralGate;
  const blocked = gate ? gate.gate_state === "blocked" : (wheelchair?.gate_state ?? "blocked") === "blocked";

  const hasObserved = neuralData?.some((c) => (c.role ?? "visible") === "visible") ?? false;
  const hasTruth = neuralData?.some((c) => c.role === "ground_truth") ?? false;

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium text-slate-700">Motor Gate</h3>
          <p className="text-xs text-slate-400">recorded boundary between observed and withheld</p>
        </div>
        <span
          className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
            blocked ? "bg-red-50 text-red-700 border border-red-200" : "bg-emerald-50 text-emerald-700 border border-emerald-200"
          }`}
        >
          {blocked ? "BLOCKED" : "ACTIVE"}
        </span>
      </div>

      <div className="space-y-0">
        <Stage
          role="OBSERVED"
          title="Upstream representation"
          detail="flyvis optic-lobe drive → MaleCNS premotor relays"
          color="text-cyan-700"
          strip="border-l-2 border-cyan-400"
        />
        <ArrowDown />
        <GateBar blocked={blocked} />
        <ArrowDown />
        <Stage
          role="WITHHELD GROUND TRUTH"
          title="DNp01"
          detail={hasTruth ? "recorded command output — not visible to the decoder" : "no recorded DNp01 trace for this stimulus"}
          muted={!hasTruth}
          color="text-emerald-700"
          strip="border-l-2 border-emerald-400"
        />
        <ArrowDown />
        <Stage
          role="MOTOR"
          title="No motor record"
          detail={
            blocked
              ? "output withheld in the recorded experiment — nothing past the gate"
              : "no motor channel is recorded; this boundary is a pairing contract"
          }
          muted
          color="text-slate-500"
          strip="border-l-2 border-slate-300"
        />
      </div>

      <p className="text-xs text-slate-400 italic">
        {hasObserved
          ? `Stimulus ${currentStimulus ?? ""} · ${blocked ? "gate blocked — decoder sees upstream only" : "gate active"}.`
          : "Load a stimulus to read the recorded boundary."}
        {gate?.dynamics_validated === false && " Dynamics NOT validated."}
      </p>
    </div>
  );
}

function Stage({ role, title, detail, color, strip, muted }: { role: string; title: string; detail: string; color: string; strip: string; muted?: boolean }) {
  return (
    <div className={`relative pl-4 ${muted ? "opacity-70" : ""}`}>
      <div className={strip}>
        <div className="px-2 py-1.5">
          <p className={`text-[10px] font-semibold tracking-wider ${color}`}>{role}</p>
          <p className="text-xs font-medium text-slate-700">{title}</p>
          <p className="text-[11px] text-slate-400">{detail}</p>
        </div>
      </div>
    </div>
  );
}

function GateBar({ blocked }: { blocked: boolean }) {
  return (
    <div className="flex items-center gap-3 py-1">
      <div className={`flex-1 ${blocked ? "gate-hatch" : "bg-emerald-100"}`} style={{ height: 8 }} />
      <span className={`text-[10px] font-semibold tracking-wide ${blocked ? "text-red-700" : "text-emerald-700"}`}>
        {blocked ? "GATE BLOCKED" : "GATE ACTIVE"}
      </span>
      <div className={`flex-1 ${blocked ? "gate-hatch" : "bg-emerald-100"}`} style={{ height: 8 }} />
    </div>
  );
}

function ArrowDown() {
  return (
    <div className="flex justify-center text-slate-300 text-xs leading-none py-0.5" aria-hidden>
      ↓
    </div>
  );
}