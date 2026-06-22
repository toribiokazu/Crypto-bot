import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Suspense, useRef, useState, useEffect } from "react";
import * as THREE from "three";

/**
 * Interactive stylized 3D head that follows the mouse cursor.
 * - Whole head rotates toward cursor (clamped)
 * - Eyes track cursor independently for extra liveliness
 * - Subtle idle breathing/bob
 */

function Head() {
  const group = useRef<THREE.Group>(null);
  const leftEye = useRef<THREE.Mesh>(null);
  const rightEye = useRef<THREE.Mesh>(null);
  const mouth = useRef<THREE.Mesh>(null);
  const { pointer } = useThree();
  const target = useRef(new THREE.Vector2(0, 0));

  useFrame((state) => {
    target.current.lerp(pointer, 0.15);
    const tx = target.current.x;
    const ty = target.current.y;

    if (group.current) {
      // Clamp rotation
      group.current.rotation.y = THREE.MathUtils.lerp(group.current.rotation.y, tx * 0.6, 0.15);
      group.current.rotation.x = THREE.MathUtils.lerp(group.current.rotation.x, -ty * 0.4, 0.15);
      // Idle bob
      group.current.position.y = Math.sin(state.clock.elapsedTime * 1.4) * 0.04;
    }

    // Eye pupil offset
    const eyeMax = 0.04;
    [leftEye, rightEye].forEach((ref) => {
      if (!ref.current) return;
      ref.current.position.x = (ref === leftEye ? -0.28 : 0.28) + tx * eyeMax;
      ref.current.position.y = 0.12 + ty * eyeMax;
    });

    if (mouth.current) {
      const s = 1 + Math.sin(state.clock.elapsedTime * 2) * 0.05;
      mouth.current.scale.set(s, 1, 1);
    }
  });

  return (
    <group ref={group}>
      {/* Head */}
      <mesh castShadow receiveShadow>
        <sphereGeometry args={[1, 64, 64]} />
        <meshStandardMaterial color="#f3c6a0" roughness={0.55} metalness={0.05} />
      </mesh>

      {/* Hair cap */}
      <mesh position={[0, 0.55, -0.05]} rotation={[0.2, 0, 0]}>
        <sphereGeometry args={[1.02, 48, 48, 0, Math.PI * 2, 0, Math.PI / 2.1]} />
        <meshStandardMaterial color="#2a1a14" roughness={0.8} />
      </mesh>

      {/* Eye whites */}
      <mesh position={[-0.28, 0.12, 0.88]}>
        <sphereGeometry args={[0.16, 32, 32]} />
        <meshStandardMaterial color="#ffffff" roughness={0.3} />
      </mesh>
      <mesh position={[0.28, 0.12, 0.88]}>
        <sphereGeometry args={[0.16, 32, 32]} />
        <meshStandardMaterial color="#ffffff" roughness={0.3} />
      </mesh>

      {/* Pupils (move) */}
      <mesh ref={leftEye} position={[-0.28, 0.12, 1.02]}>
        <sphereGeometry args={[0.06, 24, 24]} />
        <meshStandardMaterial color="#1a1209" />
      </mesh>
      <mesh ref={rightEye} position={[0.28, 0.12, 1.02]}>
        <sphereGeometry args={[0.06, 24, 24]} />
        <meshStandardMaterial color="#1a1209" />
      </mesh>

      {/* Eyebrows */}
      <mesh position={[-0.28, 0.36, 0.92]} rotation={[0, 0, -0.1]}>
        <boxGeometry args={[0.22, 0.04, 0.04]} />
        <meshStandardMaterial color="#2a1a14" />
      </mesh>
      <mesh position={[0.28, 0.36, 0.92]} rotation={[0, 0, 0.1]}>
        <boxGeometry args={[0.22, 0.04, 0.04]} />
        <meshStandardMaterial color="#2a1a14" />
      </mesh>

      {/* Nose */}
      <mesh position={[0, -0.05, 1.0]} rotation={[Math.PI / 2, 0, 0]}>
        <coneGeometry args={[0.08, 0.18, 16]} />
        <meshStandardMaterial color="#e9b890" />
      </mesh>

      {/* Mouth */}
      <mesh ref={mouth} position={[0, -0.35, 0.92]}>
        <torusGeometry args={[0.14, 0.03, 12, 32, Math.PI]} />
        <meshStandardMaterial color="#a64030" />
      </mesh>

      {/* Cheeks */}
      <mesh position={[-0.42, -0.15, 0.82]}>
        <sphereGeometry args={[0.1, 16, 16]} />
        <meshStandardMaterial color="#ec9a8a" transparent opacity={0.45} />
      </mesh>
      <mesh position={[0.42, -0.15, 0.82]}>
        <sphereGeometry args={[0.1, 16, 16]} />
        <meshStandardMaterial color="#ec9a8a" transparent opacity={0.45} />
      </mesh>
    </group>
  );
}

export default function Avatar3D({ size = 48 }: { size?: number }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) return <div style={{ width: size, height: size }} />;

  return (
    <div
      style={{ width: size, height: size }}
      className="rounded-full overflow-hidden border-2 border-primary/40 shadow-lg"
    >
      <Canvas
        camera={{ position: [0, 0, 3], fov: 35 }}
        dpr={[1, 2]}
        gl={{ antialias: true, alpha: true }}
        style={{ background: "transparent" }}
      >
        <color attach="background" args={["#1a1410"]} />
        <ambientLight intensity={0.6} />
        <directionalLight position={[2, 3, 4]} intensity={1.1} />
        <directionalLight position={[-3, -1, 2]} intensity={0.4} color="#ffb070" />
        <Suspense fallback={null}>
          <Head />
        </Suspense>
      </Canvas>
    </div>
  );
}
