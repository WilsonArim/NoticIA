"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function SearchBar() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [focused, setFocused] = useState(false);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/search?q=${encodeURIComponent(query.trim())}`);
      setQuery("");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="relative">
      <input
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        placeholder="Pesquisar..."
        className="h-9 w-40 rounded-lg border px-3 text-sm outline-none transition-all focus:w-56 focus:ring-1 sm:w-48 sm:focus:w-64"
        style={{
          borderColor: focused ? "var(--accent)" : "var(--border-primary)",
          background: focused ? "var(--surface-elevated)" : "var(--surface-secondary)",
          color: "var(--text-primary)",
          // @ts-expect-error -- CSS custom property for focus ring
          "--tw-ring-color": "var(--accent)",
        }}
      />
    </form>
  );
}
