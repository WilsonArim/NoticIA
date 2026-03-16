import Link from "next/link";
import { NavLink } from "./NavLink";
import { SearchBar } from "./SearchBar";
import { DarkModeToggle } from "./DarkModeToggle";
import { MobileMenu } from "./MobileMenu";
import { MegaMenu } from "./MegaMenu";

export function Header() {
  return (
    <header
      className="glass sticky top-0 z-50 border-b"
      style={{ borderColor: "var(--border-primary)" }}
    >
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        {/* Logo */}
        <Link href="/" className="flex shrink-0 items-center gap-2.5 group">
          <div
            className="relative flex h-8 w-8 items-center justify-center rounded-lg font-serif text-sm font-bold text-white"
            style={{ background: "var(--accent)" }}
          >
            N
            <span
              className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full animate-pulse-glow"
              style={{ background: "var(--accent)" }}
            />
          </div>
          <span
            className="hidden font-serif text-xl font-bold tracking-tight sm:inline"
            style={{ color: "var(--text-primary)" }}
          >
            NoticIA
          </span>
        </Link>

        {/* Desktop navigation */}
        <nav className="hidden items-center gap-0.5 md:flex">
          <NavLink href="/categoria" label="Últimas" />
          <MegaMenu />
          <NavLink href="/cronistas" label="Cronistas" />
          <NavLink href="/search" label="Pesquisar" />
        </nav>

        {/* Right side */}
        <div className="flex items-center gap-1">
          <SearchBar />
          <DarkModeToggle />
          <MobileMenu />
        </div>
      </div>
    </header>
  );
}
