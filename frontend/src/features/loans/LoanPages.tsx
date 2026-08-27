import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { ApiError, apiRequest } from "../../shared/api";

interface Loan {
  id: number;
  user_id: number;
  book_id: number;
  book_title: string;
  book_author: string;
  borrowed_at: string;
  due_at: string;
  returned_at: string | null;
}

interface MyLoansResponse {
  active: Loan[];
  history: Loan[];
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(value));
}

function LoansMessage({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="mx-auto max-w-3xl rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
      <h1 className="text-xl font-semibold text-slate-950">{title}</h1>
      <p className="mt-2 text-slate-600">{detail}</p>
    </div>
  );
}

function LoanCard({
  loan,
  onReturn,
  isReturning,
}: {
  loan: Loan;
  onReturn?: (loanId: number) => void;
  isReturning?: boolean;
}) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link className="text-lg font-semibold text-slate-950 hover:text-sky-700" to={`/books/${loan.book_id}`}>
            {loan.book_title}
          </Link>
          <p className="mt-1 text-sm text-slate-600">{loan.book_author}</p>
        </div>
        {onReturn ? (
          <button
            className="rounded-xl bg-slate-950 px-3 py-2 text-sm font-medium text-white disabled:opacity-60"
            disabled={isReturning}
            onClick={() => onReturn(loan.id)}
            type="button"
          >
            {isReturning ? "Returning…" : "Return book"}
          </button>
        ) : (
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">Returned</span>
        )}
      </div>
      <dl className="mt-5 grid gap-2 text-sm text-slate-600 sm:grid-cols-2">
        <div><dt className="text-slate-500">Borrowed</dt><dd className="font-medium text-slate-950">{formatDate(loan.borrowed_at)}</dd></div>
        <div><dt className="text-slate-500">Due</dt><dd className="font-medium text-slate-950">{formatDate(loan.due_at)}</dd></div>
        {loan.returned_at ? <div><dt className="text-slate-500">Returned</dt><dd className="font-medium text-slate-950">{formatDate(loan.returned_at)}</dd></div> : null}
      </dl>
    </article>
  );
}

export function LoansPage() {
  const queryClient = useQueryClient();
  const [returningId, setReturningId] = useState<number | null>(null);
  const [returnError, setReturnError] = useState<string | null>(null);
  const loansQuery = useQuery({
    queryKey: ["loans", "me"],
    queryFn: () => apiRequest<MyLoansResponse>("/api/loans/me"),
    refetchInterval: 30_000,
    retry: false,
  });

  async function returnBook(loanId: number) {
    setReturningId(loanId);
    setReturnError(null);
    try {
      await apiRequest(`/api/loans/${loanId}/return`, { method: "POST" });
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["loans", "me"] }),
        queryClient.invalidateQueries({ queryKey: ["books"] }),
      ]);
    } catch (error) {
      setReturnError(
        error instanceof ApiError && error.status === 403
          ? "You can only return your own loans."
          : "We could not return this book. Please try again.",
      );
    } finally {
      setReturningId(null);
    }
  }

  if (loansQuery.isLoading) return <LoansMessage title="Loading your loans…" detail="Fetching your current borrowing history." />;
  if (loansQuery.error) return <LoansMessage title="Loans unavailable" detail="We could not load your loans. Please try again." />;
  if (!loansQuery.data) return <LoansMessage title="Loans unavailable" detail="No loan data was returned." />;

  const { active, history } = loansQuery.data;
  return (
    <section className="mx-auto max-w-4xl">
      <p className="text-sm font-medium uppercase tracking-[0.18em] text-sky-700">Your library account</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">My loans</h1>
      <p className="mt-3 max-w-2xl text-slate-600">Keep track of what you have borrowed and when it is due.</p>
      {returnError ? <p className="mt-6 rounded-xl bg-rose-50 p-3 text-sm text-rose-700" role="alert">{returnError}</p> : null}

      <div className="mt-10">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-xl font-semibold text-slate-950">Active</h2>
          <span className="text-sm text-slate-500">{active.length} {active.length === 1 ? "book" : "books"}</span>
        </div>
        {active.length > 0 ? (
          <div className="mt-4 space-y-4">
            {active.map((loan) => <LoanCard isReturning={returningId === loan.id} key={loan.id} loan={loan} onReturn={returnBook} />)}
          </div>
        ) : (
          <div className="mt-4 rounded-2xl border border-dashed border-slate-300 bg-white p-6 text-slate-600">You have no active loans. <Link className="font-medium text-sky-700" to="/books">Browse the catalog</Link>.</div>
        )}
      </div>

      <div className="mt-12">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-xl font-semibold text-slate-950">History</h2>
          <span className="text-sm text-slate-500">{history.length} {history.length === 1 ? "book" : "books"}</span>
        </div>
        {history.length > 0 ? (
          <div className="mt-4 space-y-4">
            {history.map((loan) => <LoanCard key={loan.id} loan={loan} />)}
          </div>
        ) : (
          <div className="mt-4 rounded-2xl border border-dashed border-slate-300 bg-white p-6 text-slate-600">Returned books will appear here.</div>
        )}
      </div>
    </section>
  );
}
