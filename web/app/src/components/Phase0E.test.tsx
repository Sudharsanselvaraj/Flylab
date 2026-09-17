import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { useStore } from "../state/useStore";
import { SymbolMapPanel } from "../components/SymbolMapPanel";
import { CommunicationPanel } from "../components/CommunicationPanel";
import { DiscoveryConsole } from "../components/DiscoveryConsole";

const SYMBOLS = {
  run_id: "20260916-223510",
  mode: "replay",
  designed_ux: true,
  reveal_policy: "learn by experiment",
  label_rule: "truth norm above leave-one-out train median",
  classes: [
    { class: "escape", label: "Escape", symbol: "\u26a1", name: "escape", decoder_class: 1, evidence: "recorded dnp01 branch 1", baseline_accuracy: 0.8 },
    { class: "no_escape", label: "No-escape", symbol: "\u00b7", name: "no_escape", decoder_class: 0, evidence: "recorded dnp01 branch 0" },
  ],
  note: "Design layer on top of real decoder output (spec §4.6).",
};

const COMM = {
  run_id: "20260916-223510",
  mode: "replay",
  stimulus: "loom",
  decoded_class: "escape",
  decoded_label: "Escape",
  symbol: "\u26a1",
  confidence: 0.5382602429491706,
  confidence_source: "held-out channel R² (leave-loom-out fold)",
  framing: "model-inferred",
  note: "Decoded class is model-inferred, not recorded truth.",
};

const TEST_LOG = {
  run_id: "20260916-223510",
  mode: "replay",
  n_actions: 2,
  table: {
    loom: { n_actions: 2, symbols: { "\u26a1": 1, "\u00b7": 1 } },
    flash: { n_actions: 0, symbols: {} },
  },
  note: "No pre-scripted reveals; table reflects the session only.",
};

describe("SymbolMapPanel", () => {
  beforeEach(() => useStore.setState({ symbolSet: null }));

  it("renders nothing without a symbol set", () => {
    render(<SymbolMapPanel />);
    expect(screen.queryByText("Symbol Map")).not.toBeInTheDocument();
  });

  it("labels the layer as DESIGNED UX, not discovered biology", () => {
    useStore.setState({ symbolSet: SYMBOLS as never });
    render(<SymbolMapPanel />);
    expect(screen.getByText("DESIGNED UX")).toBeInTheDocument();
    expect(screen.getByText(/not discovered biology/)).toBeInTheDocument();
  });

  it("renders both symbol classes with their glyphs", () => {
    useStore.setState({ symbolSet: SYMBOLS as never });
    render(<SymbolMapPanel />);
    expect(screen.getByText("Escape")).toBeInTheDocument();
    expect(screen.getByText("No-escape")).toBeInTheDocument();
    expect(screen.getByText("\u26a1")).toBeInTheDocument();
    expect(screen.getByText("\u00b7")).toBeInTheDocument();
  });
});

describe("CommunicationPanel", () => {
  beforeEach(() => useStore.setState({ communication: null }));

  it("shows empty state before a stimulus is selected", () => {
    render(<CommunicationPanel />);
    expect(screen.getByText(/Select a stimulus/)).toBeInTheDocument();
  });

  it("renders decoded symbol, label, and confidence", () => {
    useStore.setState({ communication: COMM as never });
    render(<CommunicationPanel />);
    expect(screen.getByText("\u26a1")).toBeInTheDocument();
    expect(screen.getByText("Escape")).toBeInTheDocument();
    expect(screen.getByText("54%")).toBeInTheDocument();
    expect(screen.getByText(/held-out channel R²/)).toBeInTheDocument();
  });

  it("labels the decode as model-inferred", () => {
    useStore.setState({ communication: COMM as never });
    render(<CommunicationPanel />);
    expect(screen.getByText("model-inferred")).toBeInTheDocument();
    expect(screen.getByText("Decoded class is model-inferred, not recorded truth.")).toBeInTheDocument();
  });
});

describe("DiscoveryConsole", () => {
  beforeEach(() => {
    useStore.setState({ symbolSet: null, testLog: null, currentStimulus: null });
  });

  it("renders nothing without symbol set", () => {
    render(<DiscoveryConsole />);
    expect(screen.queryByText("DISCOVERY")).not.toBeInTheDocument();
  });

  it("logs a test action and shows the session correlation table", () => {
    const logTestAction = vi.fn().mockResolvedValue(undefined);
    useStore.setState({
      symbolSet: SYMBOLS as never,
      testLog: TEST_LOG as never,
      currentStimulus: "loom",
      logTestAction,
    });
    render(<DiscoveryConsole />);
    fireEvent.click(screen.getByText("\u26a1 test"));
    expect(logTestAction).toHaveBeenCalledWith("\u26a1");
    expect(screen.getByText(/2 action/)).toBeInTheDocument();
    expect(screen.getByText("loom")).toBeInTheDocument();
    expect(screen.getByText(/No pre-scripted reveals/)).toBeInTheDocument();
  });
});