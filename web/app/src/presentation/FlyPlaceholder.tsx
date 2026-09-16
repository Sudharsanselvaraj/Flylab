import { useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { useStore } from "../state/useStore";
import { makeTextSprite } from "../features/three/textSprite";
import type * as THREE from "three";

export default function FlyPlaceholder() {
  const { currentStimulus } = useStore();

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-3">
      <h3 className="text-sm font-medium text-slate-700">Fly + Wheelchair Presentation</h3>
      <p className="text-xs text-slate-400">Labeled placeholder — fly/gym integration deferred to Phase 1</p>
      <div className="h-64 rounded-lg overflow-hidden border border-slate-100">
        <Canvas camera={{ position: [0, 2, 5], fov: 45 }}>
          <ambientLight intensity={0.6} />
          <pointLight position={[3, 4, 3]} intensity={0.8} />
          <OrbitControls enablePan={false} maxDistance={10} />
          <FlyModel />
          <WheelchairModel />
          <Ground />
          <StimulusLabel stimulus={currentStimulus} />
        </Canvas>
      </div>
      <div className="flex justify-between text-xs text-slate-400">
        <span>Not validated dynamics</span>
        <span>Presentation only — no motor gating</span>
      </div>
    </div>
  );
}

function FlyModel() {
  const groupRef = useRef<THREE.Group>(null);
  useFrame(() => {
    if (groupRef.current) {
      groupRef.current.rotation.y += 0.003;
    }
  });
  return (
    <group ref={groupRef} position={[0, 0.6, 0]}>
      <mesh>
        <capsuleGeometry args={[0.15, 0.4, 8, 16]} />
        <meshStandardMaterial color="#1e293b" roughness={0.3} />
      </mesh>
      <mesh position={[0, 0.45, 0]}>
        <sphereGeometry args={[0.1, 16, 16]} />
        <meshStandardMaterial color="#1e293b" roughness={0.3} />
      </mesh>
      <Wing position={[-0.2, 0.3, 0.1]} side="left" />
      <Wing position={[0.2, 0.3, 0.1]} side="right" />
    </group>
  );
}

function Wing({ position, side }: { position: [number, number, number]; side: string }) {
  const ref = useRef<THREE.Mesh>(null);
  useFrame(() => {
    if (ref.current) {
      ref.current.rotation.z = side === "left"
        ? 0.2 + Math.sin(Date.now() * 0.02) * 0.3
        : -0.2 - Math.sin(Date.now() * 0.02) * 0.3;
    }
  });
  return (
    <mesh ref={ref} position={position} rotation={[0, 0, side === "left" ? 0.2 : -0.2]}>
      <planeGeometry args={[0.25, 0.12]} />
      <meshStandardMaterial color="#94a3b8" transparent opacity={0.5} side={2} />
    </mesh>
  );
}

function WheelchairModel() {
  const label = useMemo(() => makeTextSprite("PRESENTATION ONLY"), []);
  return (
    <group position={[0, -0.1, 0]}>
      <mesh position={[0, 0, 0]}>
        <boxGeometry args={[0.6, 0.15, 0.4]} />
        <meshStandardMaterial color="#475569" roughness={0.5} />
      </mesh>
      <mesh position={[-0.2, -0.12, 0.15]}>
        <cylinderGeometry args={[0.08, 0.08, 0.04, 16]} />
        <meshStandardMaterial color="#1e293b" />
      </mesh>
      <mesh position={[0.2, -0.12, 0.15]}>
        <cylinderGeometry args={[0.08, 0.08, 0.04, 16]} />
        <meshStandardMaterial color="#1e293b" />
      </mesh>
      <primitive object={label} position={[0, 0.25, 0]} />
    </group>
  );
}

function Ground() {
  return (
    <mesh position={[0, -0.25, 0]} rotation={[-Math.PI / 2, 0, 0]}>
      <planeGeometry args={[6, 6]} />
      <meshStandardMaterial color="#f1f5f9" opacity={0.4} transparent />
    </mesh>
  );
}

function StimulusLabel({ stimulus }: { stimulus: string | null }) {
  const sprite = useMemo(
    () => (stimulus ? makeTextSprite(`${stimulus.replace("_", " ")} · not validated`) : null),
    [stimulus],
  );
  if (!sprite) return null;
  return <primitive object={sprite} position={[0, 1.2, 0]} />;
}
