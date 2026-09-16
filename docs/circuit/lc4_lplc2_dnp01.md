# LC4/LPLC2 → DNp01 loom-escape subgraph (MaleCNS v1.0)

**Status:** bounded, anatomy-aware discovery complete. Direct route **verified**.

## Summary

| Route | Synapses | Share of DNp01 input (upstream partners ≥ 50 syn) |
|-------|----------|---------------------------------------------------|
| LC4/LPLC2 → DNp01 (direct) | **11,224** | **~29%** |
| All other upstream partners (≥ 50 syn) | 27,258 | ~71% |

**Verdict:** The classical diagram (LC4 + LPLC2 directly synapse on the DNp01 giant fiber) **holds in MaleCNS v1.0**. No single relay hop exceeds the direct receptor contribution among the top-12 upstream types.

## Key upstream partners (top 8)

| Cell type | Total synapses | Role |
|-----------|---------------|------|
| LC4 | 6,362 | direct looming receptor |
| LPLC2 | 4,862 | direct looming receptor |
| DNp70 | 1,416 | relay candidate |
| PVLP122 | 1,216 | relay candidate |
| SAD064 | 1,215 | relay candidate |
| SAD073 | 1,177 | relay candidate |
| PVLP010 | 711 | relay candidate |
| PVLP123 | 620 | relay candidate |

## Relay scan (1-hop, top-12 upstream types)

The relay scan checks whether any DNp01 upstream type receives strong input from LC4/LPLC2 (i.e. LC4/LPLC2 → relay → DNp01). The relay routes add to DNp01 input but do **not** replace the direct receptor contribution.

## Caveats and mapping status (spec §8)

- **flyvis ↔ MaleCNS mapping is a documented proxy, not a verified cell-type correspondence.** flyvis's 65 cell types do not include LC4 or LPLC2. The integration run uses LC4↔Tm/TmY proxy and LPLC2↔T4/T5 proxy (see `connectome/mapping.py` for the full auditable record).
- **Bilateral symmetry assumption:** flyvis simulates a single optic lobe; the same drive is applied bilaterally to both MaleCNS left/right receptor bodyIds.
- **Propagation model is simplified dynamics** (rate model, not biophysically validated).
