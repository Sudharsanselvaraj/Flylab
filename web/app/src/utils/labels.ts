export function channelLabel(key: string): string {
  if (key === "LC4") return "LC4 (receptor)";
  if (key === "LPLC2") return "LPLC2 (receptor)";
  if (key.startsWith("relay.")) return key.replace("relay.", "Relay ");
  if (key.startsWith("DNp01")) return key;
  return key;
}

export function layerColor(layer: string): string {
  if (layer === "receptor") return "#f59e0b";
  if (layer === "relay") return "#06b6d4";
  if (layer === "dnp01") return "#10b981";
  return "#94a3b8";
}

export function layerBadge(layer: string): string {
  if (layer === "receptor") return "bg-amber-100 text-amber-800";
  if (layer === "relay") return "bg-cyan-100 text-cyan-800";
  if (layer === "dnp01") return "bg-emerald-100 text-emerald-800";
  return "bg-gray-100 text-gray-800";
}

export function statusColor(status: string): string {
  if (status === "MEASURED") return "bg-emerald-100 text-emerald-800";
  if (status === "SYNTHESIZED") return "bg-amber-100 text-amber-800";
  if (status === "PRESENTATION") return "bg-slate-100 text-slate-800";
  return "bg-red-50 text-red-800";
}
