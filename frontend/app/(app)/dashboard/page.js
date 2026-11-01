"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis } from "recharts";
import { Radar, ShieldCheck, FileText, Target, RefreshCw, ArrowRight, ScanSearch, Brain, Presentation, Database } from "lucide-react";
import { api } from "@/lib/api";
import { Badge, Button, Card, EmptyState, ErrorBox, Gauge, PageHeader, PageLoader, SectionTitle, StatCard } from "@/components/ui";
import { STATUS, STATUS_GROUPS, clean } from "@/lib/format";

const FUNNEL = {
  detected: { label: "Détectés", icon: Radar },
  extracted: { label: "Extraits", icon: ScanSearch },
  qualified: { label: "Qualifiés", icon: ShieldCheck },
  researched: { label: "Prospect analysé", icon: Brain },
  drafted: { label: "Propositions prêtes", icon: Presentation },
};

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setStats(await api("/dashboard/stats"));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading && !stats) return <PageLoader />;
  if (error && !stats) return <ErrorBox message={error} />;
  if (!stats) return null;

  const t = stats.totals;
  const statusCount = Object.fromEntries(stats.by_status.map((s) => [s.status, s.count]));
  const donut = STATUS_GROUPS.map((g) => ({
    name: g.label, color: g.color,
    value: g.statuses.reduce((sum, s) => sum + (statusCount[s] || 0), 0),
  })).filter((d) => d.value > 0);

  const rate = t.tenders ? Math.round((100 * t.qualified) / t.tenders) : 0;
  const top = Math.max(1, ...stats.funnel.map((f) => f.count));

  return (
    <div>
      <PageHeader
        title="Tableau de bord"
        subtitle="Vue d'ensemble de votre pipeline commercial, de la détection à la proposition."
        actions={<Button variant="secondary" icon={RefreshCw} loading={loading} onClick={load}>Actualiser</Button>}
      />

      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard icon={Radar} label="Appels d'offres détectés" value={t.tenders} hint="Toutes sources confondues" />
        <StatCard icon={ShieldCheck} label="Tenders qualifiés" value={t.qualified} hint={`${rate}% de taux de qualification`} tone="dark" />
        <StatCard icon={FileText} label="Propositions générées" value={t.proposals} hint={`${t.approved_proposals} validées par le relecteur`} tone="sand" />
        <StatCard icon={Target} label="Score moyen de qualification" value={t.avg_qualification_score ?? "Non évalué"} hint="Sur 100" />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-5">
        <Card className="p-6 lg:col-span-2">
          <SectionTitle icon={Target} title="Répartition par statut" subtitle="Qualifiés, en attente et rejetés" />
          {donut.length === 0 ? (
            <div className="mt-6"><EmptyState title="Aucune donnée" text="Lancez une détection pour alimenter le graphique." /></div>
          ) : (
            <>
              <div className="relative mt-4 h-60">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={donut} dataKey="value" nameKey="name" innerRadius={68} outerRadius={98} paddingAngle={3} stroke="none">
                      {donut.map((d) => <Cell key={d.name} fill={d.color} />)}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
                <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-3xl font-extrabold text-olive-900">{t.tenders}</span>
                  <span className="text-xs font-semibold uppercase tracking-wider text-olive-500">tenders</span>
                </div>
              </div>
              <div className="mt-2 flex flex-wrap justify-center gap-4">
                {donut.map((d) => (
                  <span key={d.name} className="flex items-center gap-2 text-sm text-olive-700">
                    <span className="h-3 w-3 rounded-full" style={{ background: d.color }} />
                    {d.name} ({d.value})
                  </span>
                ))}
              </div>
            </>
          )}
        </Card>

        <Card className="p-6 lg:col-span-3">
          <SectionTitle icon={Radar} title="Entonnoir du pipeline" subtitle="Combien de tenders franchissent chaque étape" />
          <div className="mt-6 space-y-4">
            {stats.funnel.map((f) => {
              const meta = FUNNEL[f.stage];
              const Icon = meta.icon;
              return (
                <div key={f.stage} className="flex items-center gap-4">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-olive-50 text-olive-700"><Icon className="h-5 w-5" /></span>
                  <div className="flex-1">
                    <div className="mb-1 flex justify-between text-sm">
                      <span className="font-semibold text-olive-800">{meta.label}</span>
                      <span className="font-bold text-olive-900">{f.count}</span>
                    </div>
                    <div className="h-3 overflow-hidden rounded-full bg-olive-100">
                      <div className="h-full rounded-full bg-gradient-to-r from-olive-600 to-olive-400 transition-all duration-700" style={{ width: `${Math.max(3, (f.count / top) * 100)}%` }} />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-5">
        <Card className="p-6 lg:col-span-3">
          <SectionTitle icon={Database} title="Tenders par secteur" subtitle="Domaines d'activité des donneurs d'ordre" />
          {stats.by_sector.length === 0 ? (
            <div className="mt-6"><EmptyState title="Aucune donnée" /></div>
          ) : (
            <div className="mt-4 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stats.by_sector} layout="vertical" margin={{ left: 10, right: 20 }}>
                  <XAxis type="number" hide />
                  <YAxis type="category" dataKey="sector" width={130} tick={{ fontSize: 12, fill: "#3A4824" }} axisLine={false} tickLine={false} />
                  <Tooltip cursor={{ fill: "#F6F7F0" }} />
                  <Bar dataKey="count" name="Tenders" fill="#6E7F44" radius={[0, 8, 8, 0]} barSize={18} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        <Card className="p-6 lg:col-span-2">
          <SectionTitle icon={Target} title="Qualité du RAG" subtitle={`${t.documents} documents, ${t.chunks} passages indexés`} />
          {stats.benchmark ? (
            <div className="mt-6 flex items-center justify-around">
              <div className="text-center">
                <Gauge value={(stats.benchmark.recall_at_k || 0) * 100} size={110} display={(stats.benchmark.recall_at_k || 0).toFixed(2)} label="recall" />
              </div>
              <div className="text-center">
                <Gauge value={(stats.benchmark.mrr || 0) * 100} size={110} display={(stats.benchmark.mrr || 0).toFixed(2)} label="mrr" color="#8A9A5B" />
              </div>
            </div>
          ) : (
            <div className="mt-6">
              <EmptyState title="Aucun benchmark" text="Exécutez le benchmark pour mesurer la précision du retrieval."
                action={<Link href="/benchmark"><Button variant="secondary" size="sm">Ouvrir le benchmark</Button></Link>} />
            </div>
          )}
        </Card>
      </div>

      <Card className="mt-6 p-6">
        <SectionTitle icon={FileText} title="Derniers appels d'offres"
          action={<Link href="/tenders" className="flex items-center gap-1 text-sm font-semibold text-olive-700 hover:underline">Tout voir <ArrowRight className="h-4 w-4" /></Link>} />
        <div className="mt-4 divide-y divide-olive-100">
          {stats.recent.length === 0 && <p className="py-6 text-center text-sm text-olive-500">Aucun tender pour le moment.</p>}
          {stats.recent.map((r) => {
            const s = STATUS[r.status] || { label: r.status, tone: "gray" };
            return (
              <Link key={r.id} href={`/tenders/${r.id}`} className="flex items-center justify-between gap-4 py-3.5 transition hover:bg-olive-50/50">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-olive-900">{clean(r.title, "Tender en cours d'analyse")}</p>
                  <p className="truncate text-xs text-olive-500">{clean(r.issuing_organization)}</p>
                </div>
                <div className="flex items-center gap-3">
                  {r.qualification_score != null && <span className="text-sm font-bold text-olive-800">{Math.round(r.qualification_score)}/100</span>}
                  <Badge tone={s.tone}>{s.label}</Badge>
                </div>
              </Link>
            );
          })}
        </div>
      </Card>
    </div>
  );
}