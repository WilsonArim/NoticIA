"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronDown } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import {
  CATEGORY_GROUPS,
  getCategoriesByGroup,
} from "@/lib/constants/categories";

export function MegaMenu() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const pathname = usePathname();
  const isActive = pathname.startsWith("/categoria");

  // Close on route change
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  // Close on click outside
  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function handleEscape(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative flex items-center gap-1 rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:opacity-70"
        style={{ color: isActive ? "var(--text-primary)" : "var(--text-secondary)" }}
      >
        Categorias
        <ChevronDown
          size={14}
          className={`transition-transform ${open ? "rotate-180" : ""}`}
        />
        {isActive && (
          <span
            className="absolute inset-x-1 -bottom-0.5 h-0.5 rounded-full"
            style={{ background: "var(--accent)" }}
          />
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ duration: 0.2 }}
            className="absolute left-1/2 top-full z-50 mt-2 w-[640px] -translate-x-1/2 overflow-hidden rounded-2xl border shadow-xl"
            style={{
              borderColor: "var(--border-primary)",
              background: "var(--surface-elevated)",
            }}
          >
            <div className="grid grid-cols-3 gap-0 p-5">
              {CATEGORY_GROUPS.map((group) => {
                const cats = getCategoriesByGroup(group.key);
                return (
                  <div key={group.key} className="mb-4">
                    <h3
                      className="mb-2 text-[11px] font-semibold uppercase tracking-wider"
                      style={{ color: "var(--text-tertiary)" }}
                    >
                      {group.label}
                    </h3>
                    <div className="space-y-0.5">
                      {cats.map((cat) => {
                        const Icon = cat.icon;
                        return (
                          <Link
                            key={cat.slug}
                            href={`/categoria/${cat.slug}`}
                            className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm transition-colors"
                            style={{ color: "var(--text-secondary)" }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.background = "var(--surface-secondary)";
                              e.currentTarget.style.color = "var(--text-primary)";
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.background = "transparent";
                              e.currentTarget.style.color = "var(--text-secondary)";
                            }}
                          >
                            <Icon size={14} style={{ color: cat.color }} />
                            {cat.label}
                          </Link>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Footer link */}
            <div
              className="border-t px-5 py-3"
              style={{ borderColor: "var(--border-primary)" }}
            >
              <Link
                href="/categoria"
                className="text-xs font-medium transition-opacity hover:opacity-70"
                style={{ color: "var(--accent)" }}
              >
                Ver todas as categorias &rarr;
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
