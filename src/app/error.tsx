"use client";

import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[GlobalError]", error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
      <div className="mb-4 text-5xl">⚠️</div>
      <h2 className="mb-2 text-xl font-bold text-gray-900 dark:text-gray-50">
        Algo correu mal
      </h2>
      <p className="mb-6 max-w-md text-sm text-gray-500 dark:text-gray-400">
        Ocorreu um erro inesperado. A nossa equipa foi notificada.
      </p>
      <button
        onClick={reset}
        className="rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700"
      >
        Tentar novamente
      </button>
    </div>
  );
}
