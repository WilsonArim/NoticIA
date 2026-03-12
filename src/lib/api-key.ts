/**
 * Validates the PUBLISH_API_KEY used by external agents to publish articles.
 * Used in API routes / Edge Functions to authenticate the Publisher agent.
 */
export function validateApiKey(authHeader: string | null): boolean {
  if (!authHeader) return false;

  const token = authHeader.startsWith("Bearer ")
    ? authHeader.slice(7)
    : authHeader;

  const expectedKey = process.env.PUBLISH_API_KEY;

  if (!expectedKey) {
    console.error("PUBLISH_API_KEY environment variable is not set");
    return false;
  }

  // Constant-time comparison to prevent timing attacks
  if (token.length !== expectedKey.length) return false;

  let result = 0;
  for (let i = 0; i < token.length; i++) {
    result |= token.charCodeAt(i) ^ expectedKey.charCodeAt(i);
  }

  return result === 0;
}
