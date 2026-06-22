import { Canvas, useFrame } from "@react-three/fiber";
import { Suspense, useRef, useState, useEffect } from "react";
import * as THREE from "three";

/**
 * Cute chibi-style 3D head that tracks the mouse cursor across the entire window.
 */

// Shared mouse target in screen-normalized coords (-1..1 from this canvas's center)
function useGlobalPointer(canvasRef: React.RefObject<HTMLDivElement | null>) {
  const target = useRef({ x: 0, y: 0 });
  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      const el = canvasRef.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      const cx = r.left + r.width / 2;
      const cy = r.top + r.height / 2;
      // normalize by viewport so big movements still saturate nicely
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
  const leftLid = useRef<THREE.Mesh>(null);
  const rightLid = useRef<THREE.Mesh>(null);
  const mouth = useRef<THREE.Mesh>(null);
  const smooth = useRef({ x: 0, y: 0 });
  const blink = useRef({ t: 0, next: 3 });

  useFrame((state, dt) => {
    smooth.current.x += (pointer.current.x - smooth.current.x) * 0.12;
    smooth.current.y += (pointer.current.y - smooth.current.y) * 0.12;
    const tx = smooth.current.x;
    const ty = smooth.current.y;

    if (group.current) {
      group.current.rotation.y = tx * 0.7;
      group.current.rotation.x = ty * 0.45;
      group.current.position.y = Math.sin(state.clock.elapsedTime * 1.6) * 0.05 - 0.05;
    }

    const eyeMax = 0.05;
    [leftPupil, rightPupil].forEach((ref, i) => {
      if (!ref.current) return;
      const baseX = i === 0 ? -0.24 : 0.24;
      ref.current.position.x = baseX + tx * eyeMax;
      ref.current.position.y = 0.18 + -ty * eyeMax;
    });

    // Blink
    blink.current.t += dt;
    let scaleY = 1;
    if (blink.current.t > blink.current.next) {
      const p = blink.current.t - blink.current.next;
      if (p < 0.15) {
        scaleY = 1 - Math.sin((p / 0.15) * Math.PI);
      } else {
        blink.current.t = 0;
        blink.current.next = 2 + Math.random() * 3;
      }
    }
    [leftLid, rightLid].forEach((ref) => {
      if (ref.current) ref.current.scale.y = scaleY < 0.05 ? 0.05 : scaleY;
    });

    if (mouth.current) {
      const s = 1 + Math.sin(state.clock.elapsedTime * 2.2) * 0.08;
      mouth.current.scale.set(s, s * 0.9, 1);
    }
  });

  const skin = "#fbd5b5";
  const blush = "#ff9bb0";
  const hair = "#2a1a14";

  return (
    <group ref={group} position={[0, -0.05, 0]}>
      {/* Big chibi head */}
      <mesh>
        <sphereGeometry args={[1.05, 64, 64]} />
        <meshStandardMaterial color={skin} roughness={0.6} />
      </mesh>

      {/* Fluffy hair cap */}
      <mesh position={[0, 0.45, -0.02]} rotation={[0.15, 0, 0]}>
        <sphereGeometry args={[1.09, 48, 48, 0, Math.PI * 2, 0, Math.PI / 1.9]} />
        <meshStandardMaterial color={hair} roughness={0.9} />
      </mesh>
      {/* Hair tuft */}
      <mesh position={[0.15, 1.05, 0.1]} rotation={[0, 0, 0.6]}>
        <coneGeometry args={[0.12, 0.35, 16]} />
        <meshStandardMaterial color={hair} />
      </mesh>

      {/* Ears */}
      <mesh position={[-1.0, 0, 0]}>
        <sphereGeometry args={[0.14, 16, 16]} />
        <meshStandardMaterial color={skin} />
      </mesh>
      <mesh position={[1.0, 0, 0]}>
        <sphereGeometry args={[0.14, 16, 16]} />
        <meshStandardMaterial color={skin} />
      </mesh>

      {/* Huge cute eye whites */}
      <mesh position={[-0.24, 0.18, 0.92]}>
        <sphereGeometry args={[0.2, 32, 32]} />
        <meshStandardMaterial color="#ffffff" />
      </mesh>
      <mesh position={[0.24, 0.18, 0.92]}>
        <sphereGeometry args={[0.2, 32, 32]} />
        <meshStandardMaterial color="#ffffff" />
      </mesh>

      {/* Iris (color) */}
      <mesh position={[-0.24, 0.18, 1.07]}>
        <sphereGeometry args={[0.11, 24, 24]} />
        <meshStandardMaterial color="#4a2b1a" />
      </mesh>
      <mesh position={[0.24, 0.18, 1.07]}>
        <sphereGeometry args={[0.11, 24, 24]} />
        <meshStandardMaterial color="#4a2b1a" />
      </mesh>

      {/* Pupils (track cursor) */}
      <mesh ref={leftPupil} position={[-0.24, 0.18, 1.12]}>
        <sphereGeometry args={[0.06, 20, 20]} />
        <meshStandardMaterial color="#0d0805" />
      </mesh>
      <mesh ref={rightPupil} position={[0.24, 0.18, 1.12]}>
        <sphereGeometry args={[0.06, 20, 20]} />
        <meshStandardMaterial color="#0d0805" />
      </mesh>

      {/* Sparkle highlights */}
      <mesh position={[-0.19, 0.24, 1.16]}>
        <sphereGeometry args={[0.025, 12, 12]} />
        <meshBasicMaterial color="#ffffff" />
      </mesh>
      <mesh position={[0.29, 0.24, 1.16]}>
        <sphereGeometry args={[0.025, 12, 12]} />
        <meshBasicMaterial color="#ffffff" />
      </mesh>

      {/* Eyelids for blinking — sit just in front of the eye */}
      <mesh ref={leftLid} position={[-0.24, 0.18, 1.13]}>
        <sphereGeometry args={[0.205, 24, 24]} />
        <meshStandardMaterial color={skin} />
      </mesh>
      <mesh ref={rightLid} position={[0.24, 0.18, 1.13]}>
        <sphereGeometry args={[0.205, 24, 24]} />
        <meshStandardMaterial color={skin} />
      </mesh>

      {/* Tiny nose dot */}
      <mesh position={[0, -0.1, 1.04]}>
        <sphereGeometry args={[0.04, 12, 12]} />
        <meshStandardMaterial color="#e8a890" />
      </mesh>

      {/* Smiling mouth */}
      <mesh ref={mouth} position={[0, -0.32, 0.95]} rotation={[0, 0, Math.PI]}>
        <torusGeometry args={[0.12, 0.028, 12, 32, Math.PI]} />
        <meshStandardMaterial color="#c2554a" />
      </mesh>

      {/* Rosy cheeks */}
      <mesh position={[-0.46, -0.08, 0.85]}>
        <sphereGeometry args={[0.13, 16, 16]} />
        <meshStandardMaterial color={blush} transparent opacity={0.55} />
      </mesh>
      <mesh position={[0.46, -0.08, 0.85]}>
        <sphereGeometry args={[0.13, 16, 16]} />
        <meshStandardMaterial color={blush} transparent opacity={0.55} />
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
      className="rounded-full overflow-hidden border-2 border-primary/40 shadow-lg bg-[#1a1410]"
    >
      {mounted && (
        <Canvas
          camera={{ position: [0, 0, 3.1], fov: 35 }}
          dpr={[1, 2]}
          gl={{ antialias: true, alpha: true }}
        >
          <ambientLight intensity={0.7} />
          <directionalLight position={[2, 3, 4]} intensity={1.1} />
          <directionalLight position={[-3, -1, 2]} intensity={0.4} color="#ffb070" />
          <Suspense fallback={null}>
            <Head pointer={pointer} />
          </Suspense>
        </Canvas>
      )}
    </div>
  );
}
