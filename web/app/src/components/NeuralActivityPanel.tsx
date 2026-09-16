import { useMemo } from "react";
import { useStore } from "../state/useStore";
import { layerColor } from "../utils/labels";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";

export function NeuralActivityPanel() {
  const { neuralData, channelFilter, replayFrame } = useStore();

  const filtered = useMemo(() => {
    if (!neuralData) return [];
    return neuralData.filter((ch) => {
      if (ch.key === "LC4") return channelFilter.lc4;
      if (ch.key === "LPLC2") return channelFilter.lc4;
      if (ch.key.startsWith("relay.")) return channelFilter.relay;
      if (ch.key.startsWith("DNp01")) return channelFilter.dnp01;
      return true;
    });
  }, [neuralData, channelFilter]);

  const chartData = useMemo(() => {
    if (filtered.length === 0) return [];
    const maxFrames = Math.max(...filtered.map((c) => c.values.length));
    const frames = Array.from({ length: maxFrames }, (_, i) => {
      const row: Record<string, number | string> = { t: i };
      for (const ch of filtered) {
        if (i < ch.values.length) row[ch.key] = ch.values[i];
      }
      return row;
    });
    return frames;
  }, [filtered]);

  if (filtered.length === 0) return <EmptyState />;

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-3">
      <h3 className="text-sm font-medium text-slate-700">Neural Activity</h3>
      <ChannelLegend channels={filtered} />
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
            <XAxis dataKey="t" tick={{ fontSize: 10, fill: "#94a3b8" }} tickLine={false} />
            <YAxis tick={{ fontSize: 10, fill: "#94a3b8" }} tickLine={false} width={50} />
            <Tooltip
              contentStyle={{ fontSize: 11, background: "#fff", border: "1px solid #e2e8f0", borderRadius: 6 }}
              labelFormatter={(v) => `frame ${v}`}
            />
            {replayFrame > 0 && <ReferenceLine x={replayFrame} stroke="#94a3b8" strokeDasharray="3 3" />}
            {filtered.map((ch) => (
              <Line
                key={ch.key}
                type="monotone"
                dataKey={ch.key}
                stroke={layerColor(ch.layer)}
                dot={false}
                strokeWidth={1.5}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="text-xs text-slate-400 italic">
        Shown: model-inferred pre-motor activity — not validated motor command
      </p>
    </div>
  );
}

function ChannelLegend({ channels }: { channels: Array<{ key: string; layer: string; label: string }> }) {
  return (
    <div className="flex flex-wrap gap-2 text-xs">
      {channels.map((ch) => (
        <span key={ch.key} className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full" style={{ background: layerColor(ch.layer) }} />
          <span className="text-slate-600">{ch.key}</span>
        </span>
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4">
      <h3 className="text-sm font-medium text-slate-700">Neural Activity</h3>
      <p className="text-sm text-slate-400 mt-2">Select a stimulus to view recorded traces</p>
    </div>
  );
}
