"use client";

import type { VerificationStatus } from "@/types/article";

interface VerificationStampProps {
  status: VerificationStatus | string;
  verificationChangedAt?: string | null;
  size?: "sm" | "lg";
}

/**
 * Visual "stamp" overlay for article verification state.
 *
 * - none: renders nothing
 * - under_review: orange "⚠ Em Verificação"
 * - verified: green "✓ Verificado" (auto-hides 48h after verification_changed_at)
 * - debunked: red "✗ FALSO" (permanent, impossible to miss)
 */
export function VerificationStamp({
  status,
  verificationChangedAt,
  size = "sm",
}: VerificationStampProps) {
  if (!status || status === "none") return null;

  // "Verified" auto-hides after 48 hours
  if (status === "verified" && verificationChangedAt) {
    const hoursElapsed =
      (Date.now() - new Date(verificationChangedAt).getTime()) / (1000 * 60 * 60);
    if (hoursElapsed > 48) return null;
  }

  const isLg = size === "lg";

  if (status === "debunked") {
    return (
      <div
        className={`pointer-events-none select-none font-serif font-black uppercase tracking-wider ${
          isLg ? "text-2xl px-5 py-2" : "text-[11px] px-2.5 py-1"
        }`}
        style={{
          color: "#dc2626",
          border: `${isLg ? "3px" : "2px"} solid #dc2626`,
          borderRadius: isLg ? "8px" : "6px",
          background: "rgba(220, 38, 38, 0.08)",
          transform: "rotate(-4deg)",
          whiteSpace: "nowrap",
        }}
      >
        ✗ FALSO
      </div>
    );
  }

  if (status === "under_review") {
    return (
      <div
        className={`pointer-events-none select-none font-semibold uppercase tracking-wider ${
          isLg ? "text-sm px-4 py-1.5" : "text-[10px] px-2 py-0.5"
        }`}
        style={{
          color: "#d97706",
          border: `${isLg ? "2px" : "1.5px"} solid #d97706`,
          borderRadius: isLg ? "8px" : "5px",
          background: "rgba(217, 119, 6, 0.08)",
          transform: "rotate(-3deg)",
          whiteSpace: "nowrap",
        }}
      >
        ⚠ Em Verificação
      </div>
    );
  }

  if (status === "verified") {
    return (
      <div
        className={`pointer-events-none select-none font-semibold uppercase tracking-wider ${
          isLg ? "text-sm px-4 py-1.5" : "text-[10px] px-2 py-0.5"
        }`}
        style={{
          color: "#16a34a",
          border: `${isLg ? "2px" : "1.5px"} solid #16a34a`,
          borderRadius: isLg ? "8px" : "5px",
          background: "rgba(22, 163, 74, 0.08)",
          transform: "rotate(-3deg)",
          whiteSpace: "nowrap",
        }}
      >
        ✓ Verificado
      </div>
    );
  }

  return null;
}
