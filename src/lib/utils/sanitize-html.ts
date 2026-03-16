import DOMPurify from "isomorphic-dompurify";

const ALLOWED_TAGS = [
  "h1", "h2", "h3", "h4", "h5", "h6",
  "p", "br", "hr",
  "ul", "ol", "li",
  "strong", "em", "b", "i", "u", "s", "mark",
  "a", "blockquote", "pre", "code",
  "table", "thead", "tbody", "tr", "th", "td",
  "figure", "figcaption", "img",
  "span", "div", "section",
];

const ALLOWED_ATTR = [
  "href", "target", "rel", "src", "alt", "width", "height",
  "class", "id", "title",
];

export function sanitizeHtml(dirty: string): string {
  return DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    ALLOW_DATA_ATTR: false,
    ADD_ATTR: ["target"],
  });
}
