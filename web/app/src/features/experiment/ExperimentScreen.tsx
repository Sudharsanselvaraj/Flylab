import { Suspense, lazy } from "react";
import { RunSelector } from "../../components/RunSelector";
import { StimulusControls } from "../../components/StimulusControls";
import { MotorGatePanel } from "../../components/MotorGatePanel";
import { NeuralActivityPanel } from "../../components/NeuralActivityPanel";
import { DecoderPanel } from "../../components/DecoderPanel";
import { ProvenancePanel } from "../../components/ProvenancePanel";
import { ExperimentTimeline } from "../../components/ExperimentTimeline";
import { SelectableNeuronPanel } from "../../components/SelectableNeuronPanel";
import { ChannelFilterPanel } from "../../components/ChannelFilterPanel";
import { useStore } from "../../state/useStore";

const NeuralSubgraph = lazy(() => import("../three/NeuralSubgraph"));
const FlyPlaceholder = lazy(() => import("../../presentation/FlyPlaceholder"));

export function ExperimentScreen() {
  const { mode } = useStore();

  if (mode === "idle") return <LoadingView />;
  if (mode === "selecting") return <SelectView />;

  return <DashboardView />;
}

function LoadingView() {
  return (
    <div className="flex-1 flex items-center justify-center text-slate-400">
      Connecting to backend…
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
  const { error } = useStore();

  return (
    <div className="flex-1 p-6 space-y-6">
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid grid-cols-12 gap-6">
        {/* Left column: controls + motor gate */}
        <div className="col-span-3 space-y-4">
          <StimulusControls />
          <ChannelFilterPanel />
          <SelectableNeuronPanel />
          <MotorGatePanel />
        </div>

        {/* Center column: neural plot + timeline + 3D subgraph */}
        <div className="col-span-6 space-y-4">
          <NeuralActivityPanel />
          <ExperimentTimeline />
          <Suspense fallback={<div className="h-80 rounded-lg border border-slate-100 bg-slate-50 animate-pulse" />}>
            <NeuralSubgraph />
          </Suspense>
        </div>

        {/* Right column: decoder + provenance + fly */}
        <div className="col-span-3 space-y-4">
          <DecoderPanel />
          <ProvenancePanel />
          <Suspense fallback={<div className="h-64 rounded-lg border border-slate-100 bg-slate-50 animate-pulse" />}>
            <FlyPlaceholder />
          </Suspense>
        </div>
      </div>
    </div>
  );
}
