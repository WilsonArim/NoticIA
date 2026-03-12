"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

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
      <div className="rounded-xl border border-green-200 bg-green-50 p-6 text-center dark:border-green-800 dark:bg-green-950">
        <p className="text-lg font-semibold text-green-700 dark:text-green-400">
          {status === "approved" ? "Artigo aprovado!" : status === "rejected" ? "Artigo rejeitado." : "Revisao enviada."}
        </p>
        <p className="mt-1 text-sm text-green-600 dark:text-green-500">
          A redirecionar...
        </p>
      </div>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-4 rounded-xl border border-gray-200 p-6 dark:border-gray-800"
    >
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
        Decisao
      </h3>

      {/* Decision radio buttons */}
      <div className="space-y-2">
        {[
          {
            value: "approved" as const,
            label: "Aprovar",
            desc: "Publicar o artigo",
            color: "text-green-600 dark:text-green-400",
          },
          {
            value: "rejected" as const,
            label: "Rejeitar",
            desc: "Nao publicar",
            color: "text-red-600 dark:text-red-400",
          },
          {
            value: "needs_revision" as const,
            label: "Precisa Revisao",
            desc: "Devolver para edicao",
            color: "text-orange-600 dark:text-orange-400",
          },
        ].map((option) => (
          <label
            key={option.value}
            className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 transition-all ${
              status === option.value
                ? "border-blue-500 bg-blue-50 dark:border-blue-400 dark:bg-blue-950"
                : "border-gray-200 hover:border-gray-300 dark:border-gray-700 dark:hover:border-gray-600"
            }`}
          >
            <input
              type="radio"
              name="status"
              value={option.value}
              checked={status === option.value}
              onChange={(e) =>
                setStatus(e.target.value as typeof status)
              }
              className="h-4 w-4 text-blue-600"
            />
            <div>
              <span className={`text-sm font-medium ${option.color}`}>
                {option.label}
              </span>
              <p className="text-xs text-gray-400">{option.desc}</p>
            </div>
          </label>
        ))}
      </div>

      {/* Notes */}
      <div>
        <label
          htmlFor="notes"
          className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
        >
          Notas (opcional)
        </label>
        <textarea
          id="notes"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={4}
          placeholder="Observacoes sobre a decisao..."
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-800"
        />
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-600 dark:border-red-800 dark:bg-red-950 dark:text-red-400">
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {submitting ? "A submeter..." : "Submeter Decisao"}
      </button>
    </form>
  );
}
