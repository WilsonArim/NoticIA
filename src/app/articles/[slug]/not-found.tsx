import Link from "next/link";

export default function ArticleNotFound() {
  return (
    <div className="mx-auto flex max-w-7xl flex-col items-center justify-center px-4 py-24 sm:px-6 lg:px-8">
      <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
        Artigo nao encontrado
      </h2>
      <p className="mt-2 text-gray-600 dark:text-gray-400">
        O artigo que procura nao existe ou ainda nao foi publicado.
      </p>
      <Link
        href="/articles"
        className="mt-6 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
      >
        Ver todos os artigos
      </Link>
    </div>
  );
}
