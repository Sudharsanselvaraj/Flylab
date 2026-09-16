import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { useStore } from "../state/useStore";
import { StimulusControls } from "../components/StimulusControls";

const RUN = {
  run_id: "20260916-223510",
  stimuli: ["flash", "moving_edge", "loom"],
};

const NEURAL = {
  channels: [
    { key: "LC4", layer: "receptor", label: "LC4", values: [0.1, 0.2, 0.3], note: "receptor macro" },
    { key: "relay.PVLP010", layer: "relay", label: "Relay PVLP010", values: [0.05, 0.06, 0.07], note: "relay macro" },
    { key: "DNp01.0", layer: "dnp01", label: "DNp01.0", values: [0.5, 0.4, 0.3], note: "dnp01 trace" },
  ],
};

describe("StimulusControls", () => {
  beforeEach(() => {
    useStore.setState({ runs: [RUN as never], currentRunId: RUN.run_id });
    globalThis.fetch = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/neural")) return Promise.resolve({ ok: true, json: () => Promise.resolve(NEURAL) } as Response);
      if (url.includes("/provenance")) return Promise.resolve({ ok: false, json: () => Promise.resolve(null) } as Response);
      if (url.includes("/decoder")) return Promise.resolve({ ok: false, json: () => Promise.resolve(null) } as Response);
      return Promise.resolve({ ok: true, json: () => Promise.resolve(RUN) } as Response);
    });
  });

  afterEach(() => vi.restoreAllMocks());

  it("renders the three recorded stimuli as buttons", () => {
    render(<StimulusControls />);
    expect(screen.getByRole("button", { name: "flash" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "moving edge" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "loom" })).toBeInTheDocument();
  });

  it("switches the active stimulus and fetches its neural data", async () => {
    useStore.setState({ currentStimulus: "flash" });
    render(<StimulusControls />);
    fireEvent.click(screen.getByRole("button", { name: "loom" }));
    await waitFor(() => expect(useStore.getState().currentStimulus).toBe("loom"));
    expect(useStore.getState().neuralData).toBeTruthy();
    expect(useStore.getState().neuralData!.length).toBe(3);
  });

  it("never shows a stimulus that was not recorded", () => {
    render(<StimulusControls />);
    expect(screen.queryByRole("button", { name: /bogus/ })).toBeNull();
  });
});