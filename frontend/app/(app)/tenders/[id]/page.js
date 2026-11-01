"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { ArrowLeft, ScanSearch, ShieldCheck, Brain, Swords, Users, ListChecks, FileText, Download, Clock, PlayCircle } from "lucide-react";
import { api } from "@/lib/api";
import PipelineStepper from "@/components/tender/PipelineStepper";
import OverviewTab from "@/components/tender/OverviewTab";
import ProspectTab from "@/components/tender/ProspectTab";
import ProposalTab from "@/components/tender/ProposalTab";
import ExportsTab from "@/components/tender/ExportsTab";
import { Badge, Button, Card, ErrorBox, Gauge, PageLoader, Tabs } from "@/components/ui";
import { STATUS, clean } from "@/lib/format";
import { runPipeline, STEP_LABEL } from "@/lib/pipeline";

const TABS = [
  { key: "overview", label: "Informations et matrice", icon: ListChecks },
  { key: "prospect", label: "Prospect et marché", icon: Brain },
  { key: "proposal", label: "Proposition", icon: FileText },
  { key: "exports", label: "Téléchargements", icon: Download },
];

export default function TenderDetailPage() {
  const { id } = useParams();
  const [tab, setTab] = useState("overview");
  const [tender, setTender] = useState(null);
  const [matrix, setMatrix] = useState([]);
  const [prospect, setProspect] = useState(null);
  const [insights, setInsights] = useState(null);
  const [proposal, setProposal] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [t, m, p, i, d] = await Promise.all([
        api(`/tenders/${id}`),
        api(`/tenders/${id}/matrix`),
        api(`/tenders/${id}/prospect`),
        api(`/tenders/${id}/insights`),
        api(`/tenders/${id}/proposal`),
      ]);
      setTender(t); setMatrix(m); setProspect(p); setInsights(i); setProposal(d);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const run = async (key, path) => {
    setRunning(key);
    setError("");
    try {
      await api(path, { method: "POST" });
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning(null);
    }
  };

  const [autoStep, setAutoStep] = useState("");

  const continuePipeline = async () => {
    setRunning("auto");
    setError("");
    try {
      const res = await runPipeline(id, (step, phase) => phase === "start" && setAutoStep(step));
      if (!res.finished) setError(res.message);
    } catch (e) {
      setError(e.message);
    } finally {
      setAutoStep("");
      setRunning(null);
      await load();
    }
  };

  if (loading) return <PageLoader />;
  if (!tender) return <ErrorBox message={error || "Tender introuvable"} />;

  const status = tender.status;
  const s = STATUS[status] || { label: status, tone: "gray" };
  const qualifiedOrBeyond = ["qualified", "researched", "drafted"].includes(status);
  const researchedOrBeyond = ["researched", "drafted"].includes(status);

  const ACTIONS = [
    { key: "extract", label: "Extraire", icon: ScanSearch, path: `/tenders/${id}/extract?force=true`, enabled: true },
    { key: "qualify", label: "Qualifier", icon: ShieldCheck, path: `/tenders/${id}/qualify`, enabled: status !== "new" && status !== "extraction_failed" },
    { key: "research", label: "Rechercher le prospect", icon: Brain, path: `/tenders/${id}/research`, enabled: qualifiedOrBeyond },
    { key: "insights", label: "Budget et concurrence", icon: Swords, path: `/tenders/${id}/competitor-insights`, enabled: qualifiedOrBeyond },
    { key: "generate", label: "Générer la proposition", icon: Users, path: `/proposals/tenders/${id}/generate`, enabled: researchedOrBeyond },
  ];
  const actionPath = (key) => ACTIONS.find((a) => a.key === key).path;

  return (
    <div className="space-y-6">
      <Link href="/tenders" className="inline-flex items-center gap-2 text-sm font-semibold text-olive-700 hover:underline">
        <ArrowLeft className="h-4 w-4" /> Retour aux appels d'offres
      </Link>

      <Card className="p-6">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="min-w-0 flex-1">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <Badge tone={s.tone}>{s.label}</Badge>
              {tender.urgent_deadline_alert && <Badge tone="red" icon={Clock}>Échéance proche</Badge>}
            </div>
            <h1 className="text-2xl font-extrabold leading-snug tracking-tight text-olive-900">
              {clean(tender.title, "Tender en cours d'analyse")}
            </h1>
            <p className="mt-1 text-olive-600">{clean(tender.issuing_organization, "Organisation non précisée")}</p>
          </div>
          {tender.qualification_score != null && (
            <Gauge value={tender.qualification_score} size={110} stroke={11} label="score"
              color={tender.qualification_score >= 55 ? "#4B5D2E" : "#B3402F"} />
          )}
        </div>
        <div className="mt-6 border-t border-olive-100 pt-4"><PipelineStepper status={status} /></div>
      </Card>

      <Card className="p-5">
        <div className="flex flex-wrap items-center gap-3">
          <span className="mr-2 text-sm font-bold text-olive-800">Actions du pipeline</span>
          <Button
            size="sm" icon={PlayCircle}
            loading={running === "auto"}
            disabled={(running && running !== "auto") || ["drafted", "rejected_low_score", "rejected_expired", "rejected_irrelevant", "extraction_failed"].includes(status)}
            onClick={continuePipeline}
          >
            {running === "auto" ? (STEP_LABEL[autoStep] || "Démarrage") : "Continuer le pipeline"}
          </Button>
          {ACTIONS.map(({ key, label, icon, path, enabled }) => (
            <Button key={key} size="sm" variant={key === "generate" ? "primary" : "secondary"} icon={icon}
              disabled={!enabled || (running && running !== key)} loading={running === key}
              onClick={() => run(key, path)}>
              {label}
            </Button>
          ))}
        </div>
        <p className="mt-3 text-xs text-olive-500">
          Les agents s'exécutent en local sur Ollama : une étape peut durer plusieurs minutes. Ne quittez pas la page pendant l'exécution.
        </p>
        <div className="mt-3"><ErrorBox message={error} /></div>
      </Card>

      <Tabs tabs={TABS} active={tab} onChange={setTab} />

      <div className="animate-fade-up" key={tab}>
        {tab === "overview" && <OverviewTab tender={tender} matrix={matrix} />}
        {tab === "prospect" && (
          <ProspectTab
            prospect={prospect} insights={insights} canRun={qualifiedOrBeyond} running={running}
            onRunResearch={() => run("research", actionPath("research"))}
            onRunInsights={() => run("insights", actionPath("insights"))}
          />
        )}
        {tab === "proposal" && (
          <ProposalTab
            proposal={proposal} canGenerate={researchedOrBeyond} running={running}
            onGenerate={() => run("generate", actionPath("generate"))}
            onProposalChange={setProposal}
          />
        )}
        {tab === "exports" && <ExportsTab proposal={proposal} />}
      </div>
    </div>
  );
}