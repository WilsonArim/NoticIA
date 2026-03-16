export interface Chronicle {
  id: string;
  cronista_id: string;
  title: string;
  subtitle: string | null;
  body: string | null;
  body_html: string | null;
  areas: string[];
  ideology: string;
  articles_referenced: string[] | null;
  period_start: string;
  period_end: string;
  status: string;
  published_at: string | null;
  created_at: string;
  metadata: Record<string, unknown> | null;
}

export interface CronistaInfo {
  id: string;
  name: string;
  heteronimo: string;
  bio: string;
  avatar: string;
  rubrica: string;
  ideology: string;
  description: string;
  emoji: string;
}

export const CRONISTAS: CronistaInfo[] = [
  {
    id: "realista-conservador",
    name: "O Tabuleiro",
    heteronimo: "Henrique de Ataíde",
    bio: "Antigo conselheiro diplomático, reformado em Cascais. Fala como quem já viu mapas serem redesenhados.",
    avatar: "/cronistas/henrique-de-ataide.png",
    rubrica: "Geopolítica & Defesa",
    ideology: "Conservador realista",
    description: "Analisa o xadrez geopolítico global com pragmatismo e visão estratégica.",
    emoji: "♟️",
  },
  {
    id: "liberal-progressista",
    name: "A Lente",
    heteronimo: "Sofia Amaral",
    bio: "Jornalista de investigação que cobriu crises humanitárias em três continentes. Escreve com urgência e esperança.",
    avatar: "/cronistas/sofia-amaral.png",
    rubrica: "Direitos & Sociedade",
    ideology: "Liberal progressista",
    description: "Foca nos direitos humanos, liberdades civis e progresso social.",
    emoji: "🔍",
  },
  {
    id: "libertario-tecnico",
    name: "O Gráfico",
    heteronimo: "Tomás Valério",
    bio: "Ex-trader que largou a City de Londres para escrever sobre mercados sem filtros. O Excel é a sua língua materna.",
    avatar: "/cronistas/tomas-valerio.png",
    rubrica: "Mercados & Finanças",
    ideology: "Libertário",
    description: "Dados e números sem filtro ideológico — os mercados não mentem.",
    emoji: "📊",
  },
  {
    id: "militar-pragmatico",
    name: "Terreno",
    heteronimo: "Duarte Ferreira",
    bio: "Coronel reformado com 30 anos de serviço e missões NATO nos Balcãs e Afeganistão. Sem emoção, só factos e terreno.",
    avatar: "/cronistas/duarte-ferreira.png",
    rubrica: "Defesa & Estratégia",
    ideology: "Pragmático militar",
    description: "Análise operacional de conflitos, forças armadas e segurança.",
    emoji: "🎖️",
  },
  {
    id: "ambiental-realista",
    name: "O Termómetro",
    heteronimo: "Leonor Tavares",
    bio: "Engenheira ambiental com doutoramento em política energética. Recusa alarmismo e negacionismo por igual.",
    avatar: "/cronistas/leonor-tavares.png",
    rubrica: "Clima & Energia",
    ideology: "Ambiental moderado",
    description: "A crise climática com os pés na terra — soluções pragmáticas.",
    emoji: "🌡️",
  },
  {
    id: "tech-visionario",
    name: "Horizonte",
    heteronimo: "Rafael Monteiro",
    bio: "Fundador de duas startups falhadas e uma bem-sucedida. Vive entre Lisboa e São Francisco.",
    avatar: "/cronistas/rafael-monteiro.png",
    rubrica: "Tecnologia & Futuro",
    ideology: "Aceleracionista moderado",
    description: "O futuro tecnológico e o seu impacto na sociedade e economia.",
    emoji: "🔮",
  },
  {
    id: "saude-publica",
    name: "O Diagnóstico",
    heteronimo: "Sebastião Pinto",
    bio: "Médico internista que passou 15 anos no SNS antes de se dedicar à escrita. Só aceita evidência replicada.",
    avatar: "/cronistas/sebastiao-pinto.png",
    rubrica: "Saúde & Ciência",
    ideology: "Baseado em evidência",
    description: "Saúde pública e ciência sem alarmismos — só factos verificados.",
    emoji: "🩺",
  },
  {
    id: "nacional-portugues",
    name: "A Praça",
    heteronimo: "Joaquim Braga",
    bio: "Filho de Trás-os-Montes, cresceu em Lisboa, nunca perdeu o sotaque. O café é o seu gabinete.",
    avatar: "/cronistas/joaquim-braga.png",
    rubrica: "Portugal & Sociedade",
    ideology: "Centrista português",
    description: "O olhar português sobre o mundo — soberania, identidade e futuro.",
    emoji: "🇵🇹",
  },
  {
    id: "economico-institucional",
    name: "O Balanço",
    heteronimo: "Bernardo Leitão",
    bio: "Economista com passagem pelo Banco de Portugal e FMI. Fala de juros como quem traduz para a mesa do jantar.",
    avatar: "/cronistas/bernardo-leitao.png",
    rubrica: "Economia & Instituições",
    ideology: "Técnico-económico",
    description: "Política monetária, fiscal e institucional sem viés partidário.",
    emoji: "⚖️",
  },
  {
    id: "global-vs-local",
    name: "As Duas Vozes",
    heteronimo: "Vicente & Amélia Soares",
    bio: "Irmãos gémeos que nunca concordam. Vicente viveu 20 anos em Bruxelas; Amélia nunca saiu de Coimbra.",
    avatar: "/cronistas/vicente-amelia-soares.png",
    rubrica: "Global vs Local",
    ideology: "Dialógico",
    description: "Duas perspetivas em diálogo — o global e o nacional frente a frente.",
    emoji: "🗣️",
  },
];
