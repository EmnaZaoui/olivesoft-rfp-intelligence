"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Target, Building2, ListChecks, Briefcase, Banknote, ArrowRight, Pencil, Wand2, Save, X, FileText, Users, CheckCircle2, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";
import { Badge, Button, Card, EmptyState, ErrorBox } from "../ui";

const SECTIONS = [
  { key: "contexte", label: "Comprendre votre enjeu", icon: Target },
  { key: "profil_prospect", label: "Votre organisation", icon: Building2 },
  { key: "reponse_aux_exigences", label: "Réponse aux exigences", icon: ListChecks },
  { key: "references_pertinentes", label: "Références pertinentes", icon: Briefcase },
  { key: "budget_et_positionnement", label: "Budget et positionnement", icon: Banknote },
  { key: "prochaines_etapes", label: "Prochaines étapes", icon: ArrowRight },
];

const stripHeading = (md = "") => md.replace(/^\s*#{1,6}[^\n]*\n+/, "").trim();

function SectionCard({ proposal, section, content, editable, onUpdated }) {
  const [mode, setMode] = useState("view");
  const [text, setText] = useState("");
  const [instruction, setInstruction] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const Icon = section.icon;
  const body = stripHeading(content);

  const run = async (path, payload) => {
    setBusy(true);
    setError("");
    try {
      const updated = await api(path, { method: "POST", body: payload });
      onUpdated(updated);
      setMode("view");
      setInstruction("");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-olive-700 text-white"><Icon className="h-5 w-5" /></span>
          <h4 className="text-base font-bold text-olive-900">{section.label}</h4>
        </div>
        {editable && mode === "view" && (
          <div className="flex gap-2">
            <Button size="sm" variant="secondary" icon={Pencil} onClick={() => { setText(body); setMode("edit"); setError(""); }}>Modifier</Button>
            <Button size="sm" variant="accent" icon={Wand2} onClick={() => { setMode("ai"); setError(""); }}>Réécrire avec l'IA</Button>
          </div>
        )}
      </div>

      {mode === "view" && (
        <div className="md-content">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{body || "Section vide"}</ReactMarkdown>
        </div>
      )}

      {mode === "edit" && (
        <div className="space-y-3">
          <textarea className="input-field min-h-[220px] font-mono text-xs leading-relaxed" value={text} onChange={(e) => setText(e.target.value)} />
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="secondary" icon={X} onClick={() => setMode("view")}>Annuler</Button>
            <Button size="sm" icon={Save} loading={busy} onClick={() => run(`/proposals/${proposal.id}/sections/${section.key}/save`, { content: text })}>
              Enregistrer
            </Button>
          </div>
        </div>
      )}

      {mode === "ai" && (
        <div className="space-y-3">
          <div className="md-content rounded-xl bg-olive-50/60 p-4 opacity-80">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{body}</ReactMarkdown>
          </div>
          <input
            className="input-field"
            placeholder="Exemple : rends l'ouverture plus concise et mets en avant nos références bancaires"
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
          />
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="secondary" icon={X} onClick={() => setMode("view")}>Annuler</Button>
            <Button size="sm" icon={Wand2} loading={busy} disabled={!instruction.trim()}
              onClick={() => run(`/proposals/${proposal.id}/sections/${section.key}/edit`, { instruction })}>
              Appliquer l'instruction
            </Button>
          </div>
        </div>
      )}
      <div className="mt-3"><ErrorBox message={error} /></div>
    </Card>
  );
}

export default function ProposalTab({ proposal, canGenerate, running, onGenerate, onProposalChange }) {
  if (!proposal) {
    return (
      <EmptyState
        icon={FileText} title="Aucune proposition générée"
        text="Le rédacteur et le relecteur (CrewAI) produisent une proposition fondée uniquement sur la matrice de preuves. Disponible après la recherche prospect."
        action={<Button icon={Users} disabled={!canGenerate} loading={running === "generate"} onClick={onGenerate}>Générer la proposition</Button>}
      />
    );
  }

  const sections = proposal.content_sections || {};
  const known = SECTIONS.filter((s) => sections[s.key]);
  const extras = Object.keys(sections).filter((k) => !SECTIONS.some((s) => s.key === k));

  return (
    <div className="space-y-6">
      <Card className="flex flex-wrap items-center justify-between gap-4 p-5">
        <div className="flex flex-wrap items-center gap-3">
          <Badge tone={proposal.status === "approved" ? "green" : "amber"} icon={proposal.status === "approved" ? CheckCircle2 : AlertTriangle}>
            {proposal.status === "approved" ? "Validée par le relecteur" : "À relire par un humain"}
          </Badge>
          <Badge tone="olive" icon={Users}>{proposal.iterations} itération(s) rédacteur et relecteur</Badge>
        </div>
        <Button variant="secondary" size="sm" icon={Users} loading={running === "generate"} onClick={onGenerate}>Régénérer</Button>
      </Card>

      {proposal.review_feedback && proposal.status !== "approved" && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          <p className="mb-1 font-bold">Remarques du relecteur</p>
          <p className="whitespace-pre-line">{proposal.review_feedback}</p>
        </div>
      )}

      {known.map((s) => (
        <SectionCard key={s.key} proposal={proposal} section={s} content={sections[s.key]} editable onUpdated={onProposalChange} />
      ))}
      {extras.map((k) => (
        <SectionCard key={k} proposal={proposal} section={{ key: k, label: "Contenu complet", icon: FileText }} content={sections[k]} editable={false} onUpdated={onProposalChange} />
      ))}
    </div>
  );
}