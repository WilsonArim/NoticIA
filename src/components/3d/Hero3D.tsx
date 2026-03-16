"use client";

import { lazy, Suspense, useEffect, useState } from "react";

const NewsGlobe = lazy(() => import("./NewsGlobe"));
const ParticleField = lazy(() => import("./ParticleField"));

export function Hero3D() {
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

  if (!canRender) return null;

  return (
    <>
      <Suspense fallback={null}>
        <ParticleField />
      </Suspense>
    </>
  );
}

export function HeroGlobe() {
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

  if (!canRender) return null;

  return (
    <Suspense fallback={null}>
      <NewsGlobe />
    </Suspense>
  );
}
