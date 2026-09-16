import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { useStore } from "../state/useStore";
import { DecoderPanel } from "../components/DecoderPanel";

const DECODER = {
  mapping_verified: true,
  mapping_type: "connectome_grounded",
  regression: { profile: { r2: 0.9844 }, channel: { r2: 0.7308 }, design: { dyn_N: 12 } },
  run_connectome: { connected_component_size: 379 },
  caveat: "Pre-motor decoding is model-inferred, not a record of biological fixtures.",
  caveats: ["pre-motor", "not MVC"],
};

describe("DecoderPanel", () => {
  it("renders R² metrics and the model-inferred caveat", () => {
    useStore.setState({ decoder: DECODER as never });
    render(<DecoderPanel />);
    expect(screen.getByText("0.9844")).toBeInTheDocument();
    expect(screen.getByText("0.7308")).toBeInTheDocument();
    expect(screen.getByText(/model-inferred/)).toBeInTheDocument();
  });

  it("labels mapping as connectome-grounded", () => {
    useStore.setState({ decoder: DECODER as never });
    render(<DecoderPanel />);
    expect(screen.getByText("connectome-grounded")).toBeInTheDocument();
  });

  it("shows empty state without a decoder", () => {
    useStore.setState({ decoder: null });
    render(<DecoderPanel />);
    expect(screen.getByText("Select a run to view decoder results")).toBeInTheDocument();
  });
});