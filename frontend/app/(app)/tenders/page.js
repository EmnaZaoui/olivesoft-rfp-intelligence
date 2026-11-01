"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Search, Plus, Eye, FileSearch, ArrowUpDown, PlayCircle } from "lucide-react";
import { api } from "@/lib/api";
import DetectModal from "@/components/DetectModal";
import { Badge, Button, Card, EmptyState, ErrorBox, PageHeader, PageLoader, ProgressBar } from "@/components/ui";
import { STATUS, STATUS_GROUPS, clean, daysLeft, formatDate, sourceLabel } from "@/lib/format";
import ResumeModal from "@/components/ResumeModal";

export default function TendersPage() {
  const router = useRouter();
  const [tenders, setTenders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [group, setGroup] = useState("all");
  const [sortBy, setSortBy] = useState("recent");
  const [modal, setModal] = useState(false);

  const [resume, setResume] = useState(false);
  const pending = useMemo(
    () => tenders.filter((t) => ["new", "extracted", "qualified", "researched"].includes(t.status)),
    [tenders]
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setTenders(await api("/tenders/"));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    const allowed = group === "all" ? null : STATUS_GROUPS.find((g) => g.key === group).statuses;
    const list = tenders.filter((t) => {
      if (t.status === "archived") return false;
      if (allowed && !allowed.includes(t.status)) return false;
      if (!q) return true;
      return [t.title, t.issuing_organization, t.sector].some((v) => (v || "").toLowerCase().includes(q));
    });
    if (sortBy === "score") list.sort((a, b) => (b.qualification_score ?? -1) - (a.qualification_score ?? -1));
    else list.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
    return list;
  }, [tenders, query, group, sortBy]);

  const FILTERS = [{ key: "all", label: "Tous" }, ...STATUS_GROUPS.map((g) => ({ key: g.key, label: g.label }))];

  return (
    <div>
      <PageHeader
        title="Appels d'offres"
        subtitle="Toutes les opportunités détectées, avec leur score de qualification et leur statut dans le pipeline."
        actions={
          <>
            <Button variant="secondary" icon={PlayCircle} onClick={() => setResume(true)}>
              Reprendre les tenders en attente ({pending.length})
            </Button>
            <Button icon={Plus} onClick={() => setModal(true)}>Détecter des tenders</Button>
          </>
        }
      />

      <Card className="mb-6 flex flex-wrap items-center gap-3 p-4">
        <div className="relative min-w-[240px] flex-1">
          <Search className="absolute left-3.5 top-3 h-4 w-4 text-olive-400" />
          <input className="input-field pl-10" placeholder="Rechercher par titre, organisation ou secteur" value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
        <div className="flex gap-1 rounded-xl bg-olive-50 p-1">
          {FILTERS.map((f) => (
            <button key={f.key} type="button" onClick={() => setGroup(f.key)}
              className={`rounded-lg px-3.5 py-2 text-sm font-semibold transition ${group === f.key ? "bg-olive-700 text-white shadow-sm" : "text-olive-700 hover:bg-white"}`}>
              {f.label}
            </button>
          ))}
        </div>
        <Button variant="secondary" icon={ArrowUpDown} onClick={() => setSortBy(sortBy === "recent" ? "score" : "recent")}>
          {sortBy === "recent" ? "Plus récents" : "Meilleur score"}
        </Button>
      </Card>

      <ErrorBox message={error} />

      {loading ? (
        <PageLoader />
      ) : rows.length === 0 ? (
        <EmptyState icon={FileSearch} title="Aucun appel d'offres" text="Lancez une détection ou ajustez vos filtres."
          action={<Button icon={Plus} onClick={() => setModal(true)}>Détecter des tenders</Button>} />
      ) : (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-olive-50 text-xs uppercase tracking-wider text-olive-600">
                <tr>
                  <th className="px-6 py-3.5">Appel d'offres</th>
                  <th className="px-4 py-3.5">Secteur</th>
                  <th className="px-4 py-3.5">Date limite</th>
                  <th className="px-4 py-3.5">Score</th>
                  <th className="px-4 py-3.5">Source</th>
                  <th className="px-4 py-3.5">Statut</th>
                  <th className="px-6 py-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-olive-100">
                {rows.map((t) => {
                  const s = STATUS[t.status] || { label: t.status, tone: "gray" };
                  const days = daysLeft(t.deadline_date);
                  return (
                    <tr key={t.id} className="transition hover:bg-olive-50/50">
                      <td className="max-w-sm px-6 py-4">
                        <p className="line-clamp-2 font-semibold text-olive-900">{clean(t.title, "Tender en cours d'analyse")}</p>
                        <p className="mt-0.5 truncate text-xs text-olive-500">{clean(t.issuing_organization)}</p>
                      </td>
                      <td className="px-4 py-4 text-olive-700">{clean(t.sector)}</td>
                      <td className="whitespace-nowrap px-4 py-4 text-olive-700">
                        {t.deadline_date ? formatDate(t.deadline_date) : clean(t.deadline)}
                        {days !== null && days >= 0 && days <= 7 && <Badge tone="red" className="ml-2">J{days === 0 ? "" : `+${days}`}</Badge>}
                      </td>
                      <td className="w-36 px-4 py-4">
                        {t.qualification_score != null ? (
                          <>
                            <p className="mb-1 text-xs font-bold text-olive-800">{Math.round(t.qualification_score)}/100</p>
                            <ProgressBar value={t.qualification_score} />
                          </>
                        ) : <span className="text-xs text-olive-400">Non évalué</span>}
                      </td>
                      <td className="px-4 py-4"><Badge tone="olive">{sourceLabel(t.source)}</Badge></td>
                      <td className="px-4 py-4"><Badge tone={s.tone}>{s.label}</Badge></td>
                      <td className="px-6 py-4 text-right">
                        <Link href={`/tenders/${t.id}`}>
                          <Button size="sm" variant="secondary" icon={Eye}>Voir les détails</Button>
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="border-t border-olive-100 bg-olive-50/50 px-6 py-3 text-xs text-olive-600">{rows.length} résultat(s)</div>
        </Card>
      )}

      <DetectModal
        open={modal}
        onClose={() => setModal(false)}
        onDone={(created) => {
          if (created && created.id) router.push(`/tenders/${created.id}`);
          else load();
        }}
      />
       <ResumeModal open={resume} onClose={() => setResume(false)} tenders={pending} onDone={load} />
    </div>
  );
}