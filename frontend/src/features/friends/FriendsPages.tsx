import { useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, apiRequest } from "../../shared/api";
import { Button, ErrorAlert, FormField, Input, PageHeader } from "../../shared/components";
import { useTranslation } from "../../shared/i18n";
import type { PublicUser } from "../../shared/types";

interface FriendsResponse {
  items: PublicUser[];
}

interface SearchResponse {
  items: PublicUser[];
}

function Presence({ isOnline }: { isOnline: boolean }) {
  const { t } = useTranslation();

  return (
    <span className="inline-flex items-center gap-2 text-sm text-slate-500">
      <span aria-hidden="true" className={`h-2.5 w-2.5 rounded-full ${isOnline ? "bg-emerald-500" : "bg-slate-300"}`} />
      {isOnline ? t("presence.online") : t("presence.offline")}
    </span>
  );
}

function PageMessage({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
      <h2 className="text-xl font-semibold text-slate-950">{title}</h2>
      <p className="mt-2 text-slate-600">{detail}</p>
    </div>
  );
}

export function FriendsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [actionId, setActionId] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const friendsQuery = useQuery({
    queryKey: ["friends"],
    queryFn: () => apiRequest<FriendsResponse>("/api/friends"),
    refetchInterval: 30_000,
    retry: false,
  });
  const peopleQuery = useQuery({
    queryKey: ["users", "find-friends", search],
    queryFn: () => apiRequest<SearchResponse>(`/api/users?query=${encodeURIComponent(search)}&page=1&page_size=20`),
    enabled: search.length > 0,
    retry: false,
  });

  const friends = friendsQuery.data?.items ?? [];
  const friendIds = new Set(friends.map((friend) => friend.id));

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSearch(searchInput.trim());
  }

  async function addFriend(userId: number) {
    setActionError(null);
    setActionId(userId);
    try {
      await apiRequest(`/api/friends/${userId}`, { method: "POST" });
      await queryClient.invalidateQueries({ queryKey: ["friends"] });
      await queryClient.invalidateQueries({ queryKey: ["users", "find-friends"] });
    } catch (error) {
      setActionError(error instanceof ApiError && error.status === 409 ? t("friends.alreadyFriend") : t("friends.addFailed"));
    } finally {
      setActionId(null);
    }
  }

  async function removeFriend(userId: number) {
    setActionError(null);
    setActionId(userId);
    try {
      await apiRequest(`/api/friends/${userId}`, { method: "DELETE" });
      await queryClient.invalidateQueries({ queryKey: ["friends"] });
    } catch {
      setActionError(t("friends.removeFailed"));
    } finally {
      setActionId(null);
    }
  }

  return (
    <section className="mx-auto max-w-5xl">
      <div>
        <PageHeader description={t("friends.description")} eyebrow={t("friends.eyebrow")} title={t("friends.title")} />
      </div>

      <form className="mt-8 flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:flex-row" onSubmit={submitSearch}>
        <FormField className="min-w-0 flex-1" htmlFor="friend-search" label={t("friends.searchLabel")}>
          <Input id="friend-search" onChange={(event) => setSearchInput(event.target.value)} placeholder={t("friends.searchPlaceholder")} value={searchInput} />
        </FormField>
        <Button className="self-end" type="submit">{t("friends.findPeople")}</Button>
      </form>

      {search ? (
        <div className="mt-5 rounded-2xl border border-sky-100 bg-sky-50/60 p-5">
          <h2 className="font-semibold text-slate-950">{t("friends.matching", { query: search })}</h2>
          {peopleQuery.isLoading ? <p className="mt-3 text-sm text-slate-600">{t("friends.searching")}</p> : null}
          {peopleQuery.error ? <ErrorAlert className="mt-3" message={t("friends.searchUnavailable")} /> : null}
          {!peopleQuery.isLoading && !peopleQuery.error && (peopleQuery.data?.items ?? []).length === 0 ? <p className="mt-3 text-sm text-slate-600">{t("friends.noMatching")}</p> : null}
          <div className="mt-3 space-y-2">
            {(peopleQuery.data?.items ?? []).filter((person) => !friendIds.has(person.id)).map((person) => (
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-white px-4 py-3" key={person.id}>
                <div>
                  <p className="font-medium text-slate-950">{person.display_name}</p>
                  <p className="text-sm text-slate-500">{person.bio || t("friends.biographyNone")}</p>
                </div>
                <Button disabled={actionId === person.id} loading={actionId === person.id} onClick={() => void addFriend(person.id)} size="sm" type="button" variant="secondary">
                  {actionId === person.id ? t("friends.adding") : t("friends.addFriend")}
                </Button>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {actionError ? <ErrorAlert className="mt-4" message={actionError} /> : null}
      <div className="mt-8">
        <div className="mb-4 flex items-baseline justify-between gap-4">
          <h2 className="text-xl font-semibold text-slate-950">{t("friends.yourFriends")}</h2>
          <span className="text-sm text-slate-500">{t("friends.presenceRefresh")}</span>
        </div>
        {friendsQuery.isLoading ? <PageMessage title={t("friends.loadingTitle")} detail={t("friends.loadingDetail")} /> : null}
        {friendsQuery.error ? <PageMessage title={t("friends.unavailableTitle")} detail={t("friends.unavailableDetail")} /> : null}
        {!friendsQuery.isLoading && !friendsQuery.error && friends.length === 0 ? <PageMessage title={t("friends.emptyTitle")} detail={t("friends.emptyDetail")} /> : null}
        {!friendsQuery.isLoading && !friendsQuery.error && friends.length > 0 ? (
          <div className="divide-y divide-slate-100 rounded-2xl border border-slate-200 bg-white shadow-sm">
            {friends.map((friend) => (
              <div className="flex flex-wrap items-center justify-between gap-4 p-5" key={friend.id}>
                <div>
                  <h3 className="font-semibold text-slate-950">{friend.display_name}</h3>
                  <p className="mt-1 text-sm text-slate-600">{friend.bio || t("friends.biographyNone")}</p>
                </div>
                <div className="flex items-center gap-4">
                  <Presence isOnline={friend.is_online} />
                  <Button className="text-sm" disabled={actionId === friend.id} loading={actionId === friend.id} onClick={() => void removeFriend(friend.id)} size="sm" type="button" variant="danger">
                    {actionId === friend.id ? t("friends.removing") : t("friends.remove")}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </section>
  );
}
