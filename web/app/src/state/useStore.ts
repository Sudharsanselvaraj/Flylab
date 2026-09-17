import { create } from "zustand";
import type { ExperimentRun, DecoderResult, ExperimentProvenance, NeuralChannel, ChannelFilter, NeuronType, Dnp01Branch, SymbolSet, WheelchairState, CommunicationDecode, TestActionLog } from "../types/experiment";
import { fetchSymbols, fetchWheelchair, fetchCommunication, postTestAction } from "../api/client";

type AppMode = "idle" | "selecting" | "running";

interface AppState {
  mode: AppMode;
  runs: ExperimentRun[];
  currentRunId: string | null;
  currentStimulus: string | null;
  provenance: ExperimentProvenance | null;
  decoder: DecoderResult | null;
  neuralData: NeuralChannel[] | null;
  symbolSet: SymbolSet | null;
  wheelchair: WheelchairState | null;
  communication: CommunicationDecode | null;
  testLog: TestActionLog | null;
  channelFilter: ChannelFilter;
  selectedNeuronType: NeuronType;
  selectedBranch: Dnp01Branch;
  replayFrame: number;
  isPlaying: boolean;
  error: string | null;
  fetchRuns: () => Promise<void>;
  selectRun: (runId: string) => Promise<void>;
  selectStimulus: (stimulus: string) => Promise<void>;
  logTestAction: (symbol: string) => Promise<void>;
  setReplayFrame: (frame: number) => void;
  setIsPlaying: (playing: boolean) => void;
  toggleChannelFilter: (key: keyof ChannelFilter) => void;
  setSelectedNeuronType: (type: NeuronType) => void;
  setSelectedBranch: (branch: Dnp01Branch) => void;
}

const API_BASE = "/api";

export const useStore = create<AppState>((set, get) => ({
  mode: "idle",
  runs: [],
  currentRunId: null,
  currentStimulus: null,
  provenance: null,
  decoder: null,
  neuralData: null,
  symbolSet: null,
  wheelchair: null,
  communication: null,
  testLog: null,
  channelFilter: { lc4: true, lplc2: true, relay: true, dnp01: true },
  selectedNeuronType: null,
  selectedBranch: null,
  replayFrame: 0,
  isPlaying: false,
  error: null,

  fetchRuns: async () => {
    try {
      const r = await fetch(`${API_BASE}/experiments`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      set({ runs: data.runs, mode: "selecting" });
    } catch (e: unknown) {
      set({ error: `Failed to load experiments: ${e instanceof Error ? e.message : e}`, mode: "idle" });
    }
  },

  selectRun: async (runId: string) => {
    set({ currentRunId: runId, error: null });
    const [runData, provenance, decoder, symbolSet, wheelchair] = await Promise.all([
      fetch(`${API_BASE}/experiments/${runId}`).then((r) => r.json()),
      fetch(`${API_BASE}/experiments/${runId}/provenance`).then((r) => (r.ok ? r.json() : null)),
      fetch(`${API_BASE}/experiments/${runId}/decoder`).then((r) => (r.ok ? r.json() : null)),
      fetchSymbols(runId).catch(() => null),
      fetchWheelchair(runId).catch(() => null),
    ]);
    set({ provenance, decoder, symbolSet, wheelchair, currentStimulus: runData.stimuli[0] ?? null, mode: "running", communication: null, testLog: null });
    if (runData.stimuli[0]) await get().selectStimulus(runData.stimuli[0]);
  },

  selectStimulus: async (stimulus: string) => {
    const { currentRunId } = get();
    if (!currentRunId) return;
    set({ currentStimulus: stimulus, neuralData: null, error: null, replayFrame: 0, isPlaying: false, communication: null });
    try {
      const r = await fetch(`${API_BASE}/experiments/${currentRunId}/neural?stimulus=${encodeURIComponent(stimulus)}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      set({ neuralData: data.channels });
    } catch (e: unknown) {
      set({ error: `Failed to load neural data: ${e instanceof Error ? e.message : e}` });
    }
    try {
      const comms = await fetchCommunication(currentRunId, stimulus);
      set({ communication: comms });
    } catch (e: unknown) {
      set({ error: `Failed to load communication decode: ${e instanceof Error ? e.message : e}` });
    }
  },

  logTestAction: async (symbol: string) => {
    const { currentRunId, currentStimulus } = get();
    if (!currentRunId || !currentStimulus) return;
    try {
      const log = await postTestAction(currentRunId, currentStimulus, symbol);
      set({ testLog: log });
    } catch (e: unknown) {
      set({ error: `Failed to log test action: ${e instanceof Error ? e.message : e}` });
    }
  },

  setReplayFrame: (frame: number) => set({ replayFrame: frame }),
  setIsPlaying: (playing: boolean) => set({ isPlaying: playing }),
  toggleChannelFilter: (key: keyof ChannelFilter) =>
    set((s) => ({ channelFilter: { ...s.channelFilter, [key]: !s.channelFilter[key] } })),
  setSelectedNeuronType: (type: NeuronType) => set({ selectedNeuronType: type }),
  setSelectedBranch: (branch: Dnp01Branch) => set({ selectedBranch: branch }),
}));
