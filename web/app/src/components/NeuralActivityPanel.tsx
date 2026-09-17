import { useMemo } from "react";
import { useStore } from "../state/useStore";
import { layerColor } from "../utils/labels";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import type { NeuralChannel } from "../types/experiment";

const RELAY_TYPE_COLORS = ["#0ea5e9", "#0284c7", "#0891b2", "#068da9", "#0e7490"];

export function NeuralActivityPanel() {
  const { neuralData, neuralMode, setNeuralMode, channelFilter, toggleChannelFilter, replayFrame } = useStore();

  const visible = useMemo(
    () => (neuralData ?? []).filter((ch) => (ch.role ?? "visible") === "visible"),
    [neuralData],
  );
  const groundTruth = useMemo(
    () => (neuralData ?? []).filter((ch) => ch.role === "ground_truth" && channelFilter.dnp01),
    [neuralData, channelFilter],
  );

  const visibleFiltered = useMemo(() => {
    return visible.filter((ch) => {
      if (ch.key === "LC4" || ch.key === "LPLC2") return channelFilter.lc4;
      if (ch.key.startsWith("relay.")) return channelFilter.relay;
      return true;
    });
  }, [visible, channelFilter]);

  if (!neuralData || neuralData.length === 0) return <EmptyState />;

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h3 className="text-sm font-medium text-slate-700">Neural Activity</h3>
          <p className="text-xs text-slate-400">
            recorded traces — replay only, no synthesized data
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex rounded-lg border border-slate-200 overflow-hidden text-xs">
            {([
              ["lc4", "receptors"],
              ["relay", "relays"],
              ["dnp01", "truth"],
            ] as const).map(([key, label]) => (
              <button
                key={key}
                onClick={() => toggleChannelFilter(key)}
                className={`px-2.5 py-1.5 ${channelFilter[key] ? "bg-slate-100 text-slate-700" : "bg-white text-slate-400 line-through"}`}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="flex rounded-lg border border-slate-200 overflow-hidden text-xs">
            <button
              onClick={() => setNeuralMode("type_agg")}
              className={`px-3 py-1.5 ${neuralMode === "type_agg" ? "bg-slate-900 text-white" : "bg-white text-slate-600 hover:bg-slate-50"}`}
            >
              type-agg
            </button>
            <button
              onClick={() => setNeuralMode("per_neuron")}
              className={`px-3 py-1.5 ${neuralMode === "per_neuron" ? "bg-slate-900 text-white" : "bg-white text-slate-600 hover:bg-slate-50"}`}
            >
              per-neuron
            </button>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <section aria-label="Visible upstream representation">
          <SectionHeader
            tag="VISIBLE"
            title="Upstream representation"
            subtitle={
              neuralMode === "per_neuron"
                ? "each driven MaleCNS relay neuron recorded"
                : "relay shown as per-type means"
            }
            color="text-cyan-700 border-cyan-200 bg-cyan-50"
          />
          {visibleFiltered.length === 0 ? (
            <p className="text-xs text-slate-400 py-2">No visible channels enabled.</p>
          ) : (
            <>
              <Legend groups={groupVisibleChannels(visibleFiltered)} />
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={toChartData(visibleFiltered)}
                    margin={{ top: 5, right: 10, bottom: 5, left: 0 }}
                  >
                    <XAxis dataKey="t" tick={{ fontSize: 10, fill: "#94a3b8" }} tickLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: "#94a3b8" }} tickLine={false} width={50} />
                    <Tooltip
                      contentStyle={{ fontSize: 11, background: "#fff", border: "1px solid #e2e8f0", borderRadius: 6 }}
                      labelFormatter={(v) => `frame ${v}`}
                    />
                    {replayFrame > 0 && <ReferenceLine x={replayFrame} stroke="#94a3b8" strokeDasharray="3 3" />}
                    {visibleFiltered.map((ch) => (
                      <Line
                        key={ch.key}
                        type="monotone"
                        dataKey={ch.key}
                        stroke={relayStroke(neuralMode, ch)}
                        dot={false}
                        strokeWidth={1.2}
                        isAnimationActive={false}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </>
          )}
        </section>

        <section aria-label="Ground truth withheld behind the motor gate">
          <SectionHeader
            tag="GROUND TRUTH"
            title="DNp01 — withheld behind the gate"
            subtitle="recorded but not visible to the decoder; shown here for reference"
            color="text-emerald-700 border-emerald-200 bg-emerald-50"
          />
          {groundTruth.length === 0 ? (
            <p className="text-xs text-slate-400 py-2">No ground-truth trace recorded for this stimulus.</p>
          ) : (
            <>
              <Legend groups={[{ label: "DNp01 (withheld)", channels: groundTruth }]} />
              <div className="h-44">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={toChartData(groundTruth)} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
                    <XAxis dataKey="t" tick={{ fontSize: 10, fill: "#94a3b8" }} tickLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: "#94a3b8" }} tickLine={false} width={50} />
                    <Tooltip
                      contentStyle={{ fontSize: 11, background: "#fff", border: "1px solid #e2e8f0", borderRadius: 6 }}
                      labelFormatter={(v) => `frame ${v}`}
                    />
                    {replayFrame > 0 && <ReferenceLine x={replayFrame} stroke="#94a3b8" strokeDasharray="3 3" />}
                    {groundTruth.map((ch) => (
                      <Line
                        key={ch.key}
                        type="monotone"
                        dataKey={ch.key}
                        stroke={layerColor(ch.layer)}
                        dot={false}
                        strokeWidth={2}
                        isAnimationActive={false}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </>
          )}
        </section>
      </div>

      <p className="text-xs text-slate-400 italic">
        Shown: recorded pre-motor activity — not validated motor command. Visible ≠ direct motor output.
      </p>
    </div>
  );
}

function relayStroke(mode: "type_agg" | "per_neuron", ch: NeuralChannel): string {
  if (!ch.key.startsWith("relay.")) return layerColor(ch.layer);
  if (mode === "per_neuron") {
    const type = (ch.key.split(".")[1] ?? "").toUpperCase();
    const idx = ["PVLP010", "PVLP151", "SAD064", "SAD073", "PVLP122"].indexOf(type);
    return idx >= 0 ? RELAY_TYPE_COLORS[idx % RELAY_TYPE_COLORS.length] : "#0ea5e9";
  }
  return layerColor(ch.layer);
}

function groupVisibleChannels(channels: NeuralChannel[]): Array<{ label: string; channels: NeuralChannel[] }> {
  const groups: Array<{ label: string; channels: NeuralChannel[] }> = [];
  const receptors = channels.filter((c) => c.layer === "receptor");
  const relays = channels.filter((c) => c.layer === "relay");
  if (receptors.length) groups.push({ label: "LC4 / LPLC2 (receptor drive)", channels: receptors });
  if (relays.length) {
    const byType = new Map<string, NeuralChannel[]>();
    for (const r of relays) {
      const t = r.group ?? r.key.replace("relay.", "");
      byType.set(t, [...(byType.get(t) ?? []), r]);
    }
    for (const [t, chs] of byType) groups.push({ label: `${t}`, channels: chs });
  }
  return groups;
}

function Legend({ groups }: { groups: Array<{ label: string; channels: NeuralChannel[] }> }) {
  return (
    <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-500 py-1">
      {groups.map((g) => (
        <span key={g.label} className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full" style={{ background: g.channels[0] ? (g.channels[0].layer === "relay" && !g.channels[0].group ? "#06b6d4" : layerColor(g.channels[0].layer)) : "#94a3b8" }} />
          <span>
            {g.label}
            {g.channels.length > 1 ? ` (${g.channels.length})` : ""}
          </span>
        </span>
      ))}
    </div>
  );
}

function SectionHeader({ tag, title, subtitle, color }: { tag: string; title: string; subtitle: string; color: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className={`rounded border px-1.5 py-0.5 text-[10px] font-semibold tracking-wide ${color}`}>{tag}</span>
      <div>
        <p className="text-xs font-medium text-slate-700">{title}</p>
        <p className="text-[11px] text-slate-400">{subtitle}</p>
      </div>
    </div>
  );
}

function toChartData(channels: NeuralChannel[]) {
  const maxFrames = Math.max(...channels.map((c) => c.values.length));
  return Array.from({ length: maxFrames }, (_, i) => {
    const row: Record<string, number | string> = { t: i };
    for (const ch of channels) if (i < ch.values.length) row[ch.key] = ch.values[i];
    return row;
  });
}

function EmptyState() {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4">
      <h3 className="text-sm font-medium text-slate-700">Neural Activity</h3>
      <p className="text-sm text-slate-400 mt-2">Select a stimulus to view recorded traces</p>
    </div>
  );
}