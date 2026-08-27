import { useEffect, useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { ApiError, apiRequest } from "../../shared/api";
import type { PublicUser, UserDirectoryResponse } from "../../shared/types";
import { useAuth } from "../auth";
import { FileUpload, type UploadedFile } from "../files";

function Presence({ isOnline }: { isOnline: boolean }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-slate-500">
      <span
        aria-hidden="true"
        className={`h-2.5 w-2.5 rounded-full ${isOnline ? "bg-emerald-500" : "bg-slate-300"}`}
      />
      {isOnline ? "Online" : "Offline"}
    </span>
  );
}

function ProfileCard({ user }: { user: PublicUser }) {
  return (
    <Link
      className="block rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-sky-300"
      to={`/users/${user.id}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="font-semibold text-slate-950">{user.display_name}</h2>
          <p className="mt-2 line-clamp-2 text-sm text-slate-600">
            {user.bio || "No biography added yet."}
          </p>
        </div>
        <Presence isOnline={user.is_online} />
      </div>
    </Link>
  );
}

export function OwnProfilePage() {
  const { user, setUser } = useAuth();
  const [displayName, setDisplayName] = useState(user?.display_name ?? "");
  const [bio, setBio] = useState(user?.bio ?? "");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [avatar, setAvatar] = useState<UploadedFile | null>(null);

  useEffect(() => {
    if (user) {
      setDisplayName(user.display_name);
      setBio(user.bio);
    }
  }, [user]);

  if (!user) {
    return null;
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!event.currentTarget.checkValidity()) {
      event.currentTarget.reportValidity();
      return;
    }
    setMessage(null);
    setError(null);
    setIsSaving(true);
    try {
      const payload = await apiRequest<{ user?: typeof user }>("/api/users/me", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ display_name: displayName.trim(), bio: bio.trim() }),
      });
      if (payload.user) {
        setUser(payload.user);
      }
      setMessage("Your profile is updated.");
    } catch (saveError) {
      setError(
        saveError instanceof ApiError
          ? saveError.message
          : "We could not save your profile. Please try again.",
      );
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section className="mx-auto max-w-3xl">
      <div className="mb-8">
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-sky-700">Your account</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">Your profile</h1>
        <p className="mt-3 text-slate-600">
          Keep the public details that help other readers recognize you.
        </p>
      </div>
      <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="flex h-16 w-16 items-center justify-center overflow-hidden rounded-full bg-sky-100 text-xl font-semibold text-sky-800">
              {avatar ? <img alt="Your avatar" className="h-full w-full object-cover" src={avatar.url} /> : user.display_name.slice(0, 2).toUpperCase()}
            </div>
            <div>
            <p className="font-semibold text-slate-950">{user.email}</p>
            <p className="mt-1 text-sm text-slate-500">Role: {user.role}</p>
            </div>
          </div>
          <Presence isOnline={user.is_online} />
        </div>
        <div className="mb-8 border-b border-slate-100 pb-8">
          <FileUpload
            accept="image/jpeg,image/png,image/webp"
            endpoint="/api/users/me/avatar"
            helper="JPEG, PNG, or WebP. Maximum 10 MB."
            label="Profile avatar"
            onUploaded={setAvatar}
          />
          {avatar ? (
            <button className="mt-3 text-sm font-medium text-rose-700 hover:text-rose-900" onClick={() => { void apiRequest("/api/users/me/avatar", { method: "DELETE" }).then(() => setAvatar(null)).catch(() => setError("We could not remove your avatar.")); }} type="button">
              Remove avatar
            </button>
          ) : null}
        </div>
        <form className="space-y-5" onSubmit={submit}>
          <div>
            <label className="text-sm font-medium text-slate-800" htmlFor="profile-display-name">
              Display name
            </label>
            <input
              className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3"
              id="profile-display-name"
              minLength={2}
              onChange={(event) => setDisplayName(event.target.value)}
              required
              value={displayName}
            />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-800" htmlFor="profile-bio">
              Bio
            </label>
            <textarea
              className="mt-2 min-h-32 w-full rounded-xl border border-slate-300 px-4 py-3"
              id="profile-bio"
              maxLength={2000}
              onChange={(event) => setBio(event.target.value)}
              value={bio}
            />
          </div>
          {message ? <p className="text-sm text-emerald-700" role="status">{message}</p> : null}
          {error ? <p className="text-sm text-rose-700" role="alert">{error}</p> : null}
          <button
            className="rounded-xl bg-slate-950 px-5 py-3 font-medium text-white disabled:opacity-60"
            disabled={isSaving}
            type="submit"
          >
            {isSaving ? "Saving…" : "Save profile"}
          </button>
        </form>
      </div>
    </section>
  );
}

export function PublicProfilePage() {
  const { userId } = useParams();
  const profileQuery = useQuery({
    queryKey: ["users", userId],
    queryFn: () => apiRequest<{ user?: PublicUser }>(`/api/users/${userId}`),
    enabled: Boolean(userId),
    retry: false,
  });
  const user = profileQuery.data?.user;

  if (profileQuery.isLoading) {
    return <PageMessage title="Loading profile…" detail="Fetching the public profile." />;
  }
  if (profileQuery.error) {
    const notFound = profileQuery.error instanceof ApiError && profileQuery.error.status === 404;
    return (
      <PageMessage
        title={notFound ? "Profile not found" : "Profile unavailable"}
        detail={notFound ? "This reader profile does not exist." : "Please try again in a moment."}
      />
    );
  }
  if (!user) {
    return <PageMessage title="Profile unavailable" detail="No public profile data was returned." />;
  }

  return (
    <section className="mx-auto max-w-3xl">
      <Link className="text-sm font-medium text-sky-700 hover:text-sky-900" to="/people">
        ← Back to people
      </Link>
      <div className="mt-6 rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.18em] text-sky-700">Reader profile</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">
              {user.display_name}
            </h1>
          </div>
          <Presence isOnline={user.is_online} />
        </div>
        <div className="mt-8 border-t border-slate-100 pt-6">
          <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-slate-500">About</h2>
          <p className="mt-3 whitespace-pre-wrap leading-7 text-slate-700">
            {user.bio || "This reader has not added a biography yet."}
          </p>
        </div>
      </div>
    </section>
  );
}

export function PeoplePage() {
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const peopleQuery = useQuery({
    queryKey: ["users", "directory", search],
    queryFn: () =>
      apiRequest<UserDirectoryResponse>(
        `/api/users?query=${encodeURIComponent(search)}&page=1&page_size=20`,
      ),
    retry: false,
    refetchInterval: 30_000,
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSearch(query.trim());
  }

  return (
    <section className="mx-auto max-w-5xl">
      <div className="flex flex-wrap items-end justify-between gap-5">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.18em] text-sky-700">Library community</p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">Find people</h1>
          <p className="mt-3 text-slate-600">Search public reader profiles by display name.</p>
        </div>
        <Link className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700" to="/profile">
          Edit your profile
        </Link>
      </div>
      <form className="mt-8 flex flex-col gap-3 sm:flex-row" onSubmit={submit}>
        <label className="sr-only" htmlFor="people-search">Search people</label>
        <input
          className="min-w-0 flex-1 rounded-xl border border-slate-300 bg-white px-4 py-3"
          id="people-search"
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search display names"
          value={query}
        />
        <button className="rounded-xl bg-slate-950 px-5 py-3 font-medium text-white" type="submit">
          Search
        </button>
      </form>
      {peopleQuery.isLoading ? (
        <PageMessage title="Loading people…" detail="Finding public reader profiles." />
      ) : peopleQuery.error ? (
        <PageMessage title="People directory unavailable" detail="Please try again in a moment." />
      ) : (
        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          {(peopleQuery.data?.items ?? []).map((person) => (
            <ProfileCard key={person.id} user={person} />
          ))}
          {peopleQuery.data?.items.length === 0 ? (
            <p className="rounded-2xl border border-dashed border-slate-300 p-8 text-slate-600 sm:col-span-2">
              No public profiles matched that search.
            </p>
          ) : null}
        </div>
      )}
    </section>
  );
}

function PageMessage({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="mx-auto mt-8 max-w-3xl rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
      <h1 className="text-xl font-semibold text-slate-950">{title}</h1>
      <p className="mt-2 text-slate-600">{detail}</p>
    </div>
  );
}
