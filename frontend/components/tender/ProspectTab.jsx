import { Brain, Building2, TrendingUp, Swords, Handshake, FolderKanban, Banknote } from "lucide-react";
import { Badge, Button, Card, EmptyState, SectionTitle } from "../ui";
import { clean } from "@/lib/format";

function Chips({ items, tone = "olive" }) {
  const list = (items || []).filter((x) => clean(x, ""));
  if (!list.length) return <p className="text-sm text-olive-400">Aucune donnée trouvée</p>;
  return (
    <div className="flex flex-wrap gap-2">
      {list.map((item, i) => <Badge key={i} tone={tone}>{item}</Badge>)}
    </div>
  );
}

function Field({ icon: Icon, label, children }) {
  return (
    <div>
      <p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-olive-500">
        <Icon className="h-4 w-4" /> {label}
      </p>
      {children}
    </div>
  );
}

const CONFIDENCE = { low: ["Confiance faible", "amber"], medium: ["Confiance moyenne", "blue"], high: ["Confiance élevée", "green"] };

export default function ProspectTab({ prospect, insights, canRun, running, onRunResearch, onRunInsights }) {
  const conf = CONFIDENCE[insights?.confidence] || ["Confiance non précisée", "gray"];
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card className="p-6">
        <SectionTitle icon={Building2} title="Profil du prospect" subtitle="Agent ReAct, recherche web via serveur MCP" />
        {!prospect ? (
          <div className="mt-6">
            <EmptyState
              icon={Brain} title="Recherche non lancée"
              text="L'agent explore le web pour constituer le profil de l'organisation. Disponible après qualification."
              action={<Button icon={Brain} disabled={!canRun} loading={running === "research"} onClick={onRunResearch}>Lancer la recherche prospect</Button>}
            />
          </div>
        ) : (
          <div className="mt-6 space-y-6">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field icon={Building2} label="Entreprise"><p className="font-semibold text-olive-900">{clean(prospect.company_name)}</p></Field>
              <Field icon={TrendingUp} label="Chiffre d'affaires"><p className="font-semibold text-olive-900">{clean(prospect.estimated_revenue)}</p></Field>
            </div>
            <Field icon={Handshake} label="Partenaires clés"><Chips items={prospect.key_partners} /></Field>
            <Field icon={FolderKanban} label="Projets passés"><Chips items={prospect.past_projects} tone="blue" /></Field>
            {clean(prospect.research_notes, "") && (
              <p className="rounded-xl bg-olive-50/70 p-4 text-sm leading-relaxed text-olive-800">{prospect.research_notes}</p>
            )}
            <Button variant="secondary" size="sm" icon={Brain} disabled={!canRun} loading={running === "research"} onClick={onRunResearch}>
              Relancer la recherche
            </Button>
          </div>
        )}
      </Card>

      <Card className="p-6">
        <SectionTitle icon={Swords} title="Budget et concurrence" subtitle="Agent d'estimation et de positionnement" />
        {!insights ? (
          <div className="mt-6">
            <EmptyState
              icon={Swords} title="Analyse non lancée"
              text="Estimation de la fourchette budgétaire et des concurrents probables."
              action={<Button icon={Swords} disabled={!canRun} loading={running === "insights"} onClick={onRunInsights}>Lancer l'analyse</Button>}
            />
          </div>
        ) : (
          <div className="mt-6 space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-olive-700 p-5 text-white">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-olive-200">Fourchette estimée</p>
                <p className="mt-1 text-xl font-extrabold">{clean(insights.estimated_budget_range, "À confirmer")}</p>
              </div>
              <Badge tone={conf[1]}>{conf[0]}</Badge>
            </div>
            <Field icon={Banknote} label="Positionnement conseillé">
              <p className="text-sm leading-relaxed text-olive-800">{clean(insights.competitive_positioning, "Non disponible")}</p>
            </Field>
            <Field icon={Swords} label="Concurrents probables"><Chips items={insights.likely_competitors} tone="amber" /></Field>
            <Button variant="secondary" size="sm" icon={Swords} disabled={!canRun} loading={running === "insights"} onClick={onRunInsights}>
              Relancer l'analyse
            </Button>
          </div>
        )}
      </Card>
    </div>
  );
}