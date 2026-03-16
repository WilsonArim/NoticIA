import Link from "next/link";
import { Bot, Shield, Eye } from "lucide-react";

export function Footer() {
  return (
    <footer
      className="border-t"
      style={{
        borderImage: "linear-gradient(90deg, var(--accent), var(--area-economia), var(--area-tecnologia)) 1",
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
              NoticIA
            </h3>
            <p
              className="mt-2 text-sm leading-relaxed"
              style={{ color: "var(--text-secondary)" }}
            >
              Jornalismo feito por IA de forma independente. Cada artigo
              mostra fontes, raciocínio e nível de confiança.
            </p>
          </div>

          {/* Links */}
          <div>
            <h4
              className="text-xs font-semibold uppercase tracking-wider"
              style={{ color: "var(--text-tertiary)" }}
            >
              Navegação
            </h4>
            <nav className="mt-3 flex flex-col gap-2">
              {[
                { href: "/articles", label: "Artigos" },
                { href: "/cronistas", label: "Cronistas" },
                { href: "/search", label: "Pesquisar" },
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
                <Bot size={14} className="animate-pulse-glow" style={{ color: "var(--accent)" }} />
                <span>Multi-agente ativa</span>
              </div>
              <div className="flex items-center gap-2 text-sm" style={{ color: "var(--text-secondary)" }}>
                <Shield size={14} className="animate-pulse-glow" style={{ color: "var(--area-economia)" }} />
                <span>Fact-checking automático</span>
              </div>
              <div className="flex items-center gap-2 text-sm" style={{ color: "var(--text-secondary)" }}>
                <Eye size={14} className="animate-pulse-glow" style={{ color: "var(--area-tecnologia)" }} />
                <span>Raciocínio transparente</span>
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
          Verificação multi-agente: Coletores (IA) &middot; Repórteres (Keyword + IA) &middot; Fact-checkers (Claude) &middot; Editorial (Claude)
        </div>
      </div>
    </footer>
  );
}
