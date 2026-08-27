import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { ApiError, apiRequest } from "../../shared/api";
import { Button, Card, EmptyState, ErrorAlert, LinkButton, PageHeader } from "../../shared/components";
import { useTranslation } from "../../shared/i18n";

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

function formatDate(value: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(new Date(value));
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
  const { locale, t } = useTranslation();

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
            {isReturning ? t("loan.returning") : t("loan.returnBook")}
          </button>
        ) : (
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">{t("loan.returned")}</span>
        )}
      </div>
      <dl className="mt-5 grid gap-2 text-sm text-slate-600 sm:grid-cols-2">
        <div><dt className="text-slate-500">{t("loan.borrowed")}</dt><dd className="font-medium text-slate-950">{formatDate(loan.borrowed_at, locale)}</dd></div>
        <div><dt className="text-slate-500">{t("loan.due")}</dt><dd className="font-medium text-slate-950">{formatDate(loan.due_at, locale)}</dd></div>
        {loan.returned_at ? <div><dt className="text-slate-500">{t("loan.returnedAt")}</dt><dd className="font-medium text-slate-950">{formatDate(loan.returned_at, locale)}</dd></div> : null}
      </dl>
    </article>
  );
}

export function LoansPage() {
  const { t } = useTranslation();
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
          ? t("loan.onlyOwnError")
          : t("loan.returnError"),
      );
    } finally {
      setReturningId(null);
    }
  }

  if (loansQuery.isLoading) return <LoansMessage title={t("loan.loadingTitle")} detail={t("loan.loadingDetail")} />;
  if (loansQuery.error) return <LoansMessage title={t("loan.unavailableTitle")} detail={t("loan.unavailableDetail")} />;
  if (!loansQuery.data) return <LoansMessage title={t("loan.unavailableTitle")} detail={t("loan.noDataDetail")} />;

  const { active, history } = loansQuery.data;
  return (
    <section className="mx-auto max-w-4xl">
      <PageHeader description={t("loan.description")} eyebrow={t("loan.eyebrow")} title={t("loan.title")} />
      {returnError ? <ErrorAlert className="mt-6" message={returnError} /> : null}

      <div className="mt-10">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-xl font-semibold text-slate-950">{t("loan.active")}</h2>
          <span className="text-sm text-slate-500">{t(active.length === 1 ? "loan.bookCount.one" : "loan.bookCount.other", { count: active.length })}</span>
        </div>
        {active.length > 0 ? (
          <div className="mt-4 space-y-4">
            {active.map((loan) => <LoanCard isReturning={returningId === loan.id} key={loan.id} loan={loan} onReturn={returnBook} />)}
          </div>
        ) : (
          <EmptyState action={<LinkButton size="sm" to="/books">{t("loan.browseCatalog")}</LinkButton>} detail={t("loan.noActivePrefix")} title={t("loan.active")} />
        )}
      </div>

      <div className="mt-12">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-xl font-semibold text-slate-950">{t("loan.history")}</h2>
          <span className="text-sm text-slate-500">{t(history.length === 1 ? "loan.bookCount.one" : "loan.bookCount.other", { count: history.length })}</span>
        </div>
        {history.length > 0 ? (
          <div className="mt-4 space-y-4">
            {history.map((loan) => <LoanCard key={loan.id} loan={loan} />)}
          </div>
        ) : (
          <EmptyState detail={t("loan.historyEmpty")} title={t("loan.history")} />
        )}
      </div>
    </section>
  );
}
