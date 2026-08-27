import { useEffect, useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { ApiError, apiRequest } from "../../shared/api";
import { Button, Card, EmptyState, ErrorAlert, FormField, Input, LinkButton, LoadingState, Notice, PageHeader, TextArea } from "../../shared/components";
import { type Translator, useTranslation } from "../../shared/i18n";
import type { PublicUser, UserDirectoryResponse } from "../../shared/types";
import { useAuth } from "../auth";
import { FileUpload, type UploadedFile } from "../files";

function roleLabel(role: string, t: Translator): string {
  if (role === "ADMIN") return t("role.admin");
  if (role === "LIBRARIAN") return t("role.librarian");
  return t("role.member");
}

function Presence({ isOnline }: { isOnline: boolean }) {
  const { t } = useTranslation();

  return (
    <span className="inline-flex items-center gap-2 text-sm text-slate-500">
      <span
        aria-hidden="true"
        className={`h-2.5 w-2.5 rounded-full ${isOnline ? "bg-emerald-500" : "bg-slate-300"}`}
      />
      {isOnline ? t("presence.online") : t("presence.offline")}
    </span>
  );
}

function ProfileCard({ user }: { user: PublicUser }) {
  const { t } = useTranslation();

  return (
    <Link
      className="block rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-sky-300"
      to={`/users/${user.id}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="font-semibold text-slate-950">{user.display_name}</h2>
          <p className="mt-2 line-clamp-2 text-sm text-slate-600">
            {user.bio || t("friends.biographyNone")}
          </p>
        </div>
        <Presence isOnline={user.is_online} />
      </div>
    </Link>
  );
}

export function OwnProfilePage() {
  const { user, setUser } = useAuth();
  const { t } = useTranslation();
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
      setMessage(t("profile.updated"));
    } catch (saveError) {
      setError(t("profile.saveFailed"));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section className="mx-auto max-w-3xl">
      <PageHeader description={t("profile.description")} eyebrow={t("profile.eyebrow")} title={t("profile.title")} />
      <Card className="mt-8 p-8">
        <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="flex h-16 w-16 items-center justify-center overflow-hidden rounded-full bg-sky-100 text-xl font-semibold text-sky-800">
              {avatar ? <img alt={t("profile.avatarAlt")} className="h-full w-full object-cover" src={avatar.url} /> : user.display_name.slice(0, 2).toUpperCase()}
            </div>
            <div>
            <p className="font-semibold text-slate-950">{user.email}</p>
            <p className="mt-1 text-sm text-slate-500">{t("profile.role", { role: roleLabel(user.role, t) })}</p>
            </div>
          </div>
          <Presence isOnline={user.is_online} />
        </div>
        <div className="mb-8 border-b border-slate-100 pb-8">
          <FileUpload
            accept="image/jpeg,image/png,image/webp"
            endpoint="/api/users/me/avatar"
            helper={t("profile.avatarHelper")}
            label={t("profile.avatarLabel")}
            onUploaded={setAvatar}
          />
          {avatar ? (
            <Button className="mt-3" onClick={() => { void apiRequest("/api/users/me/avatar", { method: "DELETE" }).then(() => setAvatar(null)).catch(() => setError(t("profile.removeFailed"))); }} size="sm" type="button" variant="danger">
              {t("profile.removeAvatar")}
            </Button>
          ) : null}
        </div>
        <form className="space-y-5" onSubmit={submit}>
          <FormField htmlFor="profile-display-name" label={t("profile.displayName")}>
            <Input
              id="profile-display-name"
              minLength={2}
              onChange={(event) => setDisplayName(event.target.value)}
              required
              value={displayName}
            />
          </FormField>
          <FormField htmlFor="profile-bio" label={t("profile.bio")}>
            <TextArea
              className="min-h-32"
              id="profile-bio"
              maxLength={2000}
              onChange={(event) => setBio(event.target.value)}
              value={bio}
            />
          </FormField>
          {message ? <Notice message={message} /> : null}
          {error ? <ErrorAlert message={error} /> : null}
          <Button
            disabled={isSaving}
            loading={isSaving}
            type="submit"
          >
            {isSaving ? t("profile.saving") : t("profile.save")}
          </Button>
        </form>
      </Card>
    </section>
  );
}

export function PublicProfilePage() {
  const { userId } = useParams();
  const { t } = useTranslation();
  const profileQuery = useQuery({
    queryKey: ["users", userId],
    queryFn: () => apiRequest<{ user?: PublicUser }>(`/api/users/${userId}`),
    enabled: Boolean(userId),
    retry: false,
  });
  const user = profileQuery.data?.user;

  if (profileQuery.isLoading) {
    return <LoadingState title={t("profile.loadingTitle")} detail={t("profile.loadingDetail")} />;
  }
  if (profileQuery.error) {
    const notFound = profileQuery.error instanceof ApiError && profileQuery.error.status === 404;
    return (
      <PageMessage
        title={notFound ? t("profile.notFoundTitle") : t("profile.unavailableTitle")}
        detail={notFound ? t("profile.notFoundDetail") : t("profile.unavailableDetail")}
      />
    );
  }
  if (!user) {
    return <PageMessage title={t("profile.unavailableTitle")} detail={t("profile.noDataDetail")} />;
  }

  return (
    <section className="mx-auto max-w-3xl">
      <LinkButton size="sm" to="/people" variant="ghost">{t("profile.back")}</LinkButton>
      <Card className="mt-6 p-8">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.18em] text-sky-700">{t("profile.readerEyebrow")}</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">
              {user.display_name}
            </h1>
          </div>
          <Presence isOnline={user.is_online} />
        </div>
        <div className="mt-8 border-t border-slate-100 pt-6">
          <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-slate-500">{t("profile.about")}</h2>
          <p className="mt-3 whitespace-pre-wrap leading-7 text-slate-700">
            {user.bio || t("profile.publicBioNone")}
          </p>
        </div>
      </Card>
    </section>
  );
}

export function PeoplePage() {
  const { t } = useTranslation();
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
      <PageHeader
        actions={<LinkButton size="sm" to="/profile" variant="secondary">{t("people.editProfile")}</LinkButton>}
        description={t("people.description")}
        eyebrow={t("people.eyebrow")}
        title={t("people.title")}
      />
      <form className="mt-8 flex flex-col gap-3 sm:flex-row" onSubmit={submit}>
        <FormField className="min-w-0 flex-1" htmlFor="people-search" label={t("people.searchLabel")}>
          <Input id="people-search" onChange={(event) => setQuery(event.target.value)} placeholder={t("people.searchPlaceholder")} value={query} />
        </FormField>
        <Button className="self-end" type="submit">{t("people.search")}</Button>
      </form>
      {peopleQuery.isLoading ? (
        <LoadingState title={t("people.loadingTitle")} detail={t("people.loadingDetail")} />
      ) : peopleQuery.error ? (
        <PageMessage title={t("people.unavailableTitle")} detail={t("people.unavailableDetail")} />
      ) : (
        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          {(peopleQuery.data?.items ?? []).map((person) => (
            <ProfileCard key={person.id} user={person} />
          ))}
          {peopleQuery.data?.items.length === 0 ? (
            <EmptyState className="sm:col-span-2" detail={t("people.noMatch")} title={t("people.noMatch")} />
          ) : null}
        </div>
      )}
    </section>
  );
}

function PageMessage({ title, detail }: { title: string; detail: string }) {
  return (
    <Card className="mx-auto mt-8 max-w-3xl p-8 text-center">
      <h1 className="text-xl font-semibold text-slate-950">{title}</h1>
      <p className="mt-2 text-slate-600">{detail}</p>
    </Card>
  );
}
