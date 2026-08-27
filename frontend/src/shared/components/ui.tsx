import { LoaderCircle } from "lucide-react";
import { Link, type LinkProps } from "react-router-dom";
import type {
  ButtonHTMLAttributes,
  HTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";

function cx(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

type ControlVariant = "primary" | "accent" | "secondary" | "danger" | "ghost";
type ControlSize = "sm" | "md" | "lg";

const controlVariants: Record<ControlVariant, string> = {
  primary: "bg-ink text-surface hover:bg-ink-soft",
  accent: "bg-accent-700 text-surface hover:bg-accent-800",
  secondary: "border border-line bg-surface text-ink-soft hover:border-accent-700 hover:text-accent-900",
  danger: "border border-danger-50 bg-danger-50 text-danger-700 hover:border-danger-700 hover:text-danger-900",
  ghost: "text-muted hover:bg-canvas hover:text-ink",
};

const controlSizes: Record<ControlSize, string> = {
  sm: "px-3 py-2 text-sm",
  md: "px-4 py-2.5 text-sm",
  lg: "px-5 py-3",
};

function controlClass(
  variant: ControlVariant,
  size: ControlSize,
  className?: string,
): string {
  return cx(
    "inline-flex items-center justify-center gap-2 rounded-control font-medium transition duration-200 ease-out focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-accent-100 disabled:cursor-not-allowed disabled:opacity-60",
    controlVariants[variant],
    controlSizes[size],
    className,
  );
}

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ControlVariant;
  size?: ControlSize;
  loading?: boolean;
}

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  disabled,
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      aria-busy={loading || undefined}
      className={controlClass(variant, size, className)}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? <LoaderCircle aria-hidden="true" className="animate-spin" size={16} /> : null}
      {children}
    </button>
  );
}

export interface LinkButtonProps extends LinkProps {
  variant?: ControlVariant;
  size?: ControlSize;
  className?: string;
  children: ReactNode;
}

export function LinkButton({
  variant = "primary",
  size = "md",
  className,
  children,
  ...props
}: LinkButtonProps) {
  return (
    <Link className={controlClass(variant, size, className)} {...props}>
      {children}
    </Link>
  );
}

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  tone?: "surface" | "tinted";
}

export function Card({ tone = "surface", className, ...props }: CardProps) {
  return (
    <div
      className={cx(
        "rounded-panel border shadow-panel",
        tone === "surface"
          ? "border-line bg-surface"
          : "border-accent-100 bg-accent-50/70",
        className,
      )}
      {...props}
    />
  );
}

export function Badge({
  variant = "neutral",
  className,
  children,
}: {
  variant?: "neutral" | "accent" | "success" | "danger";
  className?: string;
  children: ReactNode;
}) {
  const variants = {
    neutral: "bg-canvas text-muted",
    accent: "bg-accent-50 text-accent-900",
    success: "bg-success-50 text-success-700",
    danger: "bg-danger-50 text-danger-700",
  };
  return <span className={cx("inline-flex rounded-full px-2.5 py-1 text-xs font-medium", variants[variant], className)}>{children}</span>;
}

const fieldClassName = "mt-2 w-full rounded-control border border-line bg-surface px-3 py-2.5 text-sm text-ink shadow-sm outline-none transition placeholder:text-muted/70 focus:border-accent-700 focus:ring-4 focus:ring-accent-100 disabled:cursor-not-allowed disabled:opacity-60";

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cx(fieldClassName, className)} {...props} />;
}

export function Select({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={cx(fieldClassName, className)} {...props} />;
}

export function TextArea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={cx(fieldClassName, "resize-y", className)} {...props} />;
}

export function FormField({
  label,
  htmlFor,
  hint,
  children,
  className,
}: {
  label: ReactNode;
  htmlFor?: string;
  hint?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cx("text-sm", className)}>
      <label className="font-medium text-ink-soft" htmlFor={htmlFor}>{label}</label>
      {children}
      {hint ? <p className="mt-1.5 text-xs leading-5 text-muted">{hint}</p> : null}
    </div>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-5">
      <div>
        {eyebrow ? <p className="text-sm font-medium uppercase tracking-[0.18em] text-accent-700">{eyebrow}</p> : null}
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">{title}</h1>
        {description ? <p className="mt-3 max-w-2xl leading-7 text-muted">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap gap-3">{actions}</div> : null}
    </div>
  );
}

export function LoadingState({ title, detail }: { title: string; detail?: string }) {
  return (
    <Card className="mt-8 flex items-center gap-3 p-8 text-muted" role="status">
      <LoaderCircle aria-hidden="true" className="animate-spin text-accent-700" size={20} />
      <div><p className="font-medium text-ink-soft">{title}</p>{detail ? <p className="mt-1 text-sm">{detail}</p> : null}</div>
    </Card>
  );
}

export function EmptyState({ title, detail, action }: { title: string; detail: string; action?: ReactNode }) {
  return (
    <Card className="mt-8 p-8 text-center">
      <h2 className="text-lg font-semibold text-ink">{title}</h2>
      <p className="mx-auto mt-2 max-w-md leading-6 text-muted">{detail}</p>
      {action ? <div className="mt-5 flex justify-center">{action}</div> : null}
    </Card>
  );
}

export function ErrorAlert({ message, className }: { message: ReactNode; className?: string }) {
  return <div className={cx("rounded-control border border-danger-50 bg-danger-50 px-4 py-3 text-sm text-danger-900", className)} role="alert">{message}</div>;
}

export function Notice({
  message,
  variant = "success",
  className,
}: {
  message: ReactNode;
  variant?: "success" | "accent";
  className?: string;
}) {
  return <div className={cx("rounded-control border px-4 py-3 text-sm", variant === "success" ? "border-success-50 bg-success-50 text-success-700" : "border-accent-100 bg-accent-50 text-accent-900", className)} role="status">{message}</div>;
}
