"use client";

import { useCallback, useEffect, useState } from "react";
import { ExternalLink, RefreshCw, Radar, ScanSearch, Database, ShieldCheck, Brain, Swords, Users, Presentation, ChevronRight, Workflow } from "lucide-react";
import { api } from "@/lib/api";
import { Badge, Button, Card, EmptyState, ErrorBox, PageHeader, PageLoader, SectionTitle } from "@/components/ui";
import { formatDateTime } from "@/lib/format";

const N8N_URL = process.env.NEXT_PUBLIC_N8N_URL || "http://localhost:5678";

const PIPELINE = [
  { icon: Radar, title: "Détection", tech: "Serper, Apify, API ouverte" },
  { icon: ScanSearch, title: "Extraction", tech: "LLM local, schéma JSON" },
  { icon: Database, title: "Matching RAG", tech: "pgvector, juge LLM" },
  { icon: ShieldCheck, title: "Qualification", tech: "Score pondéré, seuils" },
  { icon: Brain, title: "Prospect", tech: "LangGraph ReAct, MCP" },
  { icon: Swords, title: "Concurrence", tech: "Agent budget" },
  { icon: Users, title: "Rédaction", tech: "CrewAI, relecteur" },
  { icon: Presentation, title: "Export", tech: "PPTX et PDF" },
];

const EXEC_STATUS = {
  success: { label: "Terminée", tone: "green" },
  error: { label: "En erreur", tone: "red" },
  crashed: { label: "Plantée", tone: "red" },
  running: { label: "En cours", tone: "blue" },
  waiting: { label: "En attente", tone: "amber" },
  new: { label: "Nouvelle", tone: "gray" },
  canceled: { label: "Annulée", tone: "gray" },
};

const duration = (s) => (s == null ? "En cours" : s >= 60 ? `${Math.floor(s / 60)} min ${s % 60} s` : `${s} s`);

export default function OrchestrationPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [auto, setAuto] = useState(false);

  const load = useCallback(async () => {
    try {
      setData(await api("/orchestration/executions"));
      setError("");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (!auto) return undefined;
    const timer = setInterval(load, 10000);
    return () => clearInterval(timer);
  }, [auto, load]);

  const execs = data?.executions || [];
  const counts = execs.reduce((acc, e) => ({ ...acc, [e.status]: (acc[e.status] || 0) + 1 }), {});

  return (
    <div>
      <PageHeader
        title="Orchestration n8n"
        subtitle="Le workflow qui enchaîne détection, qualification, agents, rédaction et export, tender par tender."
        actions={
          <>
            <Button variant={auto ? "accent" : "secondary"} icon={RefreshCw} onClick={() => setAuto(!auto)}>
              {auto ? "Actualisation automatique active" : "Actualisation automatique"}
            </Button>
            <a href={N8N_URL} target="_blank" rel="noreferrer"><Button icon={ExternalLink}>Ouvrir n8n</Button></a>
          </>
        }
      />

      <Card className="p-6">
        <SectionTitle icon={Workflow} title="Pipeline orchestré" subtitle="Un tender en erreur ne bloque jamais les suivants : chaque branche revient à la boucle" />
        <div className="mt-6 flex flex-wrap items-stretch gap-y-4">
          {PIPELINE.map(({ icon: Icon, title, tech }, i) => (
            <div key={title} className="flex items-center">
              <div className="w-36 rounded-2xl border border-olive-100 bg-olive-50/60 p-4 text-center">
                <span className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-olive-700 text-white"><Icon className="h-5 w-5" /></span>
                <p className="text-sm font-bold text-olive-900">{title}</p>
                <p className="mt-1 text-[11px] leading-snug text-olive-500">{tech}</p>
              </div>
              {i < PIPELINE.length - 1 && <ChevronRight className="mx-1 h-5 w-5 shrink-0 text-olive-300" />}
            </div>
          ))}
        </div>
      </Card>

      <ErrorBox message={error} />

      <Card className="mt-6 overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 p-6 pb-4">
          <SectionTitle icon={RefreshCw} title="Exécutions récentes" subtitle="Lues depuis l'API n8n" />
          <div className="flex gap-2">
            {Object.entries(counts).map(([status, n]) => {
              const m = EXEC_STATUS[status] || { label: status, tone: "gray" };
              return <Badge key={status} tone={m.tone}>{m.label} : {n}</Badge>;
            })}
          </div>
        </div>
        {loading ? <PageLoader /> : !data?.configured ? (
          <div className="p-6 pt-0">
            <EmptyState icon={Workflow} title="API n8n non configurée"
              text="Dans n8n, créez une clé API (Settings, n8n API), puis ajoutez N8N_API_KEY dans backend/.env et redémarrez l'API."
              action={<a href={N8N_URL} target="_blank" rel="noreferrer"><Button variant="secondary" icon={ExternalLink}>Ouvrir n8n</Button></a>} />
          </div>
        ) : data.error ? (
          <div className="p-6 pt-0"><ErrorBox message={data.error} /></div>
        ) : execs.length === 0 ? (
          <div className="p-6 pt-0"><EmptyState title="Aucune exécution" text="Lancez le workflow depuis n8n pour voir apparaître son historique." /></div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-olive-50 text-xs uppercase tracking-wider text-olive-600">
                <tr><th className="px-6 py-3">Exécution</th><th className="px-4 py-3">Statut</th><th className="px-4 py-3">Déclenchement</th><th className="px-4 py-3">Début</th><th className="px-6 py-3">Durée</th></tr>
              </thead>
              <tbody className="divide-y divide-olive-100">
                {execs.map((e) => {
                  const m = EXEC_STATUS[e.status] || { label: e.status, tone: "gray" };
                  return (
                    <tr key={e.id} className="hover:bg-olive-50/50">
                      <td className="px-6 py-3.5 font-semibold text-olive-900">#{e.id}</td>
                      <td className="px-4 py-3.5"><Badge tone={m.tone}>{m.label}</Badge></td>
                      <td className="px-4 py-3.5 capitalize text-olive-700">{e.mode === "manual" ? "Manuel" : e.mode}</td>
                      <td className="px-4 py-3.5 text-olive-700">{formatDateTime(e.started_at)}</td>
                      <td className="px-6 py-3.5 text-olive-700">{duration(e.duration_seconds)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      <p className="mt-4 text-xs text-olive-500">
        L'intégration du canvas n8n en iframe est bloquée par n8n par défaut. Le bouton Ouvrir n8n affiche le canvas dans un nouvel onglet.
      </p>
    </div>
  );
}