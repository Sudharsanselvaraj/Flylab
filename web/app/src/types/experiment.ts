export interface NeuralChannel {
  key: string;
  layer: "receptor" | "relay" | "dnp01";
  label: string;
  values: number[];
  note: string;
}

export interface ExperimentRun {
  run_id: string;
  stimuli: string[];
  mode: "replay" | "live";
  manifest: Record<string, unknown>;
  mapping: string;
}

export interface DecoderResult {
  mapping_verified: boolean;
  regression: {
    profile: { r2: number };
    channel: { r2: number };
    design: { dyn_N: number };
  };
  run_connectome: { connected_component_size: number };
  mapping_type: string;
  caveat: string;
  caveats: string[];
}

export interface ProvenanceLayer {
  label: string;
  layer:
    | "MaleCNS connectivity"
    | "FlyVis visual model"
    | "Wheelchair / avatar"
    | "Contrast";
  status: "MEASURED" | "SYNTHESIZED" | "PRESENTATION" | "ABSENT";
}

export interface ProvenanceFlags {
  dynamics_validated: boolean;
  connectome_edges_verified: boolean;
  topology_validated: boolean;
}

export interface ExperimentProvenance {
  run_id: string;
  dataset: string;
  mapping: string;
  topology: string;
  flags: ProvenanceFlags;
  layers: ProvenanceLayer[];
}

export interface RunnableStimulus {
  stimulus: string;
  available: boolean;
}

export interface CurrentRun {
  run_id: string;
  stimulus: string;
  available: boolean;
  active_stimuli: string[];
  provenance?: ExperimentProvenance;
  decoder?: DecoderResult;
  neural_sample?: number;
  neural_frames?: number;
  status: "idle" | "loading" | "playing" | "paused" | "complete" | "error";
  error?: string;
}

export interface ChannelFilter {
  lc4: boolean;
  lplc2: boolean;
  relay: boolean;
  dnp01: boolean;
}

export type NeuronType = "LC4" | "LPLC2" | "relay" | "DNp01" | null;

export type Dnp01Branch = "0" | "1" | null;
