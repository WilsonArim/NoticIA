import Link from "next/link";

export default function CategoryNotFound() {
  return (
    <div className="mx-auto flex max-w-7xl flex-col items-center justify-center px-4 py-32 sm:px-6 lg:px-8">
      <h1
        className="font-serif text-4xl font-bold"
        style={{ color: "var(--text-primary)" }}
      >
        Categoria não encontrada
      </h1>
      <p className="mt-3 text-sm" style={{ color: "var(--text-secondary)" }}>
        A categoria que procura não existe ou foi removida.
      </p>
      <Link
        href="/categoria"
        className="mt-6 inline-flex items-center gap-1 rounded-xl px-4 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90"
        style={{ background: "var(--accent)" }}
      >
        &larr; Todas as categorias
      </Link>
    </div>
  );
}
