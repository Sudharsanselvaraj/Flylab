"""Loom-escape circuit queries — the Phase 0/1 flagship circuit.

Classical physiology describes visual loom detectors LC4 and LPLC2 feeding the
DNp01 "giant fiber" descending neuron, the command neuron for the fly's fast
escape jump. Per spec §7-0A we must NOT trust that diagram blindly — query the
*actual* path in MaleCNS v1.0, which may include different or additional
intermediate neurons.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from hawking_fly.connectome.client import ConnectomeClient

if TYPE_CHECKING:
    from pandas import DataFrame

LOOM_RECEPTOR_TYPES = ("LC4", "LPLC2")
DESCENDING_NEURON_TYPES = ("DNp01",)

#: The 65 cell types simulated by the pretrained flyvis optic-lobe model
#: (`flow/0000/000`). Used to select, among the *actual* MaleCNS-typed
#: upstream partners of a receptor, the subset that flyvis can drive.
FLYVIS_CELL_TYPES = frozenset(
    {
        "Am", "C2", "C3", "CT1(Lo1)", "CT1(M10)",
        "L1", "L2", "L3", "L4", "L5", "Lawf1", "Lawf2",
        "Mi1", "Mi10", "Mi11", "Mi12", "Mi13", "Mi14", "Mi15",
        "Mi2", "Mi3", "Mi4", "Mi9",
        "R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8",
        "T1", "T2", "T2a", "T3",
        "T4a", "T4b", "T4c", "T4d", "T5a", "T5b", "T5c", "T5d",
        "Tm1", "Tm16", "Tm2", "Tm20", "Tm28", "Tm3", "Tm30",
        "Tm4", "Tm5Y", "Tm5a", "Tm5b", "Tm5c", "Tm9",
        "TmY10", "TmY13", "TmY14", "TmY15", "TmY18", "TmY3",
        "TmY4", "TmY5a", "TmY9",
    }
)

#: Relay types discovered in the MaleCNS v1.0 relay scan (see
#: `data/connectome/loom_escape_relay_routes`). These are MaleCNS neuron types
#: that both receive LC4/LPLC2 input and project to DNp01.
RELAY_TYPES = (
    "SAD064",
    "PVLP122",
    "SAD073",
    "PVLP010",
    "PVLP151",
    "JO-B1_a",
    "AN12B001",
    "AN08B098",
    "SAD091",
    "IN00A062",
)


def _receptor_criteria():
    from neuprint import NeuronCriteria

    return NeuronCriteria(type=list(LOOM_RECEPTOR_TYPES))


def _dn_criteria():
    from neuprint import NeuronCriteria

    return NeuronCriteria(type=list(DESCENDING_NEURON_TYPES))


def _relay_criteria(relay_types: tuple[str, ...] = RELAY_TYPES):
    from neuprint import NeuronCriteria

    return NeuronCriteria(type=list(relay_types))


def query_loom_escape_circuit(
    client: ConnectomeClient,
    *,
    rois: tuple[str, ...] | None = None,
) -> dict[str, object]:
    """Trace the LC4/LPLC2 -> DNp01 path *in this dataset*.

    Returns a dict with the neuron tables, the direct adjacency edges, and any
    discovered intermediate neurons between the receptors and the giant fiber.
    Raises NoTokenError if no neuPrint token is configured.
    """
    result: dict[str, object] = {
        "dataset": client.config.dataset,
        "receptor_types": LOOM_RECEPTOR_TYPES,
        "descending_types": DESCENDING_NEURON_TYPES,
    }

    receptor_df, _ = client.fetch_neurons(_receptor_criteria())
    dn_df, _ = client.fetch_neurons(_dn_criteria())

    result["receptor_neurons"] = receptor_df
    result["dnp01_neurons"] = dn_df

    # Direct synapses receptors -> giant fiber
    sources_df, edges_df = client.fetch_adjacencies(_receptor_criteria(), _dn_criteria())
    result["direct_receptor_to_dnp01_neurons"] = sources_df
    result["direct_receptor_to_dnp01_edges"] = edges_df

    # Intermediate exploration: downstream of receptors, then who hits DNp01
    # upstream partners. (Heavy queries are gated behind explicit use so the
    # Phase 0A flyvis path never triggers them.)
    result["method"] = (
        "direct adjacency LC4/LPLC2 -> DNp01 pulled from live connectome; "
        "intermediate-path reconstruction pending explicit exploration"
    )
    return result


def build_loom_escape_subgraph(client: ConnectomeClient) -> dict[str, object]:
    """Produce a bounded, anatomy-aware subgraph for the propagation layer.

    Pulls the receptors + giant fiber + (optionally) their partners and
    returns edge data ready for `propagation.graph_build` to consume.
    Raises NoTokenError if no neuPrint token is configured.
    """
    data = query_loom_escape_circuit(client)

    # Collect edge rows from the direct adjacency edges table.
    edge_df: "pd.DataFrame" = data["direct_receptor_to_dnp01_edges"]  # type: ignore[assignment]
    edges = edge_df.rename(
        columns={
            "bodyId_pre": "pre",
            "bodyId_post": "post",
            "weight": "syn_count",
        }
    )
    data["edges"] = edges
    return data


def query_relay_layer(
    client: ConnectomeClient,
    *,
    relay_types: tuple[str, ...] = RELAY_TYPES,
) -> dict[str, object]:
    """Query the MaleCNS relay layer between LC4/LPLC2 and DNp01.

    Pulls the relay neuron table plus the two adjacency layers that bound it:
    ``receptor -> relay`` (LC4/LPLC2 onto relay neurons) and
    ``relay -> DNp01``. The finished query is a 3-layer MaleCNS-grounded
    graph: receptors -> relay population -> DNp01.

    The relay population is bounded to neurons that actually participate in
    the path (appear as a postsynaptic target of LC4/LPLC2 or a presynaptic
    source to DNp01), so dead-end type members with no edges to either side
    are excluded from the graph even when they share a cell type label.
    Raises NoTokenError if no neuPrint token is configured.
    """
    from neuprint import NeuronCriteria

    relay_criteria = _relay_criteria(relay_types)

    relay_neurons, _ = client.fetch_neurons(relay_criteria)
    # Guard against self/reciprocal rows among the descending pair leaking into
    # the relay table (DNp01 neurons also appear as type-matched connection
    # rows upstream of the pair).
    relay_neurons = relay_neurons[
        ~relay_neurons["type"].isin(DESCENDING_NEURON_TYPES)
    ].copy()

    # receptor -> relay adjacency
    _, receptor_to_relay_edges = client.fetch_adjacencies(
        _receptor_criteria(), relay_criteria
    )
    # relay -> DNp01 adjacency
    _, relay_to_dn_edges = client.fetch_adjacencies(relay_criteria, _dn_criteria())

    participating = set(receptor_to_relay_edges["bodyId_post"]) | set(
        relay_to_dn_edges["bodyId_pre"]
    )
    relay_neurons = relay_neurons[relay_neurons["bodyId"].isin(participating)].copy()

    return {
        "dataset": client.config.dataset,
        "receptor_types": LOOM_RECEPTOR_TYPES,
        "relay_types": relay_types,
        "descending_types": DESCENDING_NEURON_TYPES,
        "relay_neurons": relay_neurons,
        "receptor_to_relay_edges": receptor_to_relay_edges,
        "relay_to_dn_edges": relay_to_dn_edges,
    }


def build_malecns_grounded_graph(
    client: ConnectomeClient,
    *,
    relay_types: tuple[str, ...] = RELAY_TYPES,
) -> dict[str, object]:
    """Merge the 3-layer MaleCNS graph into one edge table.

    Concatenates the direct ``LC4/LPLC2 -> DNp01`` edges, the
    ``LC4/LPLC2 -> relay`` edges, and the ``relay -> DNp01`` edges into a
    single ``edges`` frame (``pre`` / ``post`` / ``syn_count``) with a neuron
    table and provenance about each layer. This is the primary bounded graph
    for the MaleCNS-grounded premotor experiment.
    """
    data = query_relay_layer(client, relay_types=relay_types)
    _, receptor_to_dn_edges = client.fetch_adjacencies(_receptor_criteria(), _dn_criteria())

    def _renamed(edges: "pd.DataFrame", layer: str) -> "pd.DataFrame":
        return edges.rename(
            columns={"bodyId_pre": "pre", "bodyId_post": "post", "weight": "syn_count"}
        ).assign(layer=layer)

    layers = [
        _renamed(receptor_to_dn_edges, "receptor_to_dn"),
        _renamed(data["receptor_to_relay_edges"], "receptor_to_relay"),
        _renamed(data["relay_to_dn_edges"], "relay_to_dn"),
    ]
    edges: "pd.DataFrame" = pd.concat(layers, ignore_index=True)
    data["edges"] = edges
    data["layer_counts"] = edges.groupby("layer").size().to_dict()
    data["layer_synapses"] = edges.groupby("layer")["syn_count"].sum().to_dict()
    data["method"] = (
        "3-layer bounded query: LC4/LPLC2 -> relay population -> DNp01, "
        "all adjacencies pulled live from MaleCNS v1.0"
    )
    return data


def query_receptor_upstream_evidence(
    client: ConnectomeClient,
    *,
    receptor_types: tuple[str, ...] = LOOM_RECEPTOR_TYPES,
) -> dict[str, object]:
    """Query the *actual* MaleCNS-typed inputs to each looming receptor.

    For every receptor type (LC4 / LPLC2) this pulls the full set of
    presynaptic partners from MaleCNS v1.0 plus their synapse counts, then
    aggregates per pre-synaptic *type*. The result is the evidence table used
    to ground the flyvis -> receptor mapping: it answers 'which flyvis cell
    classes actually synapse onto LC4/LPLC2, and with what weight?' instead of
    assuming a proxy.

    Receptor type itself (self-synapses) is retained in the *full* upstream
    table but flagged; coverage fractions computed by `mapping.build_*`
    exclude self-feedback so it measures input *from other neurons*.
    """
    from neuprint import NeuronCriteria

    per_type: dict[str, pd.DataFrame] = {}
    for rtype in receptor_types:
        crit = NeuronCriteria(type=rtype)
        _, _ = client.fetch_neurons(crit)
        pres, edges = client.fetch_adjacencies(None, crit)
        pre_neurons, _ = client.fetch_neurons(NeuronCriteria(bodyId=pres["bodyId"].tolist()))
        merged = edges.merge(
            pre_neurons[["bodyId", "type"]],
            left_on="bodyId_pre",
            right_on="bodyId",
            how="left",
            suffixes=("", "_pre"),
        )
        merged["is_self"] = merged["type"].eq(rtype)
        agg = (
            merged.groupby("type", dropna=False)
            .agg(n_pre_neurons=("bodyId_pre", "nunique"), total_syn=("weight", "sum"), is_self=("is_self", "any"))
            .reset_index()
            .rename(columns={"type": "pre_type"})
        )
        per_type[rtype] = agg
    return {
        "dataset": client.config.dataset,
        "receptor_types": receptor_types,
        "flyvis_cell_types": sorted(FLYVIS_CELL_TYPES),
        "upstream_by_type": per_type,
        "method": (
            "live MaleCNS v1.0 adjacency: all presynaptic partners of each "
            "receptor type, aggregated by pre-synaptic type with total synapse weight"
        ),
    }