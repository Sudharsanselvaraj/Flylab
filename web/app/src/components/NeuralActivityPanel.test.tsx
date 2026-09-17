import { beforeEach, describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { useStore } from "../state/useStore";
import { NeuralActivityPanel } from "../components/NeuralActivityPanel";

const CHANNELS = [
  { key: "LC4", layer: "receptor", label: "LC4", role: "visible", values: [0.1, 0.2, 0.3], note: "receptor drive" },
  { key: "relay.PVLP010", layer: "relay", label: "PVLP010", role: "visible", values: [0.05, 0.06, 0.07], note: "relay mean" },
  { key: "DNp01.0", layer: "dnp01", label: "DNp01 (R)", role: "ground_truth", withheld: true, values: [0.5, 0.4, 0.3], note: "dnp01 trace" },
] as never[];

describe("NeuralActivityPanel", () => {
  beforeEach(() => {
    useStore.setState({
      neuralData: CHANNELS,
      neuralMode: "type_agg",
      channelFilter: { lc4: true, lplc2: true, relay: true, dnp01: true },
      replayFrame: 0,
    });
  });

  it("splits VISIBLE upstream from GROUND TRUTH withheld DNp01", () => {
    render(<NeuralActivityPanel />);
    expect(screen.getByText("VISIBLE")).toBeInTheDocument();
    expect(screen.getByText("Upstream representation")).toBeInTheDocument();
    expect(screen.getByText("GROUND TRUTH")).toBeInTheDocument();
    expect(screen.getByText(/withheld behind the gate/)).toBeInTheDocument();
    expect(screen.getByText(/not validated motor command/)).toBeInTheDocument();
  });

  it("offers the per-neuron secondary representation", () => {
    render(<NeuralActivityPanel />);
    expect(screen.getByRole("button", { name: "per-neuron" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "type-agg" })).toBeInTheDocument();
  });

  it("shows the empty prompt before any stimulus is loaded", () => {
    useStore.setState({ neuralData: null });
    render(<NeuralActivityPanel />);
    expect(screen.getByText(/Select a stimulus/)).toBeInTheDocument();
  });
});