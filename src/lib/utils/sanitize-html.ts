/**
 * Server-safe HTML sanitizer — sem dependências externas de DOM.
 * Usa regex para remover tags e atributos perigosos.
 * Conteúdo vem do nosso próprio pipeline controlado, por isso
 * a abordagem de allowlist é suficiente e segura.
 */

const ALLOWED_TAGS = new Set([
  "h1", "h2", "h3", "h4", "h5", "h6",
  "p", "br", "hr",
  "ul", "ol", "li",
  "strong", "em", "b", "i", "u", "s", "mark",
  "a", "blockquote", "pre", "code",
  "table", "thead", "tbody", "tr", "th", "td",
  "figure", "figcaption", "img",
  "span", "div", "section",
]);

const ALLOWED_ATTR = new Set([
  "href", "target", "rel", "src", "alt", "width", "height",
  "class", "id", "title",
]);

const DANGEROUS_PROTOCOLS = /^(javascript|vbscript|data):/i;

/** Remove tags não permitidas, mantendo o seu conteúdo interno */
function stripDisallowedTags(html: string): string {
  return html.replace(/<\/?([a-zA-Z][a-zA-Z0-9]*)[^>]*>/g, (match, tagName) => {
    const tag = tagName.toLowerCase();
    if (ALLOWED_TAGS.has(tag)) return match;
    // Tag não permitida: mantém texto, remove a tag
    return "";
  });
}

/** Remove atributos não permitidos e URLs perigosos */
function stripDisallowedAttrs(html: string): string {
  return html.replace(/<([a-zA-Z][a-zA-Z0-9]*)((?:\s+[^>]*)?)>/g, (match, tagName, attrs) => {
    if (!attrs) return match;

    const cleanAttrs = attrs.replace(
      /\s+([a-zA-Z][a-zA-Z0-9-]*)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]*)))?/g,
      (_: string, attrName: string, dq: string, sq: string, uq: string) => {
        const attr = attrName.toLowerCase();
        if (!ALLOWED_ATTR.has(attr)) return "";

        const value = dq ?? sq ?? uq ?? "";

        // Bloquear protocolos perigosos em href e src
        if ((attr === "href" || attr === "src") && DANGEROUS_PROTOCOLS.test(value.trim())) {
          return "";
        }

        // Forçar rel="noopener noreferrer" em links externos
        if (attr === "href" && value.startsWith("http")) {
          return ` href="${value}" rel="noopener noreferrer" target="_blank"`;
        }

        return ` ${attr}="${value}"`;
      }
    );

    return `<${tagName}${cleanAttrs}>`;
  });
}

/** Remove event handlers inline (onclick, onload, etc.) */
function stripEventHandlers(html: string): string {
  return html.replace(/\s+on[a-zA-Z]+\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]*)/g, "");
}

export function sanitizeHtml(dirty: string): string {
  if (!dirty) return "";
  let result = dirty;
  result = stripEventHandlers(result);
  result = stripDisallowedAttrs(result);
  result = stripDisallowedTags(result);
  return result;
}
