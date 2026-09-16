import { useStore } from "../state/useStore";

export function ChannelFilterPanel() {
  const { channelFilter, toggleChannelFilter } = useStore();
  const filters: Array<{ key: keyof typeof channelFilter; label: string; color: string }> = [
    { key: "lc4", label: "LC4", color: "bg-amber-500" },
    { key: "lplc2", label: "LPLC2", color: "bg-cyan-500" },
    { key: "relay", label: "Relay", color: "bg-teal-500" },
    { key: "dnp01", label: "DNp01", color: "bg-emerald-500" },
  ];

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-3">
      <h3 className="text-sm font-medium text-slate-700">Channel Filter</h3>
      <div className="flex flex-wrap gap-2">
        {filters.map(({ key, label, color }) => (
          <button
            key={key}
            onClick={() => toggleChannelFilter(key)}
            className={`text-sm rounded-lg px-3 py-1.5 border transition-colors flex items-center gap-2 ${
              channelFilter[key]
                ? "bg-white text-slate-800 border-slate-300"
                : "bg-slate-50 text-slate-400 border-slate-200"
            }`}
          >
            <span className={`w-2 h-2 rounded-full ${color} ${channelFilter[key] ? "opacity-100" : "opacity-30"}`} />
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}
