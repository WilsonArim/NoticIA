import {
  Globe,
  Shield,
  TrendingUp,
  Cpu,
  Zap,
  Heart,
  FlaskConical,
  Leaf,
  Trophy,
  Flag,
  Users,
  BarChart3,
  AlertTriangle,
  Scale,
  Landmark,
  Handshake,
  Crosshair,
  FileText,
  SearchCheck,
  type LucideIcon,
} from "lucide-react";

export interface CategoryConfig {
  slug: string;
  label: string;
  description: string;
  icon: LucideIcon;
  color: string;
  group: string;
  relatedAreas: string[];
}

export interface CategoryGroup {
  key: string;
  label: string;
}

export const CATEGORY_GROUPS: CategoryGroup[] = [
  { key: "mundo", label: "Mundo" },
  { key: "ciencia_tech", label: "Ciência & Tech" },
  { key: "portugal", label: "Portugal" },
  { key: "economia", label: "Economia" },
  { key: "saude_social", label: "Saúde & Social" },
  { key: "justica", label: "Justiça & Segurança" },
];

export const CATEGORIES: CategoryConfig[] = [
  // ── Mundo ──
  {
    slug: "geopolitica",
    label: "Geopolítica",
    description: "Conflitos, alianças e o tabuleiro do poder global",
    icon: Globe,
    color: "var(--area-geopolitica)",
    group: "mundo",
    relatedAreas: ["defesa", "politica_intl", "diplomacia"],
  },
  {
    slug: "politica_intl",
    label: "Política Internacional",
    description: "Decisões políticas que moldam a ordem mundial",
    icon: Landmark,
    color: "var(--area-politica-intl)",
    group: "mundo",
    relatedAreas: ["geopolitica", "diplomacia", "defesa"],
  },
  {
    slug: "diplomacia",
    label: "Diplomacia",
    description: "Negociações, tratados e relações bilaterais",
    icon: Handshake,
    color: "var(--area-diplomacia)",
    group: "mundo",
    relatedAreas: ["geopolitica", "politica_intl", "defesa"],
  },
  {
    slug: "defesa",
    label: "Defesa",
    description: "Forças armadas, NATO e segurança colectiva",
    icon: Shield,
    color: "var(--area-defesa)",
    group: "mundo",
    relatedAreas: ["geopolitica", "defesa_estrategica", "politica_intl"],
  },
  {
    slug: "defesa_estrategica",
    label: "Defesa Estratégica",
    description: "Estratégia militar, armamento e doutrina",
    icon: Crosshair,
    color: "var(--area-defesa-estrategica)",
    group: "mundo",
    relatedAreas: ["defesa", "geopolitica", "politica_intl"],
  },

  // ── Ciência & Tech ──
  {
    slug: "tecnologia",
    label: "Tecnologia",
    description: "Inovação, IA, startups e o futuro digital",
    icon: Cpu,
    color: "var(--area-tecnologia)",
    group: "ciencia_tech",
    relatedAreas: ["ciencia", "energia", "crypto"],
  },
  {
    slug: "ciencia",
    label: "Ciência",
    description: "Descobertas, investigação e avanços científicos",
    icon: FlaskConical,
    color: "var(--area-ciencia)",
    group: "ciencia_tech",
    relatedAreas: ["tecnologia", "saude", "clima"],
  },
  {
    slug: "energia",
    label: "Energia",
    description: "Transição energética, petróleo, renováveis e nuclear",
    icon: Zap,
    color: "var(--area-energia)",
    group: "ciencia_tech",
    relatedAreas: ["clima", "economia", "tecnologia"],
  },
  {
    slug: "clima",
    label: "Clima & Ambiente",
    description: "Alterações climáticas, biodiversidade e sustentabilidade",
    icon: Leaf,
    color: "var(--area-clima)",
    group: "ciencia_tech",
    relatedAreas: ["energia", "ciencia", "regulacao"],
  },

  // ── Portugal ──
  {
    slug: "portugal",
    label: "Portugal",
    description: "Política nacional, economia e sociedade portuguesa",
    icon: Flag,
    color: "var(--area-portugal)",
    group: "portugal",
    relatedAreas: ["sociedade", "economia", "desporto"],
  },
  {
    slug: "sociedade",
    label: "Sociedade",
    description: "Temas sociais, cultura, educação e demografia",
    icon: Users,
    color: "var(--area-sociedade)",
    group: "portugal",
    relatedAreas: ["portugal", "direitos_humanos", "saude"],
  },
  {
    slug: "desporto",
    label: "Desporto",
    description: "Futebol, competições internacionais e desporto nacional",
    icon: Trophy,
    color: "var(--area-desporto)",
    group: "portugal",
    relatedAreas: ["portugal", "sociedade"],
  },

  // ── Economia ──
  {
    slug: "economia",
    label: "Economia",
    description: "Macroeconomia, PIB, emprego e comércio global",
    icon: TrendingUp,
    color: "var(--area-economia)",
    group: "economia",
    relatedAreas: ["financas", "crypto", "regulacao"],
  },
  {
    slug: "financas",
    label: "Finanças & Mercados",
    description: "Bolsas, juros, banca e investimento",
    icon: BarChart3,
    color: "var(--area-financas)",
    group: "economia",
    relatedAreas: ["economia", "crypto", "regulacao"],
  },
  {
    slug: "crypto",
    label: "Crypto & Blockchain",
    description: "Bitcoin, Ethereum, DeFi e regulação cripto",
    icon: TrendingUp,
    color: "var(--area-crypto)",
    group: "economia",
    relatedAreas: ["financas", "economia", "tecnologia"],
  },
  {
    slug: "regulacao",
    label: "Regulação",
    description: "Legislação, normas e quadros regulatórios",
    icon: FileText,
    color: "var(--area-regulacao)",
    group: "economia",
    relatedAreas: ["economia", "financas", "politica_intl"],
  },

  // ── Saúde & Social ──
  {
    slug: "saude",
    label: "Saúde",
    description: "SNS, pandemias, investigação médica e saúde pública",
    icon: Heart,
    color: "var(--area-saude)",
    group: "saude_social",
    relatedAreas: ["ciencia", "sociedade", "direitos_humanos"],
  },
  {
    slug: "direitos_humanos",
    label: "Direitos Humanos",
    description: "Liberdades civis, igualdade e justiça social",
    icon: Scale,
    color: "var(--area-direitos-humanos)",
    group: "saude_social",
    relatedAreas: ["sociedade", "saude", "politica_intl"],
  },

  // ── Justiça & Segurança ──
  {
    slug: "desinformacao",
    label: "Fact-Check",
    description: "Verificação de factos, desinformação e media literacy",
    icon: SearchCheck,
    color: "var(--area-desinformacao)",
    group: "justica",
    relatedAreas: ["sociedade", "tecnologia", "politica_intl"],
  },
  {
    slug: "crime_organizado",
    label: "Crime Organizado",
    description: "Redes criminosas, narcotráfico e segurança interna",
    icon: AlertTriangle,
    color: "var(--area-crime-organizado)",
    group: "justica",
    relatedAreas: ["direitos_humanos", "regulacao", "portugal"],
  },
];

export function getCategoryBySlug(slug: string): CategoryConfig | undefined {
  return CATEGORIES.find((c) => c.slug === slug);
}

export function getCategoriesByGroup(group: string): CategoryConfig[] {
  return CATEGORIES.filter((c) => c.group === group);
}
