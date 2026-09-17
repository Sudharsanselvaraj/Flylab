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
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ channels: [] }) } as Response);
      }
      if (url.includes("/communication")) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              run_id: "20260916-223510",
              mode: "replay",
              stimulus: "loom",
              decoded_class: "escape",
              decoded_label: "Escape",
              symbol: "\u26a1",
              confidence: 0.54,
              confidence_source: "held-out channel R\u00b2",
              framing: "model-inferred",
              note: "model-inferred decode",
            }),
        } as Response);
      }
      if (url.includes("/symbols")) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              run_id: "20260916-223510",
              mode: "replay",
              designed_ux: true,
              reveal_policy: "learn by experiment",
              label_rule: "truth norm above leave-one-out train median",
              classes: [
                { class: "escape", label: "Escape", symbol: "\u26a1", name: "escape", decoder_class: 1, evidence: "recorded dnp01 branch 1" },
                { class: "no_escape", label: "No-escape", symbol: "\u00b7", name: "no_escape", decoder_class: 0, evidence: "recorded dnp01 branch 0" },
              ],
              note: "Design layer on top of real decoder output (spec \u00a74.6).",
            }),
        } as Response);
      }
      if (url.includes("/wheelchair")) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              run_id: "20260916-223510",
              mode: "replay",
              gate_state: "blocked",
              motor_output_withheld: true,
              dynamics_validated: false,
              status: "blocked",
              label: "gate closed \u2014 motor output withheld, decoder observing",
              note: "tied to recorded motor-gate state",
            }),
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
      expect(useStore.getState().symbolSet?.classes.length).toBe(2);
      expect(useStore.getState().wheelchair?.gate_state).toBe("blocked");
      expect(useStore.getState().communication?.decoded_class).toBe("escape");
    });
  });
});