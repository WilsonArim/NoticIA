import Link from "next/link";
import { Bot, Shield, Eye } from "lucide-react";

export function Footer() {
  return (
    <footer
      className="border-t"
      style={{
        borderImage: "linear-gradient(90deg, var(--accent), var(--area-economia), var(--area-tecnologia)) 1",
        background:
          "linear-gradient(135deg, var(--surface-secondary) 0%, color-mix(in srgb, var(--surface-secondary) 95%, var(--accent) 5%) 50%, var(--surface-secondary) 100%)",
      }}
    >
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-10 sm:grid-cols-2">
          {/* About + Navigation */}
          <div>
            <h3
              className="font-serif text-xl font-bold tracking-tight"
              style={{ color: "var(--text-primary)" }}
            >
              NoticIA
            </h3>
            <p
              className="mt-3 max-w-md text-sm leading-relaxed"
              style={{ color: "var(--text-secondary)" }}
            >
              Jornalismo feito por IA de forma independente. Cada artigo
              mostra fontes, raciocínio e nível de confiança.
            </p>
            <nav className="mt-5 flex gap-4">
              {[
                { href: "/categoria", label: "Artigos" },
                { href: "/cronistas", label: "Cronistas" },
                { href: "/search", label: "Pesquisar" },
                { href: "/privacidade", label: "Privacidade" },
              ].map(({ href, label }) => (
                <Link
                  key={href}
                  href={href}
                  className="text-sm font-medium transition-opacity hover:opacity-70"
                  style={{ color: "var(--text-secondary)" }}
                >
                  {label}
                </Link>
              ))}
            </nav>
          </div>

          {/* Pipeline Status — larger icons with pulse */}
          <div>
            <h4
              className="text-xs font-semibold uppercase tracking-wider"
              style={{ color: "var(--text-tertiary)" }}
            >
              Pipeline
            </h4>
            <div className="mt-4 space-y-3.5">
              {[
                { icon: Bot, label: "Multi-agente ativa", color: "var(--accent)" },
                { icon: Shield, label: "Fact-checking automático", color: "var(--area-economia)" },
                { icon: Eye, label: "Raciocínio transparente", color: "var(--area-tecnologia)" },
              ].map(({ icon: Icon, label, color }) => (
                <div key={label} className="flex items-center gap-3">
                  <div
                    className="flex h-8 w-8 items-center justify-center rounded-lg"
                    style={{ background: `color-mix(in srgb, ${color} 12%, transparent)` }}
                  >
                    <Icon
                      size={16}
                      className="animate-pulse-glow"
                      style={{ color }}
                    />
                  </div>
                  <span className="text-sm" style={{ color: "var(--text-secondary)" }}>
                    {label}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div
          className="mt-10 border-t pt-6 text-xs"
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
