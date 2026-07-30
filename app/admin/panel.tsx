"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, Check, LockKeyhole, ShieldAlert } from "lucide-react";
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
    <div className="admin-layout">
      <section className="admin-login">
        <div className="admin-mark"><LockKeyhole size={20} aria-hidden="true" /></div>
        <p className="section-kicker">Private review surface</p>
        <h1>Review queue</h1>
        <p className="admin-lede">Approve or reject generated roast lines before they become part of the public voice.</p>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            setCredentials(draft);
          }}
          className="admin-form"
        >
          <label>
            <span>Username</span>
            <input value={draft.username} onChange={(event) => setDraft({ ...draft, username: event.target.value })} autoComplete="username" />
          </label>
          <label>
            <span>Password</span>
            <input type="password" value={draft.password} onChange={(event) => setDraft({ ...draft, password: event.target.value })} autoComplete="current-password" />
          </label>
          <button className="button primary" type="submit">Sign in <ArrowUpRight size={16} aria-hidden="true" /></button>
        </form>
        {reviews.isError ? <p className="error-text" role="alert">Invalid credentials or review service unavailable.</p> : null}
      </section>

      {credentials && reviews.data ? (
        <section className="admin-review-list">
          <div className="admin-list-heading"><span className="section-kicker">Pending lines</span><span>{reviews.data.length} open</span></div>
          {reviews.data.length === 0 ? <p className="empty-review"><Check size={16} aria-hidden="true" /> No pending reviews.</p> : null}
          {reviews.data.map((review) => (
            <article className="review-item" key={review.id}>
              <div className="review-meta"><span>Review #{review.id}</span><span>{review.reviewStatus}</span></div>
              <h2>{review.generatedContent.roastText}</h2>
              <label>
                <span>Rejection reason</span>
                <textarea
                  className="review-reason"
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
                <button className="button primary" type="button" onClick={() => approve.mutate(review.id)}><Check size={16} aria-hidden="true" /> Approve</button>
                <button
                  className="button"
                  type="button"
                  disabled={!rejectReasons[review.id]?.trim() || reject.isPending}
                  onClick={() => reject.mutate({ id: review.id, reason: rejectReasons[review.id].trim() })}
                >
                  <ShieldAlert size={16} aria-hidden="true" /> Reject
                </button>
              </div>
            </article>
          ))}
        </section>
      ) : null}
    </div>
  );
}
