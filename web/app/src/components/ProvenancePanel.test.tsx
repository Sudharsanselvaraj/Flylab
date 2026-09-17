import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { useStore } from "../state/useStore";
import { ProvenancePanel } from "../components/ProvenancePanel";

const PROVENANCE = {
  run_id: "20260916-223510",
  dataset: "MaleCNS v1.0",
  mapping: "connectome_grounded",
  topology: "loom-escape relay graph",
  flags: {
    dynamics_validated: false,
    connectome_edges_verified: true,
    topology_validated: true,
  },
  layers: [
    { label: "MaleCNS connectivity", layer: "MaleCNS connectivity", status: "MEASURED" },
    { label: "FlyVis visual model", layer: "FlyVis visual model", status: "MEASURED" },
    { label: "Wheelchair / avatar", layer: "Wheelchair / avatar", status: "PRESENTATION" },
  ],
};

const PROVENANCE_OBJECT_MAPPING = {
  ...PROVENANCE,
  mapping: {
    mode: "connectome_grounded",
    summary: "synapse-weighted upstream evidence",
    note: "mapper note",
  },
};

describe("ProvenancePanel", () => {
  it("renders honest flags — dynamics not validated, presentation layer marked", () => {
    useStore.setState({ provenance: PROVENANCE as never });
    render(<ProvenancePanel />);
    expect(screen.getByText(/connectome_edges_verified: yes/)).toBeInTheDocument();
    expect(screen.getByText(/dynamics_validated: no/)).toBeInTheDocument();
    expect(screen.getByText("PRESENTATION")).toBeInTheDocument();
    expect(screen.getByText(/Dynamics NOT validated/)).toBeInTheDocument();
  });

  it("handles the backend mapping object shape without crashing", () => {
    useStore.setState({ provenance: PROVENANCE_OBJECT_MAPPING as never });
    render(<ProvenancePanel />);
    expect(screen.getByText((t) => t.includes("connectome_grounded"))).toBeInTheDocument();
  });

  it("shows an empty state when no experiment is loaded", () => {
    useStore.setState({ provenance: null });
    render(<ProvenancePanel />);
    expect(screen.getByText("Select a run to view provenance")).toBeInTheDocument();
  });

  it("exposes the MaleCNS mapping-verified flag when the backend sends it", () => {
    useStore.setState({
      provenance: {
        ...PROVENANCE,
        flags: { ...PROVENANCE.flags, flyvis_to_malecns_mapping_verified: true },
      } as never,
      decoder: null,
    });
    render(<ProvenancePanel />);
    expect(screen.getByText(/flyvis→malecns mapping_verified: yes/)).toBeInTheDocument();
  });

  it("tags the dataset vintage as grounded premotor when the decoder mapping is verified", () => {
    useStore.setState({
      provenance: PROVENANCE as never,
      decoder: { mapping_verified: true } as never,
      currentRunId: PROVENANCE.run_id,
      currentStimulus: "loom",
    });
    render(<ProvenancePanel />);
    expect(screen.getByText("grounded premotor")).toBeInTheDocument();
  });
});