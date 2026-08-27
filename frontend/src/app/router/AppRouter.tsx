import {
  createBrowserRouter,
  Link,
  Navigate,
  Outlet,
  RouterProvider,
  useLocation,
  useNavigate,
} from "react-router-dom";

import { LoginPage, RegisterPage } from "../../features/auth/AuthPages";
import { BookDetailPage, BooksPage } from "../../features/books";
import { AdminUsersPage, ImportExportPage } from "../../features/admin";
import { FriendsPage } from "../../features/friends";
import { LoansPage } from "../../features/loans";
import { useAuth } from "../../features/auth";
import { PrivacyPage, TermsPage } from "../../features/legal";
import { OwnProfilePage, PeoplePage, PublicProfilePage } from "../../features/users";
import { AssistantPage } from "../../features/assistant";
import { Button, Card, LinkButton, PageHeader } from "../../shared/components";
import { LanguageSwitcher, useTranslation } from "../../shared/i18n";

function AppShell() {
  const { user, isLoading, logout } = useAuth();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const canManageCatalog = user?.role === "LIBRARIAN" || user?.role === "ADMIN";

  async function handleLogout() {
    try {
      await logout();
      navigate("/", { replace: true });
    } catch {
      // The cookie remains authoritative; the next /me request will recover
      // the session state if a transient logout request fails.
    }
  }

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-4">
          <Link className="text-xl font-semibold tracking-tight" to="/">
            LibraryOS
          </Link>
          <nav aria-label={t("nav.main")} className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
            <Link className="text-muted hover:text-ink" to="/books">{t("nav.books")}</Link>
            {user ? (
              <>
                <Link className="text-muted hover:text-ink" to="/people">{t("nav.people")}</Link>
                <Link className="text-muted hover:text-ink" to="/friends">{t("nav.friends")}</Link>
                <Link className="text-muted hover:text-ink" to="/loans">{t("nav.loans")}</Link>
                <Link className="text-muted hover:text-ink" to="/assistant">{t("nav.assistant")}</Link>
                <Link className="text-muted hover:text-ink" to="/profile">{t("nav.profile")}</Link>
                {canManageCatalog ? <Link className="text-muted hover:text-ink" to="/admin/import-export">{t("nav.importExport")}</Link> : null}
                {user.role === "ADMIN" ? <Link className="text-muted hover:text-ink" to="/admin/users">{t("nav.admin")}</Link> : null}
                <Button onClick={handleLogout} size="sm" variant="ghost" type="button">
                  {t("nav.logout")}
                </Button>
              </>
            ) : isLoading ? (
              <span className="text-muted" role="status">{t("nav.checkingSession")}</span>
            ) : (
              <>
                <Link className="text-muted hover:text-ink" to="/login">{t("nav.login")}</Link>
                <LinkButton size="sm" to="/register">
                  {t("nav.register")}
                </LinkButton>
              </>
            )}
            <LanguageSwitcher />
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-12 sm:py-16">
        <Outlet />
      </main>
      <footer className="border-t border-line bg-surface">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-6 text-sm text-muted">
          <span>{t("footer.tagline")}</span>
          <nav aria-label={t("nav.legal")} className="flex gap-4">
            <Link className="hover:text-ink" to="/privacy">{t("footer.privacy")}</Link>
            <Link className="hover:text-ink" to="/terms">{t("footer.terms")}</Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}

function LandingPage() {
  const { t } = useTranslation();

  return (
    <section className="py-8 sm:py-12">
      <PageHeader
        description={t("landing.description")}
        eyebrow={t("landing.eyebrow")}
        title={t("landing.title")}
        actions={
          <>
            <LinkButton size="lg" to="/books">{t("landing.browse")}</LinkButton>
            <LinkButton size="lg" to="/register" variant="secondary">{t("landing.join")}</LinkButton>
          </>
        }
      />
    </section>
  );
}

function ProtectedRoute() {
  const { user, isLoading, error } = useAuth();
  const { t } = useTranslation();
  const location = useLocation();

  if (isLoading) {
    return <RouteMessage title={t("route.checkingTitle")} detail={t("route.checkingDetail")} />;
  }
  if (error) {
    return <RouteMessage title={t("route.verifyTitle")} detail={t("route.verifyDetail")} />;
  }
  if (!user) {
    return <Navigate replace state={{ from: location.pathname }} to="/login" />;
  }
  return <Outlet />;
}

function RouteMessage({ title, detail }: { title: string; detail: string }) {
  return (
    <Card className="mx-auto max-w-xl p-8 text-center">
      <h1 className="text-xl font-semibold text-ink">{title}</h1>
      <p className="mt-2 text-muted">{detail}</p>
    </Card>
  );
}

function NotFoundPage() {
  const { t } = useTranslation();
  return <RouteMessage title={t("route.notFoundTitle")} detail={t("route.notFoundDetail")} />;
}

const router = createBrowserRouter([
  {
    path: "*",
    element: <AppShell />,
    children: [
      { index: true, element: <LandingPage /> },
      { path: "books", element: <BooksPage /> },
      { path: "books/:bookId", element: <BookDetailPage /> },
      { path: "login", element: <LoginPage /> },
      { path: "register", element: <RegisterPage /> },
      { path: "users/:userId", element: <PublicProfilePage /> },
      { path: "privacy", element: <PrivacyPage /> },
      { path: "terms", element: <TermsPage /> },
      {
        element: <ProtectedRoute />,
        children: [
          { path: "profile", element: <OwnProfilePage /> },
          { path: "people", element: <PeoplePage /> },
          { path: "friends", element: <FriendsPage /> },
          { path: "loans", element: <LoansPage /> },
          { path: "assistant", element: <AssistantPage /> },
          { path: "admin/users", element: <AdminUsersPage /> },
          { path: "admin/import-export", element: <ImportExportPage /> },
        ],
      },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} future={{ v7_startTransition: true }} />;
}
