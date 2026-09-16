import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { useStore } from "../state/useStore";
import { ExperimentTimeline } from "../components/ExperimentTimeline";

const NEURAL = [
  { key: "LC4", layer: "receptor", label: "LC4", values: [0.1, 0.2, 0.3, 0.4], note: "x" },
];

describe("ExperimentTimeline", () => {
  it("toggles play/pause and advances the replay frame", () => {
    useStore.setState({
      neuralData: NEURAL as never,
      replayFrame: 0,
      isPlaying: false,
    });
    render(<ExperimentTimeline />);
    const playBtn = screen.getByRole("button");
    fireEvent.click(playBtn);
    expect(useStore.getState().isPlaying).toBe(true);
    fireEvent.click(playBtn);
    expect(useStore.getState().isPlaying).toBe(false);
  });

  it("shows the current frame count from recorded data", () => {
    useStore.setState({
      neuralData: NEURAL as never,
      replayFrame: 2,
      isPlaying: false,
    });
    render(<ExperimentTimeline />);
    expect(screen.getByText("2/4")).toBeInTheDocument();
  });
});