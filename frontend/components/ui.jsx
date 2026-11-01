"use client";

import { Loader2, Inbox, X, AlertTriangle } from "lucide-react";

export const cx = (...classes) => classes.filter(Boolean).join(" ");

export function Card({ className, children }) {
  return <div className={cx("rounded-2xl border border-olive-100 bg-white shadow-soft", className)}>{children}</div>;
}

export function SectionTitle({ icon: Icon, title, subtitle, action }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="flex items-center gap-3">
        {Icon && (
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-olive-50 text-olive-700">
            <Icon className="h-5 w-5" />
          </span>
        )}
        <div>
          <h3 className="text-base font-bold text-olive-900">{title}</h3>
          {subtitle && <p className="text-sm text-olive-600">{subtitle}</p>}
        </div>
      </div>
      {action}
    </div>
  );
}

const TONES = {
  green: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  red: "bg-red-50 text-red-700 ring-red-600/20",
  amber: "bg-amber-50 text-amber-700 ring-amber-600/20",
  blue: "bg-sky-50 text-sky-700 ring-sky-600/20",
  olive: "bg-olive-100 text-olive-800 ring-olive-600/20",
  gray: "bg-stone-100 text-stone-600 ring-stone-500/20",
};

export function Badge({ tone = "gray", icon: Icon, children, className }) {
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset",
        TONES[tone] || TONES.gray,
        className
      )}
    >
      {Icon && <Icon className="h-3.5 w-3.5" />}
      {children}
    </span>
  );
}

const BUTTONS = {
  primary: "bg-olive-700 text-white hover:bg-olive-800 shadow-sm",
  secondary: "border border-olive-200 bg-white text-olive-800 hover:bg-olive-50",
  accent: "bg-sand-300 text-olive-900 hover:bg-sand-400",
  ghost: "text-olive-700 hover:bg-olive-50",
  danger: "bg-red-600 text-white hover:bg-red-700",
};

export function Button({
  variant = "primary", size = "md", icon: Icon, loading, className, children, disabled, type = "button", ...props
}) {
  const sizes = { sm: "px-3 py-1.5 text-sm", md: "px-4 py-2.5 text-sm", lg: "px-6 py-3 text-base" };
  return (
    <button
      type={type}
      disabled={disabled || loading}
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-xl font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-olive-500 disabled:cursor-not-allowed disabled:opacity-50",
        sizes[size], BUTTONS[variant], className
      )}
      {...props}
    >
      {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : Icon && <Icon className="h-4 w-4" />}
      {children}
    </button>
  );
}

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight text-olive-900 sm:text-3xl">{title}</h1>
        {subtitle && <p className="mt-1 max-w-2xl text-sm text-olive-600">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-3">{actions}</div>}
    </div>
  );
}

export function StatCard({ icon: Icon, label, value, hint, tone = "olive" }) {
  const bg = { olive: "bg-olive-700", sand: "bg-sand-300 text-olive-900", dark: "bg-olive-900" }[tone];
  return (
    <Card className="relative overflow-hidden p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-olive-600">{label}</p>
          <p className="mt-2 text-3xl font-extrabold tracking-tight text-olive-900">{value}</p>
          {hint && <p className="mt-1 text-xs text-olive-500">{hint}</p>}
        </div>
        <span className={cx("flex h-11 w-11 items-center justify-center rounded-xl text-white", bg)}>
          <Icon className="h-5 w-5" />
        </span>
      </div>
      <div className="absolute -bottom-6 -right-6 h-20 w-20 rounded-full bg-olive-50" />
    </Card>
  );
}

export function Tabs({ tabs, active, onChange }) {
  return (
    <div className="flex gap-1 overflow-x-auto rounded-2xl border border-olive-100 bg-white p-1.5 shadow-soft">
      {tabs.map(({ key, label, icon: Icon }) => (
        <button
          key={key}
          type="button"
          onClick={() => onChange(key)}
          className={cx(
            "flex flex-1 items-center justify-center gap-2 whitespace-nowrap rounded-xl px-4 py-2.5 text-sm font-semibold transition",
            active === key ? "bg-olive-700 text-white shadow-sm" : "text-olive-700 hover:bg-olive-50"
          )}
        >
          {Icon && <Icon className="h-4 w-4" />}
          {label}
        </button>
      ))}
    </div>
  );
}

export function ProgressBar({ value = 0, className }) {
  const v = Math.max(0, Math.min(100, value));
  const color = v >= 70 ? "bg-emerald-500" : v >= 50 ? "bg-olive-500" : v >= 30 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className={cx("h-2 w-full overflow-hidden rounded-full bg-olive-100", className)}>
      <div className={cx("h-full rounded-full transition-all duration-700", color)} style={{ width: `${v}%` }} />
    </div>
  );
}

export function Gauge({ value = 0, size = 96, stroke = 9, label, display, color = "#4B5D2E" }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const v = Math.max(0, Math.min(100, value));
  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#ECEFDF" strokeWidth={stroke} />
        <circle
          cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke}
          strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c - (c * v) / 100}
          style={{ transition: "stroke-dashoffset .9s ease" }}
        />
      </svg>
      <div className="absolute text-center leading-tight">
        <div className="text-xl font-extrabold text-olive-900">{display ?? Math.round(v)}</div>
        {label && <div className="text-[10px] font-semibold uppercase tracking-wider text-olive-500">{label}</div>}
      </div>
    </div>
  );
}

export function EmptyState({ icon: Icon = Inbox, title, text, action }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-olive-200 bg-white/60 px-6 py-14 text-center">
      <span className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-olive-50 text-olive-600">
        <Icon className="h-7 w-7" />
      </span>
      <h4 className="text-base font-bold text-olive-900">{title}</h4>
      {text && <p className="mt-1 max-w-md text-sm text-olive-600">{text}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorBox({ message }) {
  if (!message) return null;
  return (
    <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
      <span>{message}</span>
    </div>
  );
}

export function PageLoader() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin text-olive-600" />
    </div>
  );
}

export function Modal({ open, onClose, title, children, wide }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-olive-950/60 backdrop-blur-sm" onClick={onClose} />
      <div
        className={cx(
          "relative max-h-[90vh] w-full overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl animate-fade-up",
          wide ? "max-w-2xl" : "max-w-lg"
        )}
      >
        <div className="mb-5 flex items-center justify-between">
          <h3 className="text-lg font-bold text-olive-900">{title}</h3>
          <button type="button" onClick={onClose} className="rounded-lg p-1.5 text-olive-500 hover:bg-olive-50">
            <X className="h-5 w-5" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}