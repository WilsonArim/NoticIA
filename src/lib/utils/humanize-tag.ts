/** Map of common Portuguese slugified terms to their accented/readable versions */
const ACCENT_MAP: Record<string, string> = {
  geopolitica: "Geopolítica",
  ciencia: "Ciência",
  tecnologia: "Tecnologia",
  economia: "Economia",
  saude: "Saúde",
  energia: "Energia",
  sociedade: "Sociedade",
  regulacao: "Regulação",
  portugal: "Portugal",
  desporto: "Desporto",
  ambiente: "Ambiente",
  mercados: "Mercados",
  crypto: "Crypto",
  defesa: "Defesa",
  diplomacia: "Diplomacia",
  desinformacao: "Desinformação",
  "direitos-humanos": "Direitos Humanos",
  "crime-organizado": "Crime Organizado",
  "defesa-estrategica": "Defesa Estratégica",
  politica_intl: "Política Internacional",
  "politica-internacional": "Política Internacional",
  "coreia-do-norte": "Coreia do Norte",
  "coreia-do-sul": "Coreia do Sul",
  "estados-unidos": "Estados Unidos",
  "reino-unido": "Reino Unido",
  "uniao-europeia": "União Europeia",
  "taca-asiatica": "Taça Asiática",
  "copa-do-mundo": "Copa do Mundo",
  "champions-league": "Champions League",
  "inteligencia-artificial": "Inteligência Artificial",
  "alteracoes-climaticas": "Alterações Climáticas",
  "energias-renovaveis": "Energias Renováveis",
  sancoes: "Sanções",
  eleicoes: "Eleições",
  inflacao: "Inflação",
  imigracao: "Imigração",
  educacao: "Educação",
  corrupcao: "Corrupção",
  legislacao: "Legislação",
  eua: "EUA",
  ue: "UE",
  onu: "ONU",
  oms: "OMS",
  otan: "OTAN",
  nato: "NATO",
  pib: "PIB",
  ia: "IA",
  australia: "Austrália",
  russia: "Rússia",
  ucrania: "Ucrânia",
  libano: "Líbano",
  "futebol-feminino": "Futebol Feminino",
  "fact-check": "Fact-check",
};

/**
 * Convert a slugified tag to human-readable Portuguese text.
 * Replaces hyphens with spaces, capitalizes, and restores accents.
 */
export function humanizeTag(tag: string): string {
  const lower = tag.toLowerCase();

  // Always check lookup first (handles acronyms like EUA, UE, ONU and accented terms)
  if (ACCENT_MAP[lower]) return ACCENT_MAP[lower];

  // If tag already has mixed case (not all-lower/all-upper), it's pre-formatted
  // — only replace hyphens with spaces, preserve existing casing
  if (tag !== tag.toLowerCase() && tag !== tag.toUpperCase()) {
    return tag.replace(/-/g, " ");
  }

  // Fallback: replace hyphens, capitalize first letter of each space-separated word
  // (avoid \b\w which breaks with Unicode/accented characters)
  return lower
    .replace(/-/g, " ")
    .split(" ")
    .map((word) => (word.length > 0 ? word[0].toUpperCase() + word.slice(1) : word))
    .join(" ");
}
