import { describe, it, expect } from "vitest";
import { getSafeRedirect } from "./safe-redirect";

describe("getSafeRedirect", () => {
  it("retorna /dashboard por defeito", () => {
    expect(getSafeRedirect(null)).toBe("/dashboard");
  });

  it("aceita caminhos relativos validos", () => {
    expect(getSafeRedirect("/review")).toBe("/review");
    expect(getSafeRedirect("/articles/test")).toBe("/articles/test");
  });

  it("rejeita URLs absolutas", () => {
    expect(getSafeRedirect("https://evil.com")).toBe("/dashboard");
  });

  it("rejeita protocol-relative URLs", () => {
    expect(getSafeRedirect("//evil.com")).toBe("/dashboard");
  });
});
