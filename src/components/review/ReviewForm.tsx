"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/Button";

interface ReviewFormProps {
  reviewId: string;
  articleId: string;
}

export function ReviewForm({ reviewId, articleId }: ReviewFormProps) {
  const router = useRouter();
  const [status, setStatus] = useState<"approved" | "rejected" | "needs_revision">(
    "approved",
  );
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    const supabase = createClient();

    // Update review
    const { error: reviewError } = await supabase
      .from("hitl_reviews")
      .update({
        status,
        reviewer_notes: notes,
        resolved_at: new Date().toISOString(),
      })
      .eq("id", reviewId);

    if (reviewError) {
      setError(reviewError.message);
      setSubmitting(false);
      return;
    }

    // Update article status
    const articleStatus =
      status === "approved"
        ? "published"
        : status === "rejected"
          ? "rejected"
          : "review";

    const updateData: Record<string, unknown> = {
      status: articleStatus,
      review_notes: notes,
    };

    if (status === "approved") {
      updateData.published_at = new Date().toISOString();
    }

    const { error: articleError } = await supabase
      .from("articles")
      .update(updateData)
      .eq("id", articleId);

    if (articleError) {
      setError(articleError.message);
      setSubmitting(false);
      return;
    }

    setSuccess(true);
    setTimeout(() => {
      router.push("/review");
      router.refresh();
    }, 1000);
  }

  if (success) {
    return (
      <div
        className="rounded-xl border p-6 text-center"
        style={{
          borderColor: "color-mix(in srgb, var(--area-economia) 30%, transparent)",
          background: "color-mix(in srgb, var(--area-economia) 8%, transparent)",
        }}
      >
        <p
          className="text-lg font-semibold"
          style={{ color: "var(--area-economia)" }}
        >
          {status === "approved" ? "Artigo aprovado!" : status === "rejected" ? "Artigo rejeitado." : "Revisao enviada."}
        </p>
        <p
          className="mt-1 text-sm"
          style={{ color: "color-mix(in srgb, var(--area-economia) 70%, var(--text-primary))" }}
        >
          A redirecionar...
        </p>
      </div>
    );
  }

  const options = [
    {
      value: "approved" as const,
      label: "Aprovar",
      desc: "Publicar o artigo",
      color: "var(--area-economia)",
    },
    {
      value: "rejected" as const,
      label: "Rejeitar",
      desc: "Nao publicar",
      color: "var(--area-politica)",
    },
    {
      value: "needs_revision" as const,
      label: "Precisa Revisao",
      desc: "Devolver para edicao",
      color: "var(--area-energia)",
    },
  ];

  return (
    <form
      onSubmit={handleSubmit}
      className="glow-card space-y-4 p-6"
    >
      <h3
        className="text-lg font-semibold"
        style={{ color: "var(--text-primary)" }}
      >
        Decisao
      </h3>

      {/* Decision radio buttons */}
      <div className="space-y-2">
        {options.map((option) => (
          <label
            key={option.value}
            className="flex cursor-pointer items-center gap-3 rounded-xl border p-3 transition-all"
            style={{
              borderColor:
                status === option.value
                  ? "var(--accent)"
                  : "var(--border-primary)",
              background:
                status === option.value
                  ? "color-mix(in srgb, var(--accent) 8%, transparent)"
                  : "transparent",
            }}
          >
            <input
              type="radio"
              name="status"
              value={option.value}
              checked={status === option.value}
              onChange={(e) =>
                setStatus(e.target.value as typeof status)
              }
              className="h-4 w-4 accent-[var(--accent)]"
            />
            <div>
              <span
                className="text-sm font-medium"
                style={{ color: option.color }}
              >
                {option.label}
              </span>
              <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>
                {option.desc}
              </p>
            </div>
          </label>
        ))}
      </div>

      {/* Notes */}
      <div>
        <label
          htmlFor="notes"
          className="mb-1 block text-sm font-medium"
          style={{ color: "var(--text-secondary)" }}
        >
          Notas (opcional)
        </label>
        <textarea
          id="notes"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={4}
          placeholder="Observacoes sobre a decisao..."
          className="w-full rounded-xl border px-3 py-2 text-sm outline-none transition-colors focus:ring-1"
          style={{
            borderColor: "var(--border-primary)",
            background: "var(--surface-elevated)",
            color: "var(--text-primary)",
            // @ts-expect-error -- CSS custom property for focus ring
            "--tw-ring-color": "var(--accent)",
          }}
          onFocus={(e) => {
            e.currentTarget.style.borderColor = "var(--accent)";
          }}
          onBlur={(e) => {
            e.currentTarget.style.borderColor = "var(--border-primary)";
          }}
        />
      </div>

      {error && (
        <div
          className="rounded-lg border p-3 text-sm"
          style={{
            borderColor: "color-mix(in srgb, var(--area-politica) 30%, transparent)",
            background: "color-mix(in srgb, var(--area-politica) 8%, transparent)",
            color: "var(--area-politica)",
          }}
        >
          {error}
        </div>
      )}

      <Button
        type="submit"
        disabled={submitting}
        className="w-full"
      >
        {submitting ? "A submeter..." : "Submeter Decisao"}
      </Button>
    </form>
  );
}
