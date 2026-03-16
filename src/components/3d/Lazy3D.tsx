"use client";

import { lazy, Suspense, useEffect, useState, type ComponentType } from "react";

interface Lazy3DProps {
  /** The 3D component to render (lazy-imported) */
  component: ComponentType<Record<string, unknown>>;
  /** Props to pass to the 3D component */
  componentProps?: Record<string, unknown>;
  /** Fallback element while loading or on unsupported devices */
  fallback?: React.ReactNode;
}

function useCanRender3D() {
  const [can, setCan] = useState(false);
  useEffect(() => {
    // Skip 3D on mobile or low-end devices
    const isMobile = window.innerWidth < 768;
    const lowCPU =
      typeof navigator.hardwareConcurrency === "number" &&
      navigator.hardwareConcurrency < 4;
    const prefersReduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    setCan(!isMobile && !lowCPU && !prefersReduced);
  }, []);
  return can;
}

export function Lazy3D({
  component: Component,
  componentProps = {},
  fallback = null,
}: Lazy3DProps) {
  const canRender = useCanRender3D();

  if (!canRender) return <>{fallback}</>;

  return (
    <Suspense fallback={fallback}>
      <Component {...componentProps} />
    </Suspense>
  );
}

/**
 * Helper to create a lazy-loaded 3D component with automatic
 * mobile/performance fallback.
 */
export function createLazy3D<P extends Record<string, unknown>>(
  importFn: () => Promise<{ default: ComponentType<P> }>,
  fallback?: React.ReactNode,
) {
  const LazyComponent = lazy(importFn);

  return function Lazy3DWrapper(props: P) {
    return (
      <Lazy3D
        component={LazyComponent as ComponentType<Record<string, unknown>>}
        componentProps={props as Record<string, unknown>}
        fallback={fallback}
      />
    );
  };
}
