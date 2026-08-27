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
import { LoansPage } from "../../features/loans";
import { useAuth } from "../../features/auth";
import { PrivacyPage, TermsPage } from "../../features/legal";
import { OwnProfilePage, PeoplePage, PublicProfilePage } from "../../features/users";

function AppShell() {
  const { user, isLoading, logout } = useAuth();
  const navigate = useNavigate();

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
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-4">
          <Link className="text-xl font-semibold tracking-tight" to="/">
            LibraryOS
          </Link>
          <nav aria-label="Main navigation" className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
            <Link className="text-slate-600 hover:text-slate-950" to="/books">Books</Link>
            {user ? (
              <>
                <Link className="text-slate-600 hover:text-slate-950" to="/people">People</Link>
                <Link className="text-slate-600 hover:text-slate-950" to="/loans">My loans</Link>
                <Link className="text-slate-600 hover:text-slate-950" to="/profile">Profile</Link>
                <button className="font-medium text-sky-700 hover:text-sky-900" onClick={handleLogout} type="button">
                  Log out
                </button>
              </>
            ) : isLoading ? (
              <span className="text-slate-400" role="status">Checking session…</span>
            ) : (
              <>
                <Link className="text-slate-600 hover:text-slate-950" to="/login">Log in</Link>
                <Link className="rounded-lg bg-slate-950 px-3 py-2 font-medium text-white hover:bg-slate-800" to="/register">
                  Register
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-12 sm:py-16">
        <Outlet />
      </main>
      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-6 text-sm text-slate-500">
          <span>A calmer way to manage a library</span>
          <nav aria-label="Legal navigation" className="flex gap-4">
            <Link className="hover:text-slate-950" to="/privacy">Privacy Policy</Link>
            <Link className="hover:text-slate-950" to="/terms">Terms of Service</Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}

function LandingPage() {
  return (
    <section className="py-8 sm:py-12">
      <p className="mb-3 text-sm font-medium uppercase tracking-[0.18em] text-sky-700">Library management</p>
      <h1 className="max-w-2xl text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl">
        Find your next good read.
      </h1>
      <p className="mt-5 max-w-xl text-lg leading-8 text-slate-600">
        Browse the catalog, keep track of loans, and stay connected with your library community.
      </p>
      <div className="mt-8 flex flex-wrap gap-3">
        <Link className="rounded-xl bg-slate-950 px-5 py-3 font-medium text-white hover:bg-slate-800" to="/books">
          Browse books
        </Link>
        <Link className="rounded-xl border border-slate-300 bg-white px-5 py-3 font-medium text-slate-700 hover:border-slate-400" to="/register">
          Join the library
        </Link>
      </div>
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
    <section className="mx-auto max-w-xl rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-sm">
      <h1 className="text-xl font-semibold text-slate-950">{title}</h1>
      <p className="mt-2 text-slate-600">{detail}</p>
    </section>
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
          { path: "loans", element: <LoansPage /> },
        ],
      },
      { path: "*", element: <RouteMessage title="Page not found" detail="That LibraryOS page does not exist." /> },
    ],
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} future={{ v7_startTransition: true }} />;
}
