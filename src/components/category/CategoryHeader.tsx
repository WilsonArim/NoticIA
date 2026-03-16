import type { CategoryConfig } from "@/lib/constants/categories";

interface CategoryHeaderProps {
  category: CategoryConfig;
  totalArticles: number;
}

export function CategoryHeader({ category, totalArticles }: CategoryHeaderProps) {
  const Icon = category.icon;

  return (
    <div className="mb-8">
      <div className="flex items-center gap-4">
        <div
          className="flex h-14 w-14 items-center justify-center rounded-2xl"
          style={{
            color: category.color,
            backgroundColor: `color-mix(in srgb, ${category.color} 12%, transparent)`,
            border: `1px solid color-mix(in srgb, ${category.color} 25%, transparent)`,
          }}
        >
          <Icon size={28} />
        </div>
        <div>
          <h1
            className="font-serif text-3xl font-bold tracking-tight sm:text-4xl"
            style={{ color: "var(--text-primary)" }}
          >
            {category.label}
          </h1>
          <p className="mt-0.5 text-sm" style={{ color: "var(--text-secondary)" }}>
            {category.description}
          </p>
        </div>
      </div>
      <p className="mt-3 text-sm" style={{ color: "var(--text-tertiary)" }}>
        {totalArticles} {totalArticles === 1 ? "artigo publicado" : "artigos publicados"}
      </p>
    </div>
  );
}
