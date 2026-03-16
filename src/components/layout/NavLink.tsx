"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

interface NavLinkProps {
  href: string;
  label: string;
}

export function NavLink({ href, label }: NavLinkProps) {
  const pathname = usePathname();
  const isActive = pathname === href || pathname.startsWith(href + "/");

  return (
    <Link
      href={href}
      className="relative rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:opacity-70"
      style={{ color: isActive ? "var(--text-primary)" : "var(--text-secondary)" }}
    >
      {label}
      {isActive && (
        <span
          className="absolute inset-x-1 -bottom-0.5 h-0.5 rounded-full"
          style={{ background: "var(--accent)" }}
        />
      )}
    </Link>
  );
}
