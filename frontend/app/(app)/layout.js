"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { LogOut, Menu } from "lucide-react";
import Sidebar from "@/components/Sidebar";
import { PageLoader } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { initials } from "@/lib/format";

const TITLES = {
  "/dashboard": "Tableau de bord",
  "/tenders": "Appels d'offres",
  "/knowledge": "Base de connaissances",
  "/benchmark": "Benchmark RAG",
  "/orchestration": "Orchestration",
};

export default function AppLayout({ children }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  useEffect(() => setOpen(false), [pathname]);

  if (loading || !user) return <PageLoader />;

  const section = Object.entries(TITLES).find(([href]) => pathname === href || pathname.startsWith(href + "/"))?.[1];

  return (
    <div className="min-h-screen lg:pl-72">
      <Sidebar open={open} onClose={() => setOpen(false)} />
      <header className="sticky top-0 z-20 border-b border-olive-100 bg-white/90 backdrop-blur">
        <div className="h-1 bg-gradient-to-r from-brand-teal via-brand-cyan to-brand-lime" />
        <div className="flex items-center justify-between px-4 py-3 sm:px-8">
          <div className="flex items-center gap-3">
            <button type="button" onClick={() => setOpen(true)} className="rounded-lg p-2 text-olive-700 hover:bg-olive-100 lg:hidden">
              <Menu className="h-5 w-5" />
            </button>
            <div className="leading-tight">
              <p className="text-xs font-semibold uppercase tracking-wider text-olive-500">Espace commercial</p>
              <p className="text-sm font-bold text-olive-900">{section || "OliveSoft"}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden text-right leading-tight sm:block">
              <p className="text-sm font-bold text-olive-900">{user.full_name}</p>
              <p className="text-xs text-olive-500">{user.role === "admin" ? "Administrateur" : "Commercial"}</p>
            </div>
            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-olive-900 to-olive-600 text-sm font-bold text-white">
              {initials(user.full_name)}
            </span>
            <button type="button" onClick={logout} title="Se déconnecter" className="rounded-lg p-2 text-olive-600 hover:bg-olive-100">
              <LogOut className="h-5 w-5" />
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl animate-fade-up px-4 py-8 sm:px-8">{children}</main>
    </div>
  );
}