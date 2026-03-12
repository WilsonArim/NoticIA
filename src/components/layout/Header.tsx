import Link from "next/link";
import { SearchBar } from "./SearchBar";
import { DarkModeToggle } from "./DarkModeToggle";
import { MobileMenu } from "./MobileMenu";

export function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-gray-200 bg-white/90 backdrop-blur-lg dark:border-gray-800 dark:bg-gray-950/90">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        {/* Logo */}
        <Link href="/" className="flex shrink-0 items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-sm font-bold text-white">
            CN
          </div>
          <span className="hidden text-lg font-semibold text-gray-900 dark:text-gray-100 sm:inline">
            Curador de Noticias
          </span>
        </Link>

        {/* Desktop navigation */}
        <nav className="hidden items-center gap-1 md:flex">
          {[
            { href: "/articles", label: "Artigos" },
            { href: "/search", label: "Pesquisar" },
            { href: "/dashboard", label: "Dashboard" },
          ].map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className="rounded-lg px-3 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-100"
            >
              {label}
            </Link>
          ))}
        </nav>

        {/* Right side: search + dark mode + mobile menu */}
        <div className="flex items-center gap-1">
          <SearchBar />
          <DarkModeToggle />
          <MobileMenu />
        </div>
      </div>
    </header>
  );
}
