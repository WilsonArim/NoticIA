"use client";

import { useState } from "react";
import Link from "next/link";
import { ChevronDown } from "lucide-react";
import {
  CATEGORY_GROUPS,
  getCategoriesByGroup,
} from "@/lib/constants/categories";

const mainLinks = [
  { href: "/categoria", label: "Últimas" },
  { href: "/cronistas", label: "Cronistas" },
  { href: "/search", label: "Pesquisar" },
];

export function MobileMenu() {
  const [open, setOpen] = useState(false);
  const [categoriesOpen, setCategoriesOpen] = useState(false);

  return (
    <div className="md:hidden">
      <button
        onClick={() => setOpen(!open)}
        aria-label="Menu"
        className="flex h-9 w-9 items-center justify-center rounded-lg transition-colors"
        style={{ color: "var(--text-tertiary)" }}
      >
        {open ? (
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        )}
      </button>

      {open && (
        <div
          className="animate-fade-in absolute left-0 right-0 top-16 z-50 border-b px-4 py-4 shadow-lg"
          style={{
            borderColor: "var(--border-primary)",
            background: "var(--surface-elevated)",
          }}
        >
          <nav className="flex flex-col gap-1">
            {mainLinks.map(({ href, label }) => (
              <Link
                key={href}
                href={href}
                onClick={() => setOpen(false)}
                className="rounded-lg px-3 py-2.5 text-sm font-medium transition-colors"
                style={{ color: "var(--text-primary)" }}
              >
                {label}
              </Link>
            ))}

            {/* Categories accordion */}
            <button
              onClick={() => setCategoriesOpen(!categoriesOpen)}
              className="flex items-center justify-between rounded-lg px-3 py-2.5 text-sm font-medium transition-colors"
              style={{ color: "var(--text-primary)" }}
            >
              Categorias
              <ChevronDown
                size={14}
                className={`transition-transform ${categoriesOpen ? "rotate-180" : ""}`}
                style={{ color: "var(--text-tertiary)" }}
              />
            </button>

            {categoriesOpen && (
              <div
                className="animate-fade-in ml-3 space-y-1 border-l-2 pl-3"
                style={{ borderColor: "var(--border-primary)" }}
              >
                {CATEGORY_GROUPS.map((group) => {
                  const cats = getCategoriesByGroup(group.key);
                  return (
                    <div key={group.key} className="mb-3">
                      <p
                        className="mb-1 text-[10px] font-semibold uppercase tracking-wider"
                        style={{ color: "var(--text-tertiary)" }}
                      >
                        {group.label}
                      </p>
                      {cats.map((cat) => {
                        const Icon = cat.icon;
                        return (
                          <Link
                            key={cat.slug}
                            href={`/categoria/${cat.slug}`}
                            onClick={() => { setOpen(false); setCategoriesOpen(false); }}
                            className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm transition-colors"
                            style={{ color: "var(--text-secondary)" }}
                          >
                            <Icon size={14} style={{ color: cat.color }} />
                            {cat.label}
                          </Link>
                        );
                      })}
                    </div>
                  );
                })}
              </div>
            )}
          </nav>
        </div>
      )}
    </div>
  );
}
