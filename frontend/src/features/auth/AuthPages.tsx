import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { ApiError } from "../../shared/api";
import { preventInvalidSubmit, useAuth } from "./AuthProvider";

function authErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.status === 409) {
    return "An account with that email already exists.";
  }
  if (error instanceof ApiError && error.status === 401) {
    return "The email or password is incorrect.";
  }
  return "We could not complete that request. Please try again.";
}

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!preventInvalidSubmit(event)) {
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await login(email, password);
      const destination =
        (location.state as { from?: string } | null)?.from ?? "/profile";
      navigate(destination, { replace: true });
    } catch (submitError) {
      setError(authErrorMessage(submitError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="mx-auto max-w-xl">
      <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm sm:p-10">
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-sky-700">
          Welcome back
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">
          Log in to LibraryOS
        </h1>
        <p className="mt-3 text-slate-600">
          Use your library account to manage reading and community activity.
        </p>
        <form className="mt-8 space-y-5" onSubmit={submit}>
          <div>
            <label className="text-sm font-medium text-slate-800" htmlFor="login-email">
              Email
            </label>
            <input
              autoComplete="email"
              className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 text-slate-900 shadow-sm"
              id="login-email"
              name="email"
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-800" htmlFor="login-password">
              Password
            </label>
            <input
              autoComplete="current-password"
              className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 text-slate-900 shadow-sm"
              id="login-password"
              minLength={8}
              name="password"
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </div>
          {error ? (
            <p className="rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-800" role="alert">
              {error}
            </p>
          ) : null}
          <button
            className="w-full rounded-xl bg-slate-950 px-4 py-3 font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting ? "Logging in…" : "Log in"}
          </button>
        </form>
        <p className="mt-6 text-sm text-slate-600">
          New to LibraryOS?{" "}
          <Link className="font-medium text-sky-700 hover:text-sky-900" to="/register">
            Create an account
          </Link>
        </p>
      </div>
    </section>
  );
}

export function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!preventInvalidSubmit(event)) {
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await register(displayName, email, password);
      navigate("/profile", { replace: true });
    } catch (submitError) {
      setError(authErrorMessage(submitError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="mx-auto max-w-xl">
      <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm sm:p-10">
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-sky-700">
          Join the library
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">
          Create your account
        </h1>
        <p className="mt-3 text-slate-600">
          Start with a display name, email, and a password of at least eight characters.
        </p>
        <form className="mt-8 space-y-5" onSubmit={submit}>
          <div>
            <label className="text-sm font-medium text-slate-800" htmlFor="register-display-name">
              Display name
            </label>
            <input
              autoComplete="name"
              className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 text-slate-900 shadow-sm"
              id="register-display-name"
              minLength={2}
              name="display_name"
              onChange={(event) => setDisplayName(event.target.value)}
              required
              type="text"
              value={displayName}
            />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-800" htmlFor="register-email">
              Email
            </label>
            <input
              autoComplete="email"
              className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 text-slate-900 shadow-sm"
              id="register-email"
              name="email"
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-800" htmlFor="register-password">
              Password
            </label>
            <input
              autoComplete="new-password"
              className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 text-slate-900 shadow-sm"
              id="register-password"
              minLength={8}
              name="password"
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </div>
          {error ? (
            <p className="rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-800" role="alert">
              {error}
            </p>
          ) : null}
          <button
            className="w-full rounded-xl bg-slate-950 px-4 py-3 font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting ? "Creating account…" : "Create account"}
          </button>
        </form>
        <p className="mt-6 text-sm text-slate-600">
          Already registered?{" "}
          <Link className="font-medium text-sky-700 hover:text-sky-900" to="/login">
            Log in
          </Link>
        </p>
      </div>
    </section>
  );
}
