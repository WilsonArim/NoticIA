"use client";

import { useEffect } from "react";
import Link from "next/link";

export default function ArticleError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[ArticleError]", error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
      <div className="mb-4 text-5xl">📰</div>
      <h2 className="mb-2 text-xl font-bold text-gray-900 dark:text-gray-50">
        Não foi possível carregar o artigo
      </h2>
      <p className="mb-6 max-w-md text-sm text-gray-500 dark:text-gray-400">
        O artigo pode ter sido removido ou estar temporariamente indisponível.
      </p>
      <div className="flex gap-3">
        <button
          onClick={reset}
          className="rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700"
        >
          Tentar novamente
        </button>
        <Link
          href="/"
          className="rounded-lg border border-gray-300 px-6 py-2.5 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
        >
          Voltar ao início
        </Link>
      </div>
    </div>
  );
}
