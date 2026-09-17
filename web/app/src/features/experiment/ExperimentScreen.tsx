import { Suspense, lazy, useEffect, useState } from "react";
import { RunSelector } from "../../components/RunSelector";
import { StimulusControls } from "../../components/StimulusControls";
import { MotorGateBoundary } from "../../components/MotorGateBoundary";
import { NeuralActivityPanel } from "../../components/NeuralActivityPanel";
import { DecoderPanel } from "../../components/DecoderPanel";
import { ProvenancePanel } from "../../components/ProvenancePanel";
import { ExperimentTimeline } from "../../components/ExperimentTimeline";
import { ExperimentContext } from "../../components/ExperimentContext";
import { SymbolMapPanel } from "../../components/SymbolMapPanel";
import { CommunicationPanel } from "../../components/CommunicationPanel";
import { DiscoveryConsole } from "../../components/DiscoveryConsole";
import { ErrorBoundary } from "../../components/ErrorBoundary";
import { useStore } from "../../state/useStore";
import type { NeuronType } from "../../types/experiment";

const NeuralSubgraph = lazy(() => import("../three/NeuralSubgraph"));
const FlyPlaceholder = lazy(() => import("../../presentation/FlyPlaceholder"));

const NEURON_TYPES: Array<{ id: NeuronType; label: string }> = [
  { id: "LC4", label: "LC4" },
  { id: "LPLC2", label: "LPLC2" },
  { id: "relay", label: "Relay" },
  { id: "DNp01", label: "DNp01" },
];

export function ExperimentScreen() {
  const { mode, runs, fetchRuns } = useStore();

  useEffect(() => {
    if (runs.length === 0) void fetchRuns();
  }, [runs.length, fetchRuns]);

  if (mode === "idle") return <LoadingView />;
  if (mode === "selecting") return <SelectView />;

  return <DashboardView />;
}

function Missing3DView({ what }: { what: string }) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 text-sm text-slate-500">
      {what} unavailable (WebGL not supported or 3D failed to load) — rest of the app is fine.
    </div>
  );
}

function LoadingView() {
  return (
    <div className="flex-1 flex items-center justify-center text-slate-400">
      Connecting to backend… (make sure the FastAPI replay server is running on :8050)
    </div>
  );
}

function SelectView() {
  return (
    <div className="flex-1 p-6 max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-xl font-semibold text-slate-800">Select an Experiment</h2>
        <p className="text-sm text-slate-400 mt-1">Phase 0D — replay-only mode, no live simulation</p>
      </div>
      <RunSelector />
    </div>
  );
}

function DashboardView() {
  const { error, decoder, currentRunId, provenance, currentStimulus } = useStore();
  const vintage = decoder ? (decoder.mapping_verified ? "grounded premotor" : "legacy proxy") : "—";
  const dynamicsValidated = provenance?.flags?.dynamics_validated;

  return (
    <div className="flex-1 p-6">
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700 mb-4">
          {error}
        </div>
      )}

      <div className="max-w-[1440px] mx-auto space-y-5">
        {/* top strip: experiment controls + honesty flags */}
        <div className="flex flex-wrap items-center gap-x-8 gap-y-4">
          <div className="min-w-[260px]">
            <StimulusControls />
          </div>
          <div className="flex items-center gap-3 text-xs text-slate-500">
            <span className="font-mono text-[11px] text-slate-400">{currentRunId ?? "—"}</span>
            <span className="text-slate-300">|</span>
            <span>stimulus <span className="font-medium text-slate-700">{currentStimulus ?? "—"}</span></span>
            <span className="text-slate-300">|</span>
            <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-slate-700">
              <span className="text-slate-400">vintage:</span> {vintage}
            </span>
            {typeof dynamicsValidated === "boolean" && (
              <span
                className={`rounded-full px-2.5 py-0.5 ${dynamicsValidated ? "bg-emerald-100 text-emerald-800" : "bg-red-50 text-red-700"}`}
              >
                dynamics {dynamicsValidated ? "validated" : "NOT validated"}
              </span>
            )}
          </div>
        </div>

        <div className="grid grid-cols-12 gap-5 items-start">
          {/* Left — observed upstream scene */}
          <div className="col-span-12 lg:col-span-7 space-y-4">
            <NeuralActivityPanel />

            <div className="bg-white rounded-lg border border-slate-200 p-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium text-slate-700">Premotor subgraph</h3>
                <div className="flex rounded-lg border border-slate-200 overflow-hidden text-xs">
                  {NEURON_TYPES.map(({ id, label }) => (
                    <HighlightButton key={label} id={id} label={label} />
                  ))}
                  <HighlightButton id={null} label="none" />
                </div>
              </div>
              <ErrorBoundary fallback={() => <Missing3DView what="premotor subgraph" />}>
                <Suspense fallback={<div className="h-80 rounded-lg border border-slate-100 bg-slate-50 animate-pulse" />}>
                  <NeuralSubgraph />
                </Suspense>
              </ErrorBoundary>
              <p className="text-[11px] text-slate-400 mt-1.5">
                Real loom-escape connectivity; node positions are layout placeholders — no skeleton/geometry claim.
              </p>
            </div>

            <ExperimentTimeline />
            <ExperimentContext />
          </div>

          {/* Right — gate, world, decoder, provenance */}
          <div className="col-span-12 lg:col-span-5 space-y-4">
            <MotorGateBoundary />
            <ErrorBoundary fallback={() => <Missing3DView what="fly presentation" />}>
              <Suspense fallback={<div className="h-56 rounded-lg border border-slate-100 bg-slate-50 animate-pulse" />}>
                <FlyPlaceholder />
              </Suspense>
            </ErrorBoundary>
            <DecoderPanel />
            <ProvenancePanel />
          </div>
        </div>

        {/* Phase 0E — designed-UX exploration layer */}
        <DiscoverySection />
      </div>
    </div>
  );
}

function HighlightButton({ id, label }: { id: NeuronType; label: string }) {
  const { selectedNeuronType, setSelectedNeuronType } = useStore();
  return (
    <button
      onClick={() => setSelectedNeuronType(selectedNeuronType === id ? null : id)}
      className={`px-2.5 py-1.5 ${selectedNeuronType === id ? "bg-slate-900 text-white" : "bg-white text-slate-600 hover:bg-slate-50"}`}
    >
      {label}
    </button>
  );
}

function DiscoverySection() {
  const [open, setOpen] = useState(true);
  return (
    <section className="bg-white rounded-lg border border-slate-200">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-3 text-left"
      >
        <div>
          <h3 className="text-sm font-medium text-slate-700">Designed-UX exploration layer</h3>
          <p className="text-xs text-slate-400">
            Phase 0E — symbolic layer on real decoder classes; labeled “designed UX”, no scientific content added.
          </p>
        </div>
        <span className="text-slate-400 text-xs">{open ? "hide" : "show"}</span>
      </button>
      {open && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 px-4 pb-4">
          <SymbolMapPanel />
          <CommunicationPanel />
          <DiscoveryConsole />
        </div>
      )}
    </section>
  );
}