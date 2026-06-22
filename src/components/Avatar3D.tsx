import { Canvas, useFrame } from "@react-three/fiber";
import { Suspense, useRef, useState, useEffect } from "react";
import * as THREE from "three";

function useGlobalPointer(canvasRef: React.RefObject<HTMLDivElement | null>) {
  const target = useRef({ x: 0, y: 0 });
  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      const el = canvasRef.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      const cx = r.left + r.width / 2;
      const cy = r.top + r.height / 2;
      const nx = (e.clientX - cx) / (window.innerWidth / 2);
      const ny = (e.clientY - cy) / (window.innerHeight / 2);
      target.current.x = Math.max(-1.2, Math.min(1.2, nx));
      target.current.y = Math.max(-1.2, Math.min(1.2, ny));
    };
    window.addEventListener("mousemove", onMove);
    return () => window.removeEventListener("mousemove", onMove);
  }, [canvasRef]);
  return target;
}

function Head({ pointer }: { pointer: React.MutableRefObject<{ x: number; y: number }> }) {
  const group = useRef<THREE.Group>(null);
  const leftPupil = useRef<THREE.Mesh>(null);
  const rightPupil = useRef<THREE.Mesh>(null);
  const antenna = useRef<THREE.Mesh>(null);
  const antennaGlow = useRef<THREE.Mesh>(null);
  const smooth = useRef({ x: 0, y: 0 });

  useFrame((state, _dt) => {
    smooth.current.x += (pointer.current.x - smooth.current.x) * 0.12;
    smooth.current.y += (pointer.current.y - smooth.current.y) * 0.12;
    const tx = smooth.current.x;
    const ty = smooth.current.y;

    if (group.current) {
      group.current.rotation.y = tx * 0.7;
      group.current.rotation.x = ty * 0.45;
      group.current.position.y = Math.sin(state.clock.elapsedTime * 1.6) * 0.05 - 0.05;
    }

    const eyeMax = 0.045;
    [leftPupil, rightPupil].forEach((ref, i) => {
      if (!ref.current) return;
      const baseX = i === 0 ? -0.26 : 0.26;
      ref.current.position.x = baseX + tx * eyeMax;
      ref.current.position.y = 0.14 + -ty * eyeMax;
    });

    if (antenna.current) {
      antenna.current.rotation.z = Math.sin(state.clock.elapsedTime * 2.5) * 0.15;
    }
    if (antennaGlow.current) {
      const pulse = 0.7 + Math.sin(state.clock.elapsedTime * 3) * 0.3;
      (antennaGlow.current.material as THREE.MeshStandardMaterial).emissiveIntensity = pulse;
    }
  });

  const metal = "#d1d5db";
  const darkMetal = "#6b7280";
  const eyeGlow = "#67e8f9";
  const accent = "#f59e0b";

  return (
    <group ref={group} position={[0, -0.05, 0]}>
      {/* Main round head */}
      <mesh>
        <sphereGeometry args={[1.0, 64, 64]} />
        <meshStandardMaterial color={metal} metalness={0.7} roughness={0.25} />
      </mesh>

      {/* Face plate — slightly flattened front disc */}
      <mesh position={[0, 0, 0.88]} rotation={[0, 0, 0]}>
        <cylinderGeometry args={[0.82, 0.82, 0.08, 64]} />
        <meshStandardMaterial color="#e5e7eb" metalness={0.5} roughness={0.3} />
      </mesh>

      {/* Antenna stem */}
      <mesh position={[0, 1.05, 0]}>
        <cylinderGeometry args={[0.04, 0.04, 0.35, 12]} />
        <meshStandardMaterial color={darkMetal} metalness={0.8} roughness={0.2} />
      </mesh>

      {/* Antenna ball glow */}
      <mesh ref={antennaGlow} position={[0, 1.28, 0]}>
        <sphereGeometry args={[0.1, 24, 24]} />
        <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={1} />
      </mesh>

      {/* Side ear bolts */}
      <mesh position={[-1.02, 0.1, 0]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.16, 0.16, 0.12, 24]} />
        <meshStandardMaterial color={darkMetal} metalness={0.8} roughness={0.2} />
      </mesh>
      <mesh position={[1.02, 0.1, 0]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.16, 0.16, 0.12, 24]} />
        <meshStandardMaterial color={darkMetal} metalness={0.8} roughness={0.2} />
      </mesh>

      {/* Eye housings (dark rings) */}
      <mesh position={[-0.26, 0.14, 0.96]}>
        <torusGeometry args={[0.18, 0.04, 16, 48]} />
        <meshStandardMaterial color={darkMetal} metalness={0.6} roughness={0.3} />
      </mesh>
      <mesh position={[0.26, 0.14, 0.96]}>
        <torusGeometry args={[0.18, 0.04, 16, 48]} />
        <meshStandardMaterial color={darkMetal} metalness={0.6} roughness={0.3} />
      </mesh>

      {/* Eye backplates (dark screen behind eyes) */}
      <mesh position={[-0.26, 0.14, 0.92]}>
        <circleGeometry args={[0.16, 32]} />
        <meshStandardMaterial color="#111827" metalness={0.2} roughness={0.8} />
      </mesh>
      <mesh position={[0.26, 0.14, 0.92]}>
        <circleGeometry args={[0.16, 32]} />
        <meshStandardMaterial color="#111827" metalness={0.2} roughness={0.8} />
      </mesh>

      {/* Glowing irises */}
      <mesh position={[-0.26, 0.14, 0.96]}>
        <sphereGeometry args={[0.13, 32, 32]} />
        <meshStandardMaterial color={eyeGlow} emissive={eyeGlow} emissiveIntensity={1.2} />
      </mesh>
      <mesh position={[0.26, 0.14, 0.96]}>
        <sphereGeometry args={[0.13, 32, 32]} />
        <meshStandardMaterial color={eyeGlow} emissive={eyeGlow} emissiveIntensity={1.2} />
      </mesh>

      {/* Pupils (track cursor) */}
      <mesh ref={leftPupil} position={[-0.26, 0.14, 1.02]}>
        <sphereGeometry args={[0.065, 24, 24]} />
        <meshStandardMaterial color="#0f172a" />
      </mesh>
      <mesh ref={rightPupil} position={[0.26, 0.14, 1.02]}>
        <sphereGeometry args={[0.065, 24, 24]} />
        <meshStandardMaterial color="#0f172a" />
      </mesh>

      {/* Small LED mouth (cute smile) */}
      <mesh position={[0, -0.28, 0.94]} rotation={[0, 0, Math.PI]}>
        <torusGeometry args={[0.1, 0.018, 12, 32, Math.PI]} />
        <meshStandardMaterial color="#34d399" emissive="#34d399" emissiveIntensity={0.8} />
      </mesh>

      {/* Cheek LEDs (tiny accent lights) */}
      <mesh position={[-0.42, -0.1, 0.88]}>
        <sphereGeometry args={[0.04, 12, 12]} />
        <meshStandardMaterial color="#f472b6" emissive="#f472b6" emissiveIntensity={0.9} />
      </mesh>
      <mesh position={[0.42, -0.1, 0.88]}>
        <sphereGeometry args={[0.04, 12, 12]} />
        <meshStandardMaterial color="#f472b6" emissive="#f472b6" emissiveIntensity={0.9} />
      </mesh>
    </group>
  );
}

export default function Avatar3D({ size = 48 }: { size?: number }) {
  const [mounted, setMounted] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const pointer = useGlobalPointer(wrapRef);
  useEffect(() => setMounted(true), []);

  return (
    <div
      ref={wrapRef}
      style={{ width: size, height: size }}
      className="rounded-full overflow-hidden border-2 border-primary/40 shadow-lg bg-[#0f172a]"
    >
      {mounted && (
        <Canvas
          camera={{ position: [0, 0, 3.1], fov: 35 }}
          dpr={[1, 2]}
          gl={{ antialias: true, alpha: true }}
        >
          <ambientLight intensity={0.6} />
          <directionalLight position={[2, 3, 4]} intensity={1.2} />
          <directionalLight position={[-3, -1, 2]} intensity={0.3} color="#60a5fa" />
          <Suspense fallback={null}>
            <Head pointer={pointer} />
          </Suspense>
        </Canvas>
      )}
    </div>
  );
}
