"use client";

import { lazy, Suspense, useEffect, useState } from "react";
import { CertaintyIndex } from "@/components/article/CertaintyIndex";

const ConfidenceRing3D = lazy(() => import("./ConfidenceRing3D"));

interface LazyConfidenceRingProps {
  score: number;
}

export function LazyConfidenceRing({ score }: LazyConfidenceRingProps) {
  const [canRender, setCanRender] = useState(false);

  useEffect(() => {
    const isMobile = window.innerWidth < 768;
    const lowCPU =
      typeof navigator.hardwareConcurrency === "number" &&
      navigator.hardwareConcurrency < 4;
    const prefersReduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    setCanRender(!isMobile && !lowCPU && !prefersReduced);
  }, []);

  if (!canRender) {
    return <CertaintyIndex score={score} size="lg" showLabel />;
  }

  return (
    <Suspense fallback={<CertaintyIndex score={score} size="lg" showLabel />}>
      <ConfidenceRing3D score={score} />
    </Suspense>
  );
}
