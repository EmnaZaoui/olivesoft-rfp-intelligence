"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, FileSearch, Library, Target, Workflow, X } from "lucide-react";
import Logo from "./Logo";
import Chatbot from "./Chatbot";
import { cx } from "./ui";

const NAV = [
  { href: "/dashboard", label: "Tableau de bord", icon: LayoutDashboard },
  { href: "/tenders", label: "Appels d'offres", icon: FileSearch },
  { href: "/knowledge", label: "Base de connaissances", icon: Library },
  { href: "/benchmark", label: "Benchmark RAG", icon: Target },
  { href: "/orchestration", label: "Orchestration", icon: Workflow },
];

export default function Sidebar({ open, onClose }) {
  const pathname = usePathname();
  return (
    <>
      {open && <div className="fixed inset-0 z-30 bg-brand-ink/60 lg:hidden" onClick={onClose} />}
      <aside
        className={cx(
          "brand-pattern fixed inset-y-0 left-0 z-40 flex w-72 flex-col px-5 py-6 transition-transform duration-300 lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="mb-8">
          <div className="flex items-start justify-between">
            <div className="rounded-2xl bg-white px-4 py-3 shadow-lg">
              <Logo variant="color" className="h-9" />
            </div>
            <button type="button" onClick={onClose} className="rounded-lg p-1.5 text-olive-200 lg:hidden">
              <X className="h-5 w-5" />
            </button>
          </div>
          <p className="mt-3 pl-1 text-[11px] font-bold uppercase tracking-[0.22em] text-brand-teal">RFP Intelligence</p>
        </div>

        <nav className="flex-1 space-y-1.5">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(href + "/");
            return (
              <Link
                key={href}
                href={href}
                className={cx(
                  "group flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold transition",
                  active ? "bg-brand-lime text-brand-navy shadow-lg" : "text-olive-100 hover:bg-white/10"
                )}
              >
                <Icon className={cx("h-5 w-5", active ? "text-brand-navy" : "text-brand-teal group-hover:text-white")} />
                {label}
              </Link>
            );
          })}
        </nav>

        <Chatbot />
        <p className="mt-4 text-center text-[11px] text-olive-300">IEEE CSTAM Challenge, OliveSoft</p>
      </aside>
    </>
  );
}