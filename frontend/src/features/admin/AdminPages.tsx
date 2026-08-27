import { useState, type ChangeEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, apiRequest } from "../../shared/api";
import { PageHeader } from "../../shared/components";
import { useTranslation } from "../../shared/i18n";
import type { UserRole } from "../../shared/types";
import { useAuth } from "../auth";

interface AdminUser {
  id: number;
  email: string;
  display_name: string;
  bio: string;
  role: UserRole | string;
  is_online: boolean;
  created_at: string;
}

interface AdminUsersResponse {
  items: AdminUser[];
  page: number;
  page_size: number;
  total: number;
}

function PageMessage({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
      <h1 className="text-xl font-semibold text-slate-950">{title}</h1>
      <p className="mt-2 text-slate-600">{detail}</p>
    </div>
  );
}

export function AdminUsersPage() {
  const { user } = useAuth();
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [query, setQuery] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const usersQuery = useQuery({
    queryKey: ["admin", "users", query],
    queryFn: () => apiRequest<AdminUsersResponse>(`/api/admin/users?query=${encodeURIComponent(query)}&page=1&page_size=20`),
    enabled: user?.role === "ADMIN",
    retry: false,
  });

  if (user?.role !== "ADMIN") {
    return <PageMessage title={t("admin.accessTitle")} detail={t("admin.accessDetail")} />;
  }

  function beginEdit(target: AdminUser) {
    setEditingId(target.id);
    setEditName(target.display_name);
    setError(null);
    setMessage(null);
  }

  async function saveUser(target: AdminUser) {
    setError(null);
    setMessage(null);
    setBusyId(target.id);
    try {
      await apiRequest(`/api/admin/users/${target.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ display_name: editName.trim() }),
      });
      setEditingId(null);
      setMessage(t("admin.userUpdated"));
      await queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    } catch (saveError) {
      setError(t("admin.updateFailed"));
    } finally {
      setBusyId(null);
    }
  }

  async function changeRole(target: AdminUser, event: ChangeEvent<HTMLSelectElement>) {
    const role = event.target.value;
    setError(null);
    setMessage(null);
    setBusyId(target.id);
    try {
      await apiRequest(`/api/admin/users/${target.id}/role`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role }),
      });
      setMessage(t("admin.roleUpdated"));
      await queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    } catch (roleError) {
      setError(roleError instanceof ApiError && roleError.status === 409 ? t("admin.roleBlocked") : t("admin.updateFailed"));
      await queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    } finally {
      setBusyId(null);
    }
  }

  async function deleteUser(target: AdminUser) {
    if (target.id === user.id) {
      setError(t("admin.ownDelete"));
      return;
    }
    setError(null);
    setMessage(null);
    setBusyId(target.id);
    try {
      await apiRequest(`/api/admin/users/${target.id}`, { method: "DELETE" });
      setMessage(t("admin.userDeleted"));
      await queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    } catch (deleteError) {
      setError(deleteError instanceof ApiError && deleteError.status === 409 ? t("admin.deleteBlocked") : t("admin.deleteFailed"));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="mx-auto max-w-6xl">
      <PageHeader description={t("admin.description")} eyebrow={t("admin.eyebrow")} title={t("admin.title")} />
      <label className="mt-8 block max-w-xl text-sm font-medium text-slate-800" htmlFor="admin-user-search">
        {t("admin.searchLabel")}
        <input className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3" id="admin-user-search" onChange={(event) => setQuery(event.target.value)} placeholder={t("admin.searchPlaceholder")} value={query} />
      </label>
      {message ? <p className="mt-4 text-sm text-emerald-700" role="status">{message}</p> : null}
      {error ? <p className="mt-4 text-sm text-rose-700" role="alert">{error}</p> : null}
      <div className="mt-8">
        {usersQuery.isLoading ? <PageMessage title={t("admin.loadingTitle")} detail={t("admin.loadingDetail")} /> : null}
        {usersQuery.error ? <PageMessage title={t("admin.unavailableTitle")} detail={t("admin.unavailableDetail")} /> : null}
        {!usersQuery.isLoading && !usersQuery.error && (usersQuery.data?.items ?? []).length === 0 ? <PageMessage title={t("admin.emptyTitle")} detail={t("admin.emptyDetail")} /> : null}
        {!usersQuery.isLoading && !usersQuery.error && (usersQuery.data?.items ?? []).length > 0 ? (
          <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-100 bg-slate-50 text-xs uppercase tracking-[0.12em] text-slate-500">
                <tr><th className="px-5 py-4 font-medium">{t("admin.user")}</th><th className="px-5 py-4 font-medium">{t("admin.role")}</th><th className="px-5 py-4 font-medium">{t("admin.presence")}</th><th className="px-5 py-4 font-medium">{t("admin.actions")}</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {(usersQuery.data?.items ?? []).map((target) => (
                  <tr key={target.id}>
                    <td className="px-5 py-5 align-top">
                      {editingId === target.id ? (
                        <div className="flex flex-wrap gap-2">
                          <input aria-label={t("admin.displayNameFor", { email: target.email })} className="rounded-lg border border-slate-300 px-3 py-2" onChange={(event) => setEditName(event.target.value)} value={editName} />
                          <button className="rounded-lg bg-slate-950 px-3 py-2 font-medium text-white disabled:opacity-50" disabled={busyId === target.id || editName.trim().length < 2} onClick={() => void saveUser(target)} type="button">{t("admin.save")}</button>
                          <button className="rounded-lg border border-slate-300 px-3 py-2" onClick={() => setEditingId(null)} type="button">{t("admin.cancel")}</button>
                        </div>
                      ) : (
                        <>
                          <p className="font-medium text-slate-950">{target.display_name}</p>
                          <p className="mt-1 text-slate-500">{target.email}</p>
                        </>
                      )}
                    </td>
                    <td className="px-5 py-5 align-top">
                      <label className="sr-only" htmlFor={`role-${target.id}`}>{t("admin.roleFor", { email: target.email })}</label>
                      <select className="rounded-lg border border-slate-300 bg-white px-3 py-2" disabled={busyId === target.id || target.id === user.id} id={`role-${target.id}`} onChange={(event) => void changeRole(target, event)} value={target.role}>
                        <option value="MEMBER">{t("role.member")}</option>
                        <option value="LIBRARIAN">{t("role.librarian")}</option>
                        <option value="ADMIN">{t("role.admin")}</option>
                      </select>
                    </td>
                    <td className="px-5 py-5 align-top text-slate-600">{target.is_online ? t("presence.online") : t("presence.offline")}</td>
                    <td className="px-5 py-5 align-top">
                      <div className="flex flex-wrap gap-3">
                        <button className="font-medium text-sky-800 hover:text-sky-950 disabled:opacity-50" disabled={busyId === target.id} onClick={() => beginEdit(target)} type="button">{t("admin.edit")}</button>
                        <button className="font-medium text-rose-700 hover:text-rose-900 disabled:opacity-50" disabled={busyId === target.id || target.id === user.id} onClick={() => void deleteUser(target)} type="button">{t("admin.delete")}</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>
    </section>
  );
}
