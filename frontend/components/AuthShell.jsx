import { Radar, Database, Users, Presentation } from "lucide-react";
import Logo from "./Logo";

const FEATURES = [
  { icon: Radar, title: "Détection multi sources", text: "API ouvertes, recherche web et portails d'appels d'offres." },
  { icon: Database, title: "Matching RAG exigence par exigence", text: "Chaque besoin est confronté à vos CV et projets réels." },
  { icon: Users, title: "Agents et équipe de rédaction", text: "Prospect, concurrence, rédacteur et relecteur." },
  { icon: Presentation, title: "Propositions prêtes à présenter", text: "Export PPTX et PDF aux couleurs OliveSoft." },
];

export function Field({ icon: Icon, label, right, ...props }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-semibold text-olive-800">{label}</span>
      <div className="relative">
        <Icon className="pointer-events-none absolute left-4.5 top-1/2 h-4 w-4 -translate-y-1/2 text-brand-cyan" style={{ left: "1.1rem" }} />
        <input className="auth-input" {...props} />
        {right}
      </div>
    </label>
  );
}

export default function AuthShell({ title, subtitle, children }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      <div className="brand-pattern relative hidden flex-col justify-between overflow-hidden p-12 text-white lg:flex">
        <div className="absolute -right-24 top-1/3 h-72 w-72 rounded-full bg-brand-teal/10 blur-3xl" />
        <div className="absolute -left-20 bottom-10 h-64 w-64 rounded-full bg-brand-lime/10 blur-3xl" />

        <div className="relative max-w-sm overflow-hidden rounded-2xl ring-1 ring-white/15">
          <Logo variant="dark" className="h-24" />
        </div>

        <div className="relative">
          <p className="mb-4 text-xs font-bold uppercase tracking-[0.25em] text-brand-teal">RFP Intelligence</p>
          <h2 className="max-w-xl text-4xl font-extrabold leading-tight tracking-tight">
            Répondez plus vite aux appels d'offres qui vous correspondent vraiment
          </h2>
          <p className="mt-4 max-w-md text-olive-200">
            Détection, qualification, recherche prospect et proposition commerciale, dans un seul parcours piloté par l'IA.
          </p>
          <ul className="mt-10 space-y-5">
            {FEATURES.map(({ icon: Icon, title: t, text }) => (
              <li key={t} className="flex items-start gap-4">
                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-white/10 text-brand-teal ring-1 ring-white/10">
                  <Icon className="h-5 w-5" />
                </span>
                <div>
                  <p className="font-semibold">{t}</p>
                  <p className="text-sm text-olive-200">{text}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-sm text-olive-300">IEEE CSTAM Challenge, OliveSoft</p>
      </div>

      <div className="relative flex items-center justify-center bg-white px-6 py-12">
        <div className="absolute right-0 top-0 h-56 w-56 rounded-bl-full bg-gradient-to-br from-brand-teal/15 to-brand-lime/10" />
        <div className="relative w-full max-w-md animate-fade-up">
          <div className="mb-8 lg:hidden"><Logo variant="color" className="h-10" /></div>
          <span className="mb-4 block h-1.5 w-14 rounded-full bg-gradient-to-r from-brand-teal to-brand-lime" />
          <h1 className="text-3xl font-extrabold tracking-tight text-olive-900">{title}</h1>
          <p className="mt-2 text-olive-600">{subtitle}</p>
          <div className="mt-8">{children}</div>
        </div>
      </div>
    </div>
  );
}