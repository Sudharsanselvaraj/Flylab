import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import { useStore } from "../state/useStore";

const NEURAL = {
  mode: "replay",
  representation: "per_neuron",
  gate: {
    gate_state: "blocked",
    motor_output_withheld: true,
    withheld_truth: "DNp01",
    motor_record: false,
    dynamics_validated: false,
    label: "gate blocked",
    note: "recorded boundary",
  },
  channels: [
    { key: "relay.PVLP010.3", layer: "relay", label: "PVLP010 #3", role: "visible", values: [0.1], note: "cell" },
  ],
};

describe("neural + gate store", () => {
  beforeEach(() => {
    useStore.setState({
      currentRunId: "20260916-223510",
      currentStimulus: "loom",
      neuralData: null,
      neuralGate: null,
      neuralMode: "type_agg",
      error: null,
    });
  });

  afterEach(() => vi.restoreAllMocks());

  it("switching representation refetches the recorded trace with mode=per_neuron", async () => {
    globalThis.fetch = vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(NEURAL) } as Response));
    await useStore.getState().setNeuralMode("per_neuron");
    const url = String((globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls.at(-1)?.[0]);
    expect(url).toContain("mode=per_neuron");
    expect(useStore.getState().neuralMode).toBe("per_neuron");
    expect(useStore.getState().neuralData?.[0]?.key).toBe("relay.PVLP010.3");
    expect(useStore.getState().neuralGate?.gate_state).toBe("blocked");
  });

  it("stimulus selection loads the recorded gate boundary with it", async () => {
    globalThis.fetch = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/neural")) return Promise.resolve({ ok: true, json: () => Promise.resolve(NEURAL) } as Response);
      if (url.includes("/communication")) return Promise.reject(new Error("no comms"));
      return Promise.resolve({ ok: false, json: () => Promise.resolve(null) } as Response);
    });
    await useStore.getState().selectStimulus("loom");
    expect(useStore.getState().neuralData).toHaveLength(1);
    expect(useStore.getState().neuralGate?.motor_output_withheld).toBe(true);
    expect(useStore.getState().neuralGate?.dynamics_validated).toBe(false);
  });
});