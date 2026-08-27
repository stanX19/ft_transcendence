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

function AppShell() {
  const { user, isLoading, logout } = useAuth();
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
          <nav aria-label="Main navigation" className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
            <Link className="text-muted hover:text-ink" to="/books">Books</Link>
            {user ? (
              <>
                <Link className="text-muted hover:text-ink" to="/people">People</Link>
                <Link className="text-muted hover:text-ink" to="/friends">Friends</Link>
                <Link className="text-muted hover:text-ink" to="/loans">My loans</Link>
                <Link className="text-muted hover:text-ink" to="/assistant">AI Assistant</Link>
                <Link className="text-muted hover:text-ink" to="/profile">Profile</Link>
                {canManageCatalog ? <Link className="text-muted hover:text-ink" to="/admin/import-export">Import / Export</Link> : null}
                {user.role === "ADMIN" ? <Link className="text-muted hover:text-ink" to="/admin/users">Admin</Link> : null}
                <Button onClick={handleLogout} size="sm" variant="ghost" type="button">
                  Log out
                </Button>
              </>
            ) : isLoading ? (
              <span className="text-muted" role="status">Checking session…</span>
            ) : (
              <>
                <Link className="text-muted hover:text-ink" to="/login">Log in</Link>
                <LinkButton size="sm" to="/register">
                  Register
                </LinkButton>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-12 sm:py-16">
        <Outlet />
      </main>
      <footer className="border-t border-line bg-surface">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-6 text-sm text-muted">
          <span>A calmer way to manage a library</span>
          <nav aria-label="Legal navigation" className="flex gap-4">
            <Link className="hover:text-ink" to="/privacy">Privacy Policy</Link>
            <Link className="hover:text-ink" to="/terms">Terms of Service</Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}

function LandingPage() {
  return (
    <section className="py-8 sm:py-12">
      <PageHeader
        description="Browse the catalog, keep track of loans, and stay connected with your library community."
        eyebrow="Library management"
        title="Find your next good read."
        actions={
          <>
            <LinkButton size="lg" to="/books">Browse books</LinkButton>
            <LinkButton size="lg" to="/register" variant="secondary">Join the library</LinkButton>
          </>
        }
      />
    </section>
  );
}

function ProtectedRoute() {
  const { user, isLoading, error } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <RouteMessage title="Checking your session…" detail="Please wait while we verify your account." />;
  }
  if (error) {
    return <RouteMessage title="We could not verify your session" detail="Refresh the page and try again." />;
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
      { path: "*", element: <RouteMessage title="Page not found" detail="That LibraryOS page does not exist." /> },
    ],
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} future={{ v7_startTransition: true }} />;
}
