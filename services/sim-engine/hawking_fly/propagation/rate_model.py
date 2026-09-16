"""Propagation layer — custom neural dynamics over the real connectome graph.

EXPLICIT LABEL (spec §3/§8): the connectivity graph below is *real* (MaleCNS /
flyvis connectome derived), but the dynamics are a simplified rate model
(leaky-integrator + saturating nonlinearity). This is "connectivity-informed,
not dynamics-validated" — never present it as validated biophysics.

Phase 0A only needs a *plausible* propagation to carry flyvis optic-lobe
activity forward; the go/no-go decoder work happens in Phase 0C.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import numpy.typing as npt
from scipy import sparse

Nonlinearity = Callable[[npt.NDArray[np.float64]], npt.NDArray[np.float64]]


def relu(x: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    return np.clip(x, 0.0, None)


def saturating(x: npt.NDArray[np.float64], steepness: float = 1.0) -> npt.NDArray[np.float64]:
    """Monotone saturating nonlinearity bounded in [0, 1]."""
    return 1.0 / (1.0 + np.exp(-steepness * x))


@dataclass
class RateModel:
    """Leaky-integrator rate model over an NxN sparse weight matrix.

    Dynamics (forward Euler):

        tau * dr/dt = -r + f(W @ r + b + input(t))

    where W rows are incoming synapses (row-normalized by option). The model
    is pure NumPy/SciPy on purpose: it is a *simplified* stand-in for
    biophysical dynamics and stays trivially cheap at 1k-5k nodes.
    """

    weight: sparse.csr_matrix
    tau: npt.NDArray[np.float64] | float = 1.0
    bias: npt.NDArray[np.float64] | None = None
    nonlinearity: Nonlinearity = saturating
    dt: float = 0.01
    node_ids: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._w = self.weight.tocsr().astype(np.float64)
        self._n = self._w.shape[0]
        self._tau = (
            np.full(self._n, self.tau, dtype=np.float64)
            if np.isscalar(self.tau)
            else np.asarray(self.tau, dtype=np.float64)
        )
        self._b = (
            np.zeros(self._n, dtype=np.float64)
            if self.bias is None
            else np.asarray(self.bias, dtype=np.float64)
        )

    @classmethod
    def from_edge_list(
        cls,
        pre: npt.ArrayLike,
        post: npt.ArrayLike,
        weights: npt.ArrayLike,
        n_nodes: int,
        node_ids: list[int] | None = None,
        normalize: bool = True,
        **kwargs: object,
    ) -> "RateModel":
        """Build from edge lists (pre, post, weight), optionally row-normalizing.

        The weight matrix is oriented ``weight[post, pre]`` so that ``weight @ x``
        has one row per *post*-synaptic node — this is what ``step``/``simulate``
        expect (see class docstring).
        """
        pre = np.asarray(pre)
        post = np.asarray(post)
        w = np.asarray(weights, dtype=np.float64)

        # Internal indices: remap bodyIds to 0..n-1 in arbitrary-but-stable order.
        ids = list(node_ids) if node_ids else sorted(set(pre) | set(post))
        index = {n: i for i, n in enumerate(ids)}
        if len(ids) != n_nodes:
            raise ValueError(
                f"n_nodes={n_nodes} but node_ids resolves to {len(ids)} nodes"
            )
        rows = np.array([index[int(p)] for p in post])  # post -> row
        cols = np.array([index[int(p)] for p in pre])  # pre -> column
        mat = sparse.coo_matrix((w, (rows, cols)), shape=(n_nodes, n_nodes))
        if normalize:
            # Incoming normalization: divide each post row by its total incoming.
            in_degree = np.asarray(mat.sum(axis=1)).ravel()
            in_degree[in_degree == 0] = 1.0
            mat = sparse.diags(1.0 / in_degree) @ mat
        return cls(mat.tocsr(), node_ids=ids, **kwargs)

    def _input(self, drive: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        drive = np.asarray(drive, dtype=np.float64)
        return self._w @ drive + self._b

    def step(
        self,
        r: npt.NDArray[np.float64],
        external_input: npt.NDArray[np.float64],
    ) -> npt.NDArray[np.float64]:
        """One Euler step: r += dt/tau * (-r + f(W r + b + u))."""
        r = np.asarray(r, dtype=np.float64)
        drive = self._input(external_input)
        return r + (self.dt / self._tau) * (-r + self.nonlinearity(drive))

    def simulate(
        self,
        r0: npt.NDArray[np.float64],
        inputs: npt.NDArray[np.float64],
    ) -> npt.NDArray[np.float64]:
        """Run the dynamics for T steps; inputs shape (T, n) or (n,) broadcast.

        Returns activity of shape (T, n).
        """
        r0 = np.asarray(r0, dtype=np.float64)
        inputs = np.asarray(inputs, dtype=np.float64)
        T = inputs.shape[0]
        trace = np.empty((T, self._n), dtype=np.float64)
        r = r0.copy()
        for t in range(T):
            r = self.step(r, inputs[t])
            trace[t] = r
        return trace