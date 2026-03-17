import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Privacidade",
  description:
    "Politica de privacidade do NoticIA. Sem cookies, sem rastreamento, sem dados pessoais.",
};

const sections = [
  {
    title: "1. Dados que recolhemos",
    content: `Nao recolhemos dados pessoais identificaveis. Especificamente:`,
    bullets: [
      "Nao exigimos registo nem criacao de conta",
      "Nao usamos formularios de contacto",
      "Nao instalamos cookies de rastreamento ou publicidade",
      "Nao partilhamos dados com terceiros para fins comerciais",
    ],
    subsections: [
      {
        title: "Vercel (alojamento)",
        text: "O site esta alojado na plataforma Vercel. Como qualquer servidor web, os servidores da Vercel registam automaticamente dados tecnicos de acesso, incluindo enderecos IP, browser utilizado e paginas visitadas. Estes registos sao usados exclusivamente para fins de seguranca e diagnostico tecnico.",
        link: {
          label: "Politica de privacidade da Vercel",
          href: "https://vercel.com/legal/privacy-policy",
        },
      },
      {
        title: "Vercel Analytics (estatisticas de visitas)",
        text: "Usamos o Vercel Analytics para compreender como o site e utilizado. Esta ferramenta foi concebida com privacidade em mente: nao usa cookies, nao rastreia utilizadores individuais e nao recolhe dados pessoais identificaveis. Os dados recolhidos sao exclusivamente agregados: numero de visitantes, paginas mais visitadas, paises de origem e tipo de dispositivo (computador/telemovel).",
      },
    ],
  },
  {
    title: "2. Cookies",
    content:
      "O NoticIA nao instala cookies de rastreamento, publicidade ou analise comportamental. Podem ser utilizados cookies tecnicos estritamente necessarios para o funcionamento do site (como cache do browser), que nao requerem consentimento nos termos do RGPD.",
  },
  {
    title: "3. Os seus direitos (RGPD)",
    content:
      "Como nao recolhemos dados pessoais identificaveis, a maioria dos direitos previstos no RGPD (acesso, rectificacao, eliminacao) nao se aplica neste contexto. Caso tenha alguma questao sobre privacidade, pode contactar-nos atraves do GitHub do projecto.",
    link: {
      label: "github.com/WilsonArim/NoticIA",
      href: "https://github.com/WilsonArim/NoticIA",
    },
  },
  {
    title: "4. Alteracoes a esta politica",
    content:
      "Qualquer alteracao a esta politica sera publicada nesta pagina com a data de actualizacao. Recomendamos que a consulte periodicamente.",
  },
  {
    title: "5. Lei aplicavel",
    content:
      "Esta politica e regida pela legislacao portuguesa e pelo Regulamento Geral sobre a Proteccao de Dados (RGPD \u2014 Regulamento UE 2016/679).",
  },
];

export default function PrivacidadePage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
      <header className="mb-10">
        <h1
          className="font-serif text-3xl font-bold tracking-tight sm:text-4xl"
          style={{ color: "var(--text-primary)" }}
        >
          Politica de Privacidade
        </h1>
        <p className="mt-3 text-sm" style={{ color: "var(--text-tertiary)" }}>
          Ultima actualizacao: Marco de 2026
        </p>
        <p
          className="mt-4 text-base leading-relaxed"
          style={{ color: "var(--text-secondary)" }}
        >
          O NoticIA (noticia-ia.vercel.app) e um site de jornalismo
          independente alimentado por inteligencia artificial. Esta politica
          explica de forma clara e transparente como tratamos os dados dos nossos
          visitantes.
        </p>
      </header>

      <div className="space-y-10">
        {sections.map((section) => (
          <section key={section.title}>
            <h2
              className="font-serif text-xl font-semibold"
              style={{ color: "var(--text-primary)" }}
            >
              {section.title}
            </h2>
            <div
              className="mt-1 h-0.5 w-12 rounded-full"
              style={{ background: "var(--accent)" }}
            />
            <p
              className="mt-4 text-sm leading-relaxed"
              style={{ color: "var(--text-secondary)" }}
            >
              {section.content}
            </p>

            {section.bullets && (
              <ul className="mt-3 space-y-1.5 pl-5">
                {section.bullets.map((b) => (
                  <li
                    key={b}
                    className="list-disc text-sm"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    {b}
                  </li>
                ))}
              </ul>
            )}

            {"subsections" in section &&
              section.subsections?.map((sub) => (
                <div
                  key={sub.title}
                  className="mt-5 rounded-xl p-5"
                  style={{ background: "var(--surface-secondary)" }}
                >
                  <h3
                    className="text-sm font-semibold"
                    style={{ color: "var(--text-primary)" }}
                  >
                    {sub.title}
                  </h3>
                  <p
                    className="mt-2 text-sm leading-relaxed"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    {sub.text}
                  </p>
                  {"link" in sub && sub.link && (
                    <a
                      href={sub.link.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-2 inline-block text-sm font-medium underline underline-offset-2 transition-opacity hover:opacity-70"
                      style={{ color: "var(--accent)" }}
                    >
                      {sub.link.label}
                    </a>
                  )}
                </div>
              ))}

            {"link" in section && section.link && (
              <a
                href={section.link.href}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-3 inline-block text-sm font-medium underline underline-offset-2 transition-opacity hover:opacity-70"
                style={{ color: "var(--accent)" }}
              >
                {section.link.label}
              </a>
            )}
          </section>
        ))}
      </div>

      <footer
        className="mt-12 border-t pt-6 text-center text-xs"
        style={{
          borderColor: "var(--border-primary)",
          color: "var(--text-tertiary)",
        }}
      >
        <Link
          href="/"
          className="font-medium transition-opacity hover:opacity-70"
          style={{ color: "var(--accent)" }}
        >
          Voltar ao NoticIA
        </Link>
      </footer>
    </div>
  );
}
