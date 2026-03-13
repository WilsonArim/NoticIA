import Link from "next/link";
import { Bot, Shield, Eye } from "lucide-react";

export function Footer() {
  return (
    <footer
      className="border-t"
      style={{
        borderColor: "var(--border-primary)",
        background: "var(--surface-secondary)",
      }}
    >
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-8 sm:grid-cols-3">
          {/* About */}
          <div>
            <h3
              className="font-serif text-lg font-bold tracking-tight"
              style={{ color: "var(--text-primary)" }}
            >
              Curador de Noticias
            </h3>
            <p
              className="mt-2 text-sm leading-relaxed"
              style={{ color: "var(--text-secondary)" }}
            >
              Jornalismo feito por IA de forma independente. Cada artigo
              mostra fontes, raciocinio e nivel de confianca.
            </p>
          </div>

          {/* Links */}
          <div>
            <h4
              className="text-xs font-semibold uppercase tracking-wider"
              style={{ color: "var(--text-tertiary)" }}
            >
              Navegacao
            </h4>
            <nav className="mt-3 flex flex-col gap-2">
              {[
                { href: "/articles", label: "Artigos" },
                { href: "/search", label: "Pesquisar" },
                { href: "/dashboard", label: "Observatorio" },
              ].map(({ href, label }) => (
                <Link
                  key={href}
                  href={href}
                  className="text-sm transition-opacity hover:opacity-70"
                  style={{ color: "var(--text-secondary)" }}
                >
                  {label}
                </Link>
              ))}
            </nav>
          </div>

          {/* Pipeline Status */}
          <div>
            <h4
              className="text-xs font-semibold uppercase tracking-wider"
              style={{ color: "var(--text-tertiary)" }}
            >
              Pipeline
            </h4>
            <div className="mt-3 space-y-2.5">
              <div className="flex items-center gap-2 text-sm" style={{ color: "var(--text-secondary)" }}>
                <Bot size={14} style={{ color: "var(--accent)" }} />
                <span>Multi-agente ativa</span>
              </div>
              <div className="flex items-center gap-2 text-sm" style={{ color: "var(--text-secondary)" }}>
                <Shield size={14} style={{ color: "var(--area-economia)" }} />
                <span>Fact-checking automatico</span>
              </div>
              <div className="flex items-center gap-2 text-sm" style={{ color: "var(--text-secondary)" }}>
                <Eye size={14} style={{ color: "var(--area-tecnologia)" }} />
                <span>Raciocinio transparente</span>
              </div>
            </div>
          </div>
        </div>

        <div
          className="mt-8 border-t pt-6 text-center text-xs"
          style={{
            borderColor: "var(--border-primary)",
            color: "var(--text-tertiary)",
          }}
        >
          Verificacao multi-agente: Coletores (Grok) &middot; Reporteres (Claude) &middot; Fact-checkers (Grok) &middot; Editorial (Claude)
        </div>
      </div>
    </footer>
  );
}
