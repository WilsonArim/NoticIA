"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function SearchBar() {
  const router = useRouter();
  const [query, setQuery] = useState("");

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
        placeholder="Pesquisar..."
        className="h-9 w-40 rounded-lg border border-gray-200 bg-gray-50 px-3 text-sm placeholder-gray-400 outline-none transition-all focus:w-56 focus:border-blue-500 focus:bg-white focus:ring-1 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-800 dark:placeholder-gray-500 dark:focus:border-blue-400 dark:focus:bg-gray-900 sm:w-48 sm:focus:w-64"
      />
    </form>
  );
}
