import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { ApiError } from "../../shared/api";
import { Button, Card, ErrorAlert, FormField, Input, PageHeader } from "../../shared/components";
import { type Translator, useTranslation } from "../../shared/i18n";
import { preventInvalidSubmit, useAuth } from "./AuthProvider";

function authErrorMessage(error: unknown, t: Translator): string {
  if (error instanceof ApiError && error.status === 409) {
    return t("auth.error.accountExists");
  }
  if (error instanceof ApiError && error.status === 401) {
    return t("auth.error.invalidCredentials");
  }
  return t("auth.error.generic");
}

export function LoginPage() {
  const { login } = useAuth();
  const { t } = useTranslation();
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
      setError(authErrorMessage(submitError, t));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="mx-auto max-w-xl">
      <Card className="p-8 sm:p-10">
        <PageHeader
          description={t("auth.loginDescription")}
          eyebrow={t("auth.loginEyebrow")}
          title={t("auth.loginTitle")}
        />
        <form className="mt-8 space-y-5" onSubmit={submit}>
          <FormField htmlFor="login-email" label={t("auth.email")}>
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
          <FormField htmlFor="login-password" label={t("auth.password")}>
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
            {isSubmitting ? t("auth.loggingIn") : t("auth.login")}
          </Button>
        </form>
        <p className="mt-6 text-sm text-muted">
          {t("auth.newToLibrary")}{" "}
          <Link className="font-medium text-accent-700 hover:text-accent-900" to="/register">
            {t("auth.createAccount")}
          </Link>
        </p>
      </Card>
    </section>
  );
}

export function RegisterPage() {
  const { register } = useAuth();
  const { t } = useTranslation();
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
      setError(authErrorMessage(submitError, t));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="mx-auto max-w-xl">
      <Card className="p-8 sm:p-10">
        <PageHeader
          description={t("auth.registerDescription")}
          eyebrow={t("auth.registerEyebrow")}
          title={t("auth.registerTitle")}
        />
        <form className="mt-8 space-y-5" onSubmit={submit}>
          <FormField htmlFor="register-display-name" label={t("auth.displayName")}>
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
          <FormField htmlFor="register-email" label={t("auth.email")}>
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
          <FormField htmlFor="register-password" label={t("auth.password")}>
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
            {isSubmitting ? t("auth.creatingAccount") : t("auth.createAccount")}
          </Button>
        </form>
        <p className="mt-6 text-sm text-muted">
          {t("auth.alreadyRegistered")}{" "}
          <Link className="font-medium text-accent-700 hover:text-accent-900" to="/login">
            {t("auth.login")}
          </Link>
        </p>
      </Card>
    </section>
  );
}
