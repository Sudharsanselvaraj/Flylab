import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { useStore } from "../../state/useStore";
import { ExperimentScreen } from "./ExperimentScreen";

const RUNS = { runs: [{ run_id: "20260916-223510", stimuli: ["flash", "loom"], path: "x" }] };

describe("ExperimentScreen bootstrap", () => {
  beforeEach(() => {
    useStore.setState({
      mode: "idle",
      runs: [],
      currentRunId: null,
      neuralData: null,
      error: null,
    });
  });

  afterEach(() => vi.restoreAllMocks());

  it("calls fetchRuns on mount so it never hangs on 'Connecting…'", async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({ ok: true, json: () => Promise.resolve(RUNS) } as Response),
    );
    render(<ExperimentScreen />);
    await waitFor(() => {
      expect(useStore.getState().mode).toBe("selecting");
      expect(useStore.getState().runs.length).toBe(1);
    });
    // the run selector is reached — no permanent loading state
    expect(screen.getByText(/Select an Experiment/)).toBeInTheDocument();
  });

  it("shows a helpful error panel when the backend is unreachable", async () => {
    globalThis.fetch = vi.fn(() => Promise.reject(new Error("network down")));
    render(<ExperimentScreen />);
    await waitFor(() => {
      expect(useStore.getState().error).toBeTruthy();
    });
  });

  it("navigates to the dashboard after selecting a run", async () => {
    useStore.setState({ mode: "selecting", runs: RUNS.runs as never });
    globalThis.fetch = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/neural")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ channels: [] }),
        } as Response);
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ run_id: "20260916-223510", stimuli: ["flash", "loom"] }),
      } as Response);
    });
    render(<ExperimentScreen />);
    await screen.findByText("20260916-223510");
    await screen.findByRole("button", { name: /20260916-223510/ }).then((btn) => btn.click());
    await waitFor(() => {
      expect(useStore.getState().mode).toBe("running");
      expect(useStore.getState().neuralData).toEqual([]);
    });
  });
});