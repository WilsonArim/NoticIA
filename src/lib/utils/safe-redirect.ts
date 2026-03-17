/** Validate redirect parameter to prevent open redirect attacks */
export function getSafeRedirect(param: string | null): string {
  if (!param) return "/dashboard";
  // Must start with / and NOT with // (protocol-relative URL)
  if (param.startsWith("/") && !param.startsWith("//")) {
    return param;
  }
  return "/dashboard";
}
