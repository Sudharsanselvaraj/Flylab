import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { useStore } from "../state/useStore";
import { MotorGatePanel } from "../components/MotorGatePanel";

const CHANNELS = [
  { key: "LC4", layer: "receptor", label: "LC4", values: [0.1, 0.5, 1.2], note: "receptor" },
  { key: "LPLC2", layer: "receptor", label: "LPLC2", values: [0.05, 0.1, 0.09], note: "receptor" },
] as never[];

describe("MotorGatePanel", () => {
  it("derives gate peaks from the real recorded traces", () => {
    useStore.setState({ neuralData: CHANNELS });
    render(<MotorGatePanel />);
    expect(screen.getByText("1.200")).toBeInTheDocument();
    expect(screen.getByText("0.100")).toBeInTheDocument();
    expect(screen.getByText(/not validated/)).toBeInTheDocument();
  });

  it("shows nothing without neural data", () => {
    useStore.setState({ neuralData: null as never });
    render(<MotorGatePanel />);
    expect(screen.queryByText("Motor Gate State")).toBeNull();
  });
});