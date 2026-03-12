import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t border-gray-200 bg-gray-50 dark:border-gray-800 dark:bg-gray-900">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
          <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
            <div className="flex h-6 w-6 items-center justify-center rounded bg-blue-600 text-xs font-bold text-white">
              CN
            </div>
            <span>Curador de Noticias</span>
            <span className="text-gray-300 dark:text-gray-600">|</span>
            <span>Jornalismo IA Transparente</span>
          </div>

          <nav className="flex gap-4 text-sm text-gray-500 dark:text-gray-400">
            <Link href="/articles" className="hover:text-gray-700 dark:hover:text-gray-300">
              Artigos
            </Link>
            <Link href="/search" className="hover:text-gray-700 dark:hover:text-gray-300">
              Pesquisar
            </Link>
            <Link href="/dashboard" className="hover:text-gray-700 dark:hover:text-gray-300">
              Dashboard
            </Link>
          </nav>
        </div>

        <div className="mt-4 text-center text-xs text-gray-400 dark:text-gray-500">
          Todos os artigos sao verificados por uma pipeline de IA com
          fact-checking multi-agente. Confianca e raciocinio sao sempre
          visiveis.
        </div>
      </div>
    </footer>
  );
}
