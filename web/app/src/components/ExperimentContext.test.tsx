import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { useStore } from "../state/useStore";
import { ExperimentContext } from "../components/ExperimentContext";

describe("ExperimentContext", () => {
  it("states what is observed, blocked, ground truth, and inferred", () => {
    useStore.setState({ decoder: null });
    render(<ExperimentContext />);
    expect(screen.getByText(/upstream neural activity reveal a blocked motor command/)).toBeInTheDocument();
    expect(screen.getByText("OBSERVED")).toBeInTheDocument();
    expect(screen.getByText("BLOCKED")).toBeInTheDocument();
    expect(screen.getByText("GROUND TRUTH")).toBeInTheDocument();
    expect(screen.getByText("INFERRED")).toBeInTheDocument();
  });

  it("labels the decoder study honestly as proxy/infrastructure", () => {
    useStore.setState({ decoder: { mapping_type: "connectome_grounded" } as never });
    render(<ExperimentContext />);
    expect(screen.getByText(/proxy\/infrastructure.*model-inferred/)).toBeInTheDocument();
  });
});