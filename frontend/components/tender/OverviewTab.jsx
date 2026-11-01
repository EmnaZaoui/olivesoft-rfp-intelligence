import { Building2, Layers, Wallet, CalendarClock, ExternalLink, ListChecks, CheckCircle2, XCircle, HelpCircle, AlertTriangle } from "lucide-react";
import { Badge, Card, EmptyState, Gauge, ProgressBar, SectionTitle } from "../ui";
import { clean, daysLeft, formatDate, sourceLabel } from "@/lib/format";

function InfoItem({ icon: Icon, label, value }) {
  return (
    <div className="flex items-start gap-3">
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-olive-50 text-olive-700">
        <Icon className="h-5 w-5" />
      </span>
      <div className="min-w-0">
        <p className="text-xs font-semibold uppercase tracking-wider text-olive-500">{label}</p>
        <p className="break-words text-sm font-semibold text-olive-900">{value}</p>
      </div>
    </div>
  );
}

function Criterion({ label, value, detail }) {
  const state = value === true ? "ok" : value === false ? "ko" : "na";
  const Icon = { ok: CheckCircle2, ko: XCircle, na: HelpCircle }[state];
  const color = { ok: "text-emerald-600", ko: "text-red-600", na: "text-olive-400" }[state];
  return (
    <div className="flex items-center gap-3 rounded-xl border border-olive-100 p-3">
      <Icon className={`h-5 w-5 ${color}`} />
      <div>
        <p className="text-sm font-semibold text-olive-900">{label}</p>
        <p className="text-xs text-olive-500">{detail}</p>
      </div>
    </div>
  );
}

export default function OverviewTab({ tender, matrix }) {
  const covered = matrix.filter((m) => m.covered).length;
  const coverage = matrix.length ? Math.round((100 * covered) / matrix.length) : 0;
  const days = daysLeft(tender.deadline_date);
  const reasons = tender.qualification_reasons || [];

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <SectionTitle icon={Layers} title="Informations extraites" subtitle="Champs structurés par le LLM à partir du texte source" />
        <div className="mt-6 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <InfoItem icon={Building2} label="Organisation" value={clean(tender.issuing_organization)} />
          <InfoItem icon={Layers} label="Secteur" value={clean(tender.sector)} />
          <InfoItem icon={Wallet} label="Budget" value={clean(tender.estimated_budget)} />
          <InfoItem
            icon={CalendarClock} label="Date limite"
            value={clean(tender.deadline) + (days !== null ? (days < 0 ? " (expiré)" : ` (dans ${days} j)`) : "")}
          />
        </div>
        {tender.summary && <p className="mt-6 rounded-xl bg-olive-50/70 p-4 text-sm leading-relaxed text-olive-800">{tender.summary}</p>}
        <div className="mt-4 flex flex-wrap items-center gap-3 text-sm text-olive-600">
          <Badge tone="olive">Source : {sourceLabel(tender.source)}</Badge>
          {tender.source_url && tender.source_url.startsWith("http") && (
            <a href={tender.source_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 font-semibold text-olive-700 hover:underline">
              Ouvrir la source <ExternalLink className="h-4 w-4" />
            </a>
          )}
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="p-6 lg:col-span-2">
          <SectionTitle icon={ListChecks} title="Critères de qualification" subtitle="Score pondéré : fit technique 50%, budget 20%, secteur 15%, délai 15%" />
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            <Criterion
              label="Fit technique" value={tender.technical_fit_score === null || tender.technical_fit_score === undefined ? null : tender.technical_fit_score >= 35}
              detail={tender.technical_fit_score != null ? `Score moyen des exigences : ${Math.round(tender.technical_fit_score)}/100` : "Non évalué"}
            />
            <Criterion label="Budget suffisant" value={tender.budget_sufficient} detail={clean(tender.estimated_budget)} />
            <Criterion label="Secteur stratégique" value={tender.sector_strategic} detail={clean(tender.sector)} />
            <Criterion label="Délai réalisable" value={tender.deadline_feasible} detail={days !== null ? `${days} jour(s) restants` : "Date non identifiée"} />
          </div>
          {tender.urgent_deadline_alert && (
            <div className="mt-4 flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">
              <AlertTriangle className="h-5 w-5" /> Échéance très proche : à traiter en priorité.
            </div>
          )}
          {reasons.length > 0 && (
            <ul className="mt-4 space-y-2 text-sm text-olive-700">
              {reasons.map((r, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-sand-400" />
                  {r}
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card className="flex flex-col items-center justify-center p-6 text-center">
          <p className="mb-4 text-sm font-semibold text-olive-600">Couverture des exigences</p>
          <Gauge value={coverage} size={130} stroke={12} display={`${coverage}%`} label="couvert" color={coverage >= 40 ? "#4B5D2E" : "#B3402F"} />
          <p className="mt-4 text-sm text-olive-600">{covered} sur {matrix.length} exigences couvertes</p>
        </Card>
      </div>

      <Card className="overflow-hidden">
        <div className="p-6 pb-4">
          <SectionTitle icon={ListChecks} title="Matrice d'exigences" subtitle="Chaque exigence est confrontée aux CV et projets indexés, puis notée par un juge LLM" />
        </div>
        {matrix.length === 0 ? (
          <div className="p-6 pt-0">
            <EmptyState title="Aucune matrice disponible" text="Lancez la qualification pour calculer la couverture exigence par exigence." />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-olive-50 text-xs uppercase tracking-wider text-olive-600">
                <tr>
                  <th className="px-6 py-3">Exigence</th>
                  <th className="px-4 py-3">Couverture</th>
                  <th className="px-4 py-3">Score</th>
                  <th className="px-4 py-3">Référence OliveSoft</th>
                  <th className="px-6 py-3">Preuve concrète</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-olive-100">
                {matrix.map((m) => (
                  <tr key={m.id} className="align-top hover:bg-olive-50/40">
                    <td className="max-w-xs px-6 py-4 font-medium text-olive-900">{m.requirement_text}</td>
                    <td className="px-4 py-4">
                      <Badge tone={m.covered ? "green" : "amber"} icon={m.covered ? CheckCircle2 : AlertTriangle}>
                        {m.covered ? "Couverte" : "À approfondir"}
                      </Badge>
                    </td>
                    <td className="w-36 px-4 py-4">
                      <p className="mb-1 text-xs font-bold text-olive-800">{Math.round(m.score)}/100</p>
                      <ProgressBar value={m.score} />
                    </td>
                    <td className="px-4 py-4 text-olive-700">{clean(m.best_document_title, "Aucune")}</td>
                    <td className="max-w-xs px-6 py-4 text-olive-700">
                      {clean(m.concrete_evidence, "") || <span className="text-olive-400">{clean(m.justification, "Non disponible")}</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}