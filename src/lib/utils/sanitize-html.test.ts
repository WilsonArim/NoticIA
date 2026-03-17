import { describe, it, expect } from "vitest";
import { sanitizeHtml } from "./sanitize-html";

describe("sanitizeHtml", () => {
  it("permite tags seguras", () => {
    const html = "<p>Texto <strong>bold</strong></p>";
    expect(sanitizeHtml(html)).toBe(html);
  });

  it("remove scripts", () => {
    const dirty = '<p>Texto</p><script>alert("xss")</script>';
    expect(sanitizeHtml(dirty)).toBe("<p>Texto</p>");
  });

  it("remove onerror de imgs", () => {
    const dirty = '<img src="x" onerror="alert(1)">';
    const clean = sanitizeHtml(dirty);
    expect(clean).not.toContain("onerror");
    expect(clean).toContain("<img");
  });

  it("remove iframes", () => {
    const dirty = '<iframe src="https://evil.com"></iframe>';
    expect(sanitizeHtml(dirty)).toBe("");
  });

  it("permite links com href", () => {
    const html = '<a href="https://reuters.com" target="_blank">Reuters</a>';
    expect(sanitizeHtml(html)).toContain('href="https://reuters.com"');
  });
});
