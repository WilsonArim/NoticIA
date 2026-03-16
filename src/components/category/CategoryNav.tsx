import Link from "next/link";
import { getCategoryBySlug } from "@/lib/constants/categories";

interface CategoryNavProps {
  areas: string[];
  currentSlug: string;
}

export function CategoryNav({ areas, currentSlug }: CategoryNavProps) {
  const categories = areas
    .filter((slug) => slug !== currentSlug)
    .map((slug) => getCategoryBySlug(slug))
    .filter(Boolean);

  if (categories.length === 0) return null;

  return (
    <div className="mt-10">
      <h3
        className="mb-3 text-xs font-medium uppercase tracking-wider"
        style={{ color: "var(--text-tertiary)" }}
      >
        Categorias relacionadas
      </h3>
      <div className="flex flex-wrap gap-2">
        {categories.map((cat) => {
          if (!cat) return null;
          const Icon = cat.icon;
          return (
            <Link
              key={cat.slug}
              href={`/categoria/${cat.slug}`}
              className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-opacity hover:opacity-80"
              style={{
                color: cat.color,
                backgroundColor: `color-mix(in srgb, ${cat.color} 10%, transparent)`,
                border: `1px solid color-mix(in srgb, ${cat.color} 20%, transparent)`,
              }}
            >
              <Icon size={12} />
              {cat.label}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
