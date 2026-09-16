import { useStore } from "../state/useStore";
import type { NeuronType, Dnp01Branch } from "../types/experiment";

const TYPES: Array<{ id: NeuronType; label: string; disabled?: boolean }> = [
  { id: "LC4", label: "LC4" },
  { id: "LPLC2", label: "LPLC2" },
  { id: "relay", label: "Relay" },
  { id: "DNp01", label: "DNp01" },
];

export function SelectableNeuronPanel() {
  const { selectedNeuronType, setSelectedNeuronType, selectedBranch, setSelectedBranch, runs, currentRunId } = useStore();
  const run = runs.find((r) => r.run_id === currentRunId);
  const groundingMode = run?.mapping ?? "unknown";

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-3">
      <h3 className="text-sm font-medium text-slate-700">Neuron Selection</h3>
      <div className="flex flex-wrap gap-2">
        {TYPES.map(({ id, label }) => (
          <button
            key={label}
            onClick={() => setSelectedNeuronType(selectedNeuronType === id ? null : id)}
            className={`text-sm rounded-lg px-3 py-1.5 border transition-colors ${
              selectedNeuronType === id
                ? "bg-slate-900 text-white border-slate-900"
                : "bg-white text-slate-700 border-slate-200 hover:border-slate-400"
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      {selectedNeuronType === "DNp01" && (
        <div className="flex gap-2 ml-4">
          {(["0", "1"] as Dnp01Branch[]).map((b) => (
            <button
              key={b}
              onClick={() => setSelectedBranch(selectedBranch === b ? null : b)}
              className={`text-xs rounded px-2 py-1 border transition-colors ${
                selectedBranch === b
                  ? "bg-emerald-700 text-white border-emerald-700"
                  : "bg-white text-slate-600 border-slate-200"
              }`}
            >
              branch {b}
            </button>
          ))}
        </div>
      )}
      <p className="text-xs text-slate-400">
        Grounding: <span className="font-medium text-slate-600">{groundingMode}</span>
      </p>
    </div>
  );
}
