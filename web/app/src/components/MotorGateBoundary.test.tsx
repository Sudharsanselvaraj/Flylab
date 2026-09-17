import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { useStore } from "../state/useStore";
import { MotorGateBoundary } from "../components/MotorGateBoundary";

const GATE_BLOCKED = {
  run_id: "20260916-223510",
  gate_state: "blocked",
  motor_output_withheld: true,
  withheld_truth: "DNp01",
  motor_record: false,
  dynamics_validated: false,
  label: "gate blocked — motor output withheld, decoder sees upstream only",
  note: "recorded motor-gate state",
};

const CHANNELS = [
  { key: "relay.PVLP010", layer: "relay", label: "PVLP010", role: "visible", values: [0.1, 0.2], note: "relay" },
  { key: "DNp01.0", layer: "dnp01", label: "DNp01 (R)", role: "ground_truth", withheld: true, values: [0.5, 0.6], note: "dnp01" },
] as never[];

describe("MotorGateBoundary", () => {
  it("tells the blocked story: observed → blocked gate → withheld DNp01 → no motor record", () => {
    useStore.setState({ neuralGate: GATE_BLOCKED as never, neuralData: CHANNELS, currentStimulus: "loom" });
    render(<MotorGateBoundary />);
    expect(screen.getByText("BLOCKED")).toBeInTheDocument();
    expect(screen.getByText("OBSERVED")).toBeInTheDocument();
    expect(screen.getByText("WITHHELD GROUND TRUTH")).toBeInTheDocument();
    expect(screen.getByText("No motor record")).toBeInTheDocument();
    expect(screen.getByText(/Dynamics NOT validated/)).toBeInTheDocument();
  });

  it("never claims validated dynamics even when gate is active", () => {
    useStore.setState({
      neuralGate: { ...GATE_BLOCKED, gate_state: "active", motor_output_withheld: false } as never,
      neuralData: null,
    });
    render(<MotorGateBoundary />);
    expect(screen.getByText("ACTIVE")).toBeInTheDocument();
    expect(screen.getByText(/no motor channel is recorded/)).toBeInTheDocument();
  });

  it("falls back to the recorded wheelchair gate state when the neural gate is absent", () => {
    useStore.setState({
      neuralGate: null,
      wheelchair: { gate_state: "blocked", motor_output_withheld: true, dynamics_validated: false } as never,
      neuralData: null,
    });
    render(<MotorGateBoundary />);
    expect(screen.getByText("BLOCKED")).toBeInTheDocument();
  });

  it("shows the empty gate without data", () => {
    useStore.setState({ neuralGate: null, wheelchair: null, neuralData: null, currentStimulus: null });
    render(<MotorGateBoundary />);
    expect(screen.getByText(/Load a stimulus/)).toBeInTheDocument();
  });
});