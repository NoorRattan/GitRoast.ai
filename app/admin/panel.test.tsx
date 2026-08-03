import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AdminPanel } from "./panel";

const fetchAdminReviews = vi.fn();
const approveReview = vi.fn();
const rejectReview = vi.fn();

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return {
    ...actual,
    fetchAdminReviews: (...args: unknown[]) => fetchAdminReviews(...args),
    approveReview: (...args: unknown[]) => approveReview(...args),
    rejectReview: (...args: unknown[]) => rejectReview(...args)
  };
});

function renderPanel(): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><AdminPanel /></QueryClientProvider>);
}

describe("AdminPanel", () => {
  it("keeps credentials in memory and reaches the protected review list", async () => {
    fetchAdminReviews.mockResolvedValueOnce([]);

    renderPanel();
    fireEvent.change(screen.getByLabelText(/Username/), { target: { value: "admin" } });
    fireEvent.change(screen.getByLabelText(/Password/), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => expect(fetchAdminReviews).toHaveBeenCalledWith({ username: "admin", password: "secret" }));
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
    expect(document.cookie).toBe("");
  });

  it("shows a clear invalid-credentials state", async () => {
    fetchAdminReviews.mockRejectedValueOnce(new Error("unauthorized"));

    renderPanel();
    fireEvent.change(screen.getByLabelText(/Username/), { target: { value: "admin" } });
    fireEvent.change(screen.getByLabelText(/Password/), { target: { value: "bad" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid credentials");
  });

  it("submits the reviewer's own rejection reason", async () => {
    fetchAdminReviews.mockResolvedValue([
      {
        id: 9,
        auditId: 3,
        generatedContent: {
          roastText: "Too generic",
          strengths: ["a", "b", "c"],
          improvementAreas: ["x", "y", "z"],
          roadmap: []
        },
        reviewStatus: "pending",
        reason: null,
        createdAt: "2026-07-28T00:00:00Z"
      }
    ]);
    rejectReview.mockResolvedValueOnce(undefined);

    renderPanel();
    fireEvent.change(screen.getByLabelText(/Username/), { target: { value: "admin" } });
    fireEvent.change(screen.getByLabelText(/Password/), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await screen.findByText("Review #9");

    fireEvent.change(screen.getByLabelText("Rejection reason"), {
      target: { value: "The evidence line repeats the verdict." }
    });
    fireEvent.click(screen.getByRole("button", { name: "Reject" }));

    await waitFor(() => expect(rejectReview).toHaveBeenCalledWith(
      { username: "admin", password: "secret" },
      9,
      "The evidence line repeats the verdict."
    ));
  });
});
