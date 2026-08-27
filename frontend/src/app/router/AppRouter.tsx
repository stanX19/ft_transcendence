import { createBrowserRouter, RouterProvider } from "react-router-dom";

function AppShell() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <span className="text-xl font-semibold tracking-tight">LibraryOS</span>
          <span className="text-sm text-slate-500">A calmer way to manage a library</span>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-16">
        <p className="mb-3 text-sm font-medium uppercase tracking-[0.18em] text-sky-700">
          Library management
        </p>
        <h1 className="max-w-2xl text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl">
          Find your next good read.
        </h1>
        <p className="mt-5 max-w-xl text-lg leading-8 text-slate-600">
          Browse the catalog, keep track of loans, and stay connected with your library community.
        </p>
      </main>
    </div>
  );
}

const router = createBrowserRouter([
  {
    path: "*",
    element: <AppShell />,
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} future={{ v7_startTransition: true }} />;
}
