import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { ApiError } from "../../shared/api";
import { Button, Card, ErrorAlert, FormField, Input, PageHeader } from "../../shared/components";
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
      <Card className="p-8 sm:p-10">
        <PageHeader
          description="Use your library account to manage reading and community activity."
          eyebrow="Welcome back"
          title="Log in to LibraryOS"
        />
        <form className="mt-8 space-y-5" onSubmit={submit}>
          <FormField htmlFor="login-email" label="Email">
            <Input
              autoComplete="email"
              id="login-email"
              name="email"
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </FormField>
          <FormField htmlFor="login-password" label="Password">
            <Input
              autoComplete="current-password"
              id="login-password"
              minLength={8}
              name="password"
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </FormField>
          {error ? (
            <ErrorAlert message={error} />
          ) : null}
          <Button
            className="w-full"
            disabled={isSubmitting}
            loading={isSubmitting}
            type="submit"
          >
            {isSubmitting ? "Logging in…" : "Log in"}
          </Button>
        </form>
        <p className="mt-6 text-sm text-muted">
          New to LibraryOS?{" "}
          <Link className="font-medium text-accent-700 hover:text-accent-900" to="/register">
            Create an account
          </Link>
        </p>
      </Card>
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
      <Card className="p-8 sm:p-10">
        <PageHeader
          description="Start with a display name, email, and a password of at least eight characters."
          eyebrow="Join the library"
          title="Create your account"
        />
        <form className="mt-8 space-y-5" onSubmit={submit}>
          <FormField htmlFor="register-display-name" label="Display name">
            <Input
              autoComplete="name"
              id="register-display-name"
              minLength={2}
              name="display_name"
              onChange={(event) => setDisplayName(event.target.value)}
              required
              type="text"
              value={displayName}
            />
          </FormField>
          <FormField htmlFor="register-email" label="Email">
            <Input
              autoComplete="email"
              id="register-email"
              name="email"
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </FormField>
          <FormField htmlFor="register-password" label="Password">
            <Input
              autoComplete="new-password"
              id="register-password"
              minLength={8}
              name="password"
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </FormField>
          {error ? (
            <ErrorAlert message={error} />
          ) : null}
          <Button
            className="w-full"
            disabled={isSubmitting}
            loading={isSubmitting}
            type="submit"
          >
            {isSubmitting ? "Creating account…" : "Create account"}
          </Button>
        </form>
        <p className="mt-6 text-sm text-muted">
          Already registered?{" "}
          <Link className="font-medium text-accent-700 hover:text-accent-900" to="/login">
            Log in
          </Link>
        </p>
      </Card>
    </section>
  );
}
