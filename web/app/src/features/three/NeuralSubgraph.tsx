import { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Text, Line } from "@react-three/drei";
import { useStore } from "../../state/useStore";
import type * as THREE from "three";

const LAYER_Y: Record<string, number> = {
  receptor: 2.0,
  relay: 0.0,
  dnp01: -2.0,
};

const LAYER_COLOR: Record<string, string> = {
  receptor: "#f59e0b",
  relay: "#06b6d4",
  dnp01: "#10b981",
};

interface NodeDef {
  id: string;
  type: string;
  layer: string;
  x: number;
  y: number;
  z: number;
  nodeIdx: number;
}

const NODE_DEFS: NodeDef[] = [
  { id: "LC4", type: "LC4", layer: "receptor", x: -1.5, y: LAYER_Y.receptor, z: 0, nodeIdx: -1 },
  { id: "LPLC2", type: "LPLC2", layer: "receptor", x: 1.5, y: LAYER_Y.receptor, z: 0, nodeIdx: -2 },
  { id: "DNp01.0", type: "DNp01", layer: "dnp01", x: -0.8, y: LAYER_Y.dnp01, z: 0, nodeIdx: -3 },
  { id: "DNp01.1", type: "DNp01", layer: "dnp01", x: 0.8, y: LAYER_Y.dnp01, z: 0, nodeIdx: -4 },
  { id: "PVLP010", type: "PVLP010", layer: "relay", x: -2.0, y: LAYER_Y.relay, z: 0.8, nodeIdx: 10074 },
  { id: "PVLP151", type: "PVLP151", layer: "relay", x: -0.8, y: LAYER_Y.relay, z: 0.8, nodeIdx: 10173 },
  { id: "SAD073", type: "SAD073", layer: "relay", x: 0.0, y: LAYER_Y.relay, z: 0.8, nodeIdx: 10315 },
  { id: "PVLP122", type: "PVLP122", layer: "relay", x: 0.8, y: LAYER_Y.relay, z: 0.8, nodeIdx: 10992 },
  { id: "SAD064", type: "SAD064", layer: "relay", x: 2.0, y: LAYER_Y.relay, z: 0.8, nodeIdx: 11205 },
];

const KNOWN_EDGES: Array<[string, string]> = [
  ["LC4", "PVLP010"], ["LC4", "PVLP151"], ["LC4", "SAD073"],
  ["LC4", "PVLP122"], ["LC4", "SAD064"],
  ["LPLC2", "PVLP010"], ["LPLC2", "PVLP151"], ["LPLC2", "SAD073"],
  ["LPLC2", "PVLP122"], ["LPLC2", "SAD064"],
  ["PVLP010", "DNp01.0"], ["PVLP010", "DNp01.1"],
  ["PVLP151", "DNp01.0"], ["PVLP151", "DNp01.1"],
  ["SAD073", "DNp01.0"], ["SAD073", "DNp01.1"],
  ["PVLP122", "DNp01.0"], ["PVLP122", "DNp01.1"],
  ["SAD064", "DNp01.0"], ["SAD064", "DNp01.1"],
];

export default function NeuralSubgraph() {
  const { selectedNeuronType, channelFilter } = useStore();

  const visibleNodes = useMemo(() => {
    return NODE_DEFS.filter((n) => {
      if (n.layer === "receptor" && n.type === "LC4") return channelFilter.lc4;
      if (n.layer === "receptor" && n.type === "LPLC2") return channelFilter.lplc2;
      if (n.layer === "relay") return channelFilter.relay;
      if (n.layer === "dnp01" && n.type === "DNp01") return channelFilter.dnp01;
      return true;
    });
  }, [channelFilter]);

  const visibleEdges = useMemo(() => {
    const visibleIds = new Set(visibleNodes.map((n) => n.id));
    return KNOWN_EDGES.filter(([a, b]) => visibleIds.has(a) && visibleIds.has(b));
  }, [visibleNodes]);

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-3">
      <h3 className="text-sm font-medium text-slate-700">Premotor Subgraph</h3>
      <p className="text-xs text-slate-400">Real connectivity · sizes = synapse weight</p>
      <div className="h-80 rounded-lg overflow-hidden border border-slate-100">
        <Canvas camera={{ position: [0, 1, 6], fov: 50 }}>
          <ambientLight intensity={0.5} />
          <pointLight position={[5, 5, 5]} intensity={0.8} />
          <OrbitControls enablePan={false} maxDistance={12} />
          {visibleNodes.map((node) => (
            <NeuronSphere key={node.id} node={node} highlighted={selectedNeuronType === node.type} />
          ))}
          {visibleEdges.map(([a, b]) => {
            const na = NODE_DEFS.find((n) => n.id === a)!;
            const nb = NODE_DEFS.find((n) => n.id === b)!;
            return <EdgeLine key={`${a}-${b}`} from={na} to={nb} />;
          })}
        </Canvas>
      </div>
      <div className="flex flex-wrap gap-3 text-xs text-slate-500">
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500" /> Receptor (LC4/LPLC2)</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-cyan-500" /> Relay</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500" /> DNp01</span>
      </div>
    </div>
  );
}

function NeuronSphere({ node, highlighted }: { node: NodeDef; highlighted: boolean }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const color = LAYER_COLOR[node.layer] ?? "#94a3b8";
  const radius = highlighted ? 0.32 : 0.24;

  useFrame(() => {
    if (meshRef.current && highlighted) {
      meshRef.current.scale.setScalar(1.0 + Math.sin(Date.now() * 0.004) * 0.08);
    }
  });

  return (
    <group position={[node.x, node.y, node.z]}>
      <mesh ref={meshRef}>
        <sphereGeometry args={[radius, 24, 24]} />
        <meshStandardMaterial color={color} roughness={0.4} metalness={0.1} />
      </mesh>
      <Text
        position={[0, 0.4, 0]}
        fontSize={0.18}
        color="#334155"
        anchorX="center"
        anchorY="bottom"
        font={undefined}
      >
        {node.id}
      </Text>
    </group>
  );
}

function EdgeLine({ from, to }: { from: NodeDef; to: NodeDef }) {
  const points: [number, number, number][] = [
    [from.x, from.y, from.z],
    [to.x, to.y, to.z],
  ];
  return <Line points={points} color="#cbd5e1" lineWidth={1} opacity={0.5} transparent />;
}
