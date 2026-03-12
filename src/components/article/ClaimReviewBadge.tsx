import type { VerificationStatus } from "@/types/claim";

interface ClaimReviewBadgeProps {
  status: VerificationStatus | string;
  size?: "sm" | "md";
}

const statusConfig: Record<
  string,
  { label: string; color: string; icon: string }
> = {
  verified: {
    label: "Verificado",
    color:
      "bg-green-50 text-green-700 border-green-200 dark:bg-green-950 dark:text-green-400 dark:border-green-800",
    icon: "\u2713",
  },
  refuted: {
    label: "Refutado",
    color:
      "bg-red-50 text-red-700 border-red-200 dark:bg-red-950 dark:text-red-400 dark:border-red-800",
    icon: "\u2717",
  },
  disputed: {
    label: "Disputado",
    color:
      "bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-950 dark:text-orange-400 dark:border-orange-800",
    icon: "!",
  },
  pending: {
    label: "Pendente",
    color:
      "bg-gray-50 text-gray-600 border-gray-200 dark:bg-gray-900 dark:text-gray-400 dark:border-gray-700",
    icon: "?",
  },
  unverifiable: {
    label: "Inverificavel",
    color:
      "bg-yellow-50 text-yellow-700 border-yellow-200 dark:bg-yellow-950 dark:text-yellow-400 dark:border-yellow-800",
    icon: "~",
  },
};

export function ClaimReviewBadge({ status, size = "sm" }: ClaimReviewBadgeProps) {
  const config = statusConfig[status] || statusConfig.pending;

  const sizeClasses = size === "sm" ? "text-xs px-2 py-0.5" : "text-sm px-3 py-1";

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border font-medium ${config.color} ${sizeClasses}`}
    >
      <span className="font-bold">{config.icon}</span>
      {config.label}
    </span>
  );
}
