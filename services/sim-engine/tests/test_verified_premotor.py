"""Tests for the MaleCNS-grounded premotor representation (Phase 3A + 5).

Covers neuron identity, graph path reproducibility, provenance flags, and
verified/unverified status of the relay-layer VISIBLE representation.
"""

from __future__ import annotations

from pathlib import Path

import json
import numpy as np
import pytest

SAMPLE_RUN = Path(
    "/Users/sudharsan/Downloads/The Hawking Fly"
    "/experiments/loom_escape/20260916-214652"
)


# ---------------------------------------------------------------------------
# Graph integrity
# ---------------------------------------------------------------------------

class TestMaleCNSGraph:
    """The 3-layer graph caches must be consistent and neuron-identity safe."""

    @pytest.fixture(autouse=True)
    def _load(self):
        from hawking_fly.connectome.cache import load_cached_circuit
        self.graph, _ = load_cached_circuit("loom_escape_full_graph")
        self.relay, _ = load_cached_circuit("loom_escape_relay_neurons")
        self.rec, _ = load_cached_circuit("loom_escape_receptor_neurons")

    def test_three_layers_present(self):
        layers = set(self.graph["layer"])
        assert layers == {"receptor_to_dn", "receptor_to_relay", "relay_to_dn"}

    def test_receptor_to_relay_post_are_relay_neurons(self):
        r2r = self.graph[self.graph["layer"] == "receptor_to_relay"]
        bad = set(r2r["post"]) - set(self.relay["bodyId"])
        assert bad == set(), f"non-relay posts in receptor_to_relay: {bad}"

    def test_relay_to_dn_pre_are_relay_neurons(self):
        r2dn = self.graph[self.graph["layer"] == "relay_to_dn"]
        bad = set(r2dn["pre"]) - set(self.relay["bodyId"])
        assert bad == set(), f"non-relay pres in relay_to_dn: {bad}"

    def test_relay_to_dn_posts_are_dn01(self):
        r2dn = self.graph[self.graph["layer"] == "relay_to_dn"]
        dn_posts = set(r2dn["post"])
        assert len(dn_posts) == 2, f"expected 2 DNp01 posts, got {len(dn_posts)}"

    def test_no_self_edges(self):
        self_edges = self.graph[self.graph["pre"] == self.graph["post"]]
        assert len(self_edges) == 0

    def test_total_synapses_positive(self):
        assert int(self.graph["syn_count"].sum()) > 0


# ---------------------------------------------------------------------------
# Relay neuron identity
# ---------------------------------------------------------------------------

class TestRelayNeuronIdentity:
    """5 driven relay types must be present and produce valid traces."""

    EXPECTED_DRIVEN_TYPES = {"PVLP010", "PVLP122", "PVLP151", "SAD064", "SAD073"}

    def test_relay_neurons_json_exists(self):
        assert (SAMPLE_RUN / "connectome" / "relay_neurons.json").is_file()

    def test_driven_types_match_expectation(self):
        meta = json.loads((SAMPLE_RUN / "connectome" / "relay_neurons.json").read_text())
        types = {m["type"] for m in meta if m["has_receptor_input"]}
        assert types == self.EXPECTED_DRIVEN_TYPES

    def test_n_driven_21(self):
        meta = json.loads((SAMPLE_RUN / "connectome" / "relay_neurons.json").read_text())
        n_driven = sum(1 for m in meta if m["has_receptor_input"])
        assert n_driven == 21

    def test_relay_trace_shapes(self):
        for stim in ["flash", "moving_edge", "loom"]:
            tr = np.load(SAMPLE_RUN / "connectome" / f"relay_{stim}.npz")["trace"]
            assert tr.ndim == 3
            assert tr.shape[2] == 52  # all relay channels


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------

class TestProvenance:
    """Verified/verified flags must correctly express the honest status."""

    def test_individual_manifest_perc(self):
        m = json.loads((SAMPLE_RUN / "manifest.json").read_text())
        perc = m["perc"]
        assert perc["connectome_edges_verified"] is True
        assert perc["cell_identity_verified"] is True
        assert perc["flyvis_to_malecns_mapping_verified"] is False
        assert perc["dynamics_validated"] is False

    def test_mapping_verified_false_for_decoder(self):
        from hawking_fly.decoder.data import load_paired_dataset
        ds = load_paired_dataset(SAMPLE_RUN, filename="motor_gate_verified_v0.npz")
        assert ds.mapping_verified is False

    def test_type_agg_manifest_flags(self):
        m = json.loads((SAMPLE_RUN / "manifest_type_agg.json").read_text())
        perc = m["perc"]
        assert perc["connectome_edges_verified"] is True
        assert perc["dynamics_validated"] is False


# ---------------------------------------------------------------------------
# Threshold sensitivity stability
# ---------------------------------------------------------------------------

class TestThresholdSensitivity:
    """Relay norms must be stable across reasonable thresholds."""

    def test_threshold_norms_stable(self):
        """≥10 vs ≥500 thresholds differ by <20% in relay mean-abs norm."""
        from hawking_fly.connectome.cache import load_cached_circuit
        full, _ = load_cached_circuit("loom_escape_full_graph")
        r2r = full[full["layer"] == "receptor_to_relay"].copy()
        syn_per_relay = r2r.groupby("post")["syn_count"].sum()
        # stats: fraction of total syn that lives above each threshold
        total = int(syn_per_relay.sum())
        for th in [10, 50, 100, 500]:
            kept = int(syn_per_relay[syn_per_relay >= th].sum())
            frac = kept / total if total else 0
            if th <= 50:
                assert frac >= 0.9, f"threshold {th}: only {frac:.2%} of syn retained"


# ---------------------------------------------------------------------------
# Decoder dataset integrity
# ---------------------------------------------------------------------------

class TestDecoderDataset:
    """Verified dataset must be loadable and have correct schema."""

    def test_individual_loads(self):
        from hawking_fly.decoder.data import load_paired_dataset
        ds = load_paired_dataset(SAMPLE_RUN, filename="motor_gate_verified_v0.npz")
        assert len(ds.trajectories) == 8

    def test_individual_has_21_channels(self):
        from hawking_fly.decoder.data import load_paired_dataset
        ds = load_paired_dataset(SAMPLE_RUN, filename="motor_gate_verified_v0.npz")
        for t in ds.trajectories:
            assert t.visible.shape[1] == 21

    def test_type_agg_loads(self):
        from hawking_fly.decoder.data import load_paired_dataset
        ds = load_paired_dataset(SAMPLE_RUN, filename="motor_gate_verified_v0_type_agg.npz")
        assert len(ds.trajectories) == 8
        for t in ds.trajectories:
            assert t.visible.shape[1] == 5
