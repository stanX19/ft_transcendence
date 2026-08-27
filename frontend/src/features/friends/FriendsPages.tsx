import { useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, apiRequest } from "../../shared/api";
import type { PublicUser } from "../../shared/types";

interface FriendsResponse {
  items: PublicUser[];
}

interface SearchResponse {
  items: PublicUser[];
}

function Presence({ isOnline }: { isOnline: boolean }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-slate-500">
      <span aria-hidden="true" className={`h-2.5 w-2.5 rounded-full ${isOnline ? "bg-emerald-500" : "bg-slate-300"}`} />
      {isOnline ? "Online" : "Offline"}
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
      setActionError(error instanceof ApiError && error.status === 409 ? "That person is already a friend." : "We could not add that friend.");
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
      setActionError("We could not remove that friend. Please try again.");
    } finally {
      setActionId(null);
    }
  }

  return (
    <section className="mx-auto max-w-5xl">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-sky-700">Library community</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">Friends</h1>
        <p className="mt-3 max-w-2xl text-slate-600">Keep your reading circle close and see who is around.</p>
      </div>

      <form className="mt-8 flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:flex-row" onSubmit={submitSearch}>
        <label className="sr-only" htmlFor="friend-search">Find people to add</label>
        <input
          className="min-w-0 flex-1 rounded-xl border border-slate-300 px-4 py-3"
          id="friend-search"
          onChange={(event) => setSearchInput(event.target.value)}
          placeholder="Find people by display name"
          value={searchInput}
        />
        <button className="rounded-xl bg-slate-950 px-5 py-3 font-medium text-white" type="submit">Find people</button>
      </form>

      {search ? (
        <div className="mt-5 rounded-2xl border border-sky-100 bg-sky-50/60 p-5">
          <h2 className="font-semibold text-slate-950">People matching “{search}”</h2>
          {peopleQuery.isLoading ? <p className="mt-3 text-sm text-slate-600">Searching people…</p> : null}
          {peopleQuery.error ? <p className="mt-3 text-sm text-rose-700" role="alert">People search is unavailable right now.</p> : null}
          {!peopleQuery.isLoading && !peopleQuery.error && (peopleQuery.data?.items ?? []).length === 0 ? <p className="mt-3 text-sm text-slate-600">No matching people found.</p> : null}
          <div className="mt-3 space-y-2">
            {(peopleQuery.data?.items ?? []).filter((person) => !friendIds.has(person.id)).map((person) => (
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-white px-4 py-3" key={person.id}>
                <div>
                  <p className="font-medium text-slate-950">{person.display_name}</p>
                  <p className="text-sm text-slate-500">{person.bio || "No biography added yet."}</p>
                </div>
                <button className="rounded-lg border border-sky-200 px-3 py-2 text-sm font-medium text-sky-800 disabled:opacity-50" disabled={actionId === person.id} onClick={() => void addFriend(person.id)} type="button">
                  {actionId === person.id ? "Adding…" : "Add friend"}
                </button>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {actionError ? <p className="mt-4 text-sm text-rose-700" role="alert">{actionError}</p> : null}
      <div className="mt-8">
        <div className="mb-4 flex items-baseline justify-between gap-4">
          <h2 className="text-xl font-semibold text-slate-950">Your friends</h2>
          <span className="text-sm text-slate-500">Presence updates every 30 seconds</span>
        </div>
        {friendsQuery.isLoading ? <PageMessage title="Loading friends…" detail="Checking your reading circle." /> : null}
        {friendsQuery.error ? <PageMessage title="Friends unavailable" detail="We could not load your friends. Please try again." /> : null}
        {!friendsQuery.isLoading && !friendsQuery.error && friends.length === 0 ? <PageMessage title="No friends yet" detail="Search above to add someone from the library community." /> : null}
        {!friendsQuery.isLoading && !friendsQuery.error && friends.length > 0 ? (
          <div className="divide-y divide-slate-100 rounded-2xl border border-slate-200 bg-white shadow-sm">
            {friends.map((friend) => (
              <div className="flex flex-wrap items-center justify-between gap-4 p-5" key={friend.id}>
                <div>
                  <h3 className="font-semibold text-slate-950">{friend.display_name}</h3>
                  <p className="mt-1 text-sm text-slate-600">{friend.bio || "No biography added yet."}</p>
                </div>
                <div className="flex items-center gap-4">
                  <Presence isOnline={friend.is_online} />
                  <button className="text-sm font-medium text-rose-700 hover:text-rose-900 disabled:opacity-50" disabled={actionId === friend.id} onClick={() => void removeFriend(friend.id)} type="button">
                    {actionId === friend.id ? "Removing…" : "Remove"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </section>
  );
}
