"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { AdminCredentials } from "@/lib/api-client";
import { approveReview, fetchAdminReviews, rejectReview } from "@/lib/api-client";

/** Admin review panel using Basic credentials held only in React state. */
export function AdminPanel(): JSX.Element {
  const [draft, setDraft] = useState<AdminCredentials>({ username: "", password: "" });
  const [credentials, setCredentials] = useState<AdminCredentials | null>(null);
  const [rejectReasons, setRejectReasons] = useState<Record<number, string>>({});
  const queryClient = useQueryClient();
  const reviews = useQuery({
    queryKey: ["admin-reviews", credentials?.username],
    queryFn: () => fetchAdminReviews(credentials as AdminCredentials),
    enabled: credentials !== null,
    retry: false
  });
  const approve = useMutation({
    mutationFn: (id: number) => approveReview(credentials as AdminCredentials, id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-reviews"] })
  });
  const reject = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) => rejectReview(credentials as AdminCredentials, id, reason),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-reviews"] })
  });

  return (
    <div className="grid">
      <section className="panel admin-login">
        <h1>Review queue</h1>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            setCredentials(draft);
          }}
          className="admin-form"
        >
          <label>
            <span className="muted">Username</span>
            <input className="input" value={draft.username} onChange={(event) => setDraft({ ...draft, username: event.target.value })} autoComplete="username" />
          </label>
          <label>
            <span className="muted">Password</span>
            <input className="input" type="password" value={draft.password} onChange={(event) => setDraft({ ...draft, password: event.target.value })} autoComplete="current-password" />
          </label>
          <button className="button primary" type="submit">Sign in</button>
        </form>
        {reviews.isError ? <p className="error-text" role="alert">Invalid credentials or review service unavailable.</p> : null}
      </section>

      {credentials && reviews.data ? (
        <section className="grid">
          {reviews.data.length === 0 ? <p className="muted">No pending reviews.</p> : null}
          {reviews.data.map((review) => (
            <article className="panel review-item" key={review.id}>
              <h2>Review #{review.id}</h2>
              <p>{review.generatedContent.roastText}</p>
              <label>
                <span className="muted">Rejection reason</span>
                <textarea
                  className="input review-reason"
                  value={rejectReasons[review.id] ?? ""}
                  onChange={(event) => setRejectReasons({
                    ...rejectReasons,
                    [review.id]: event.target.value
                  })}
                  maxLength={1000}
                  placeholder="Explain what needs to change in the line bank."
                />
              </label>
              <div className="review-actions">
                <button className="button primary" type="button" onClick={() => approve.mutate(review.id)}>Approve</button>
                <button
                  className="button"
                  type="button"
                  disabled={!rejectReasons[review.id]?.trim() || reject.isPending}
                  onClick={() => reject.mutate({ id: review.id, reason: rejectReasons[review.id].trim() })}
                >
                  Reject
                </button>
              </div>
            </article>
          ))}
        </section>
      ) : null}
    </div>
  );
}
