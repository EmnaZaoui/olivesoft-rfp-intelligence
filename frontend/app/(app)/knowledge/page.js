"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Upload, Search, Trash2, User, FolderKanban, FileText, RefreshCw, Database, Layers } from "lucide-react";
import { api } from "@/lib/api";
import { Badge, Button, Card, EmptyState, ErrorBox, PageHeader, PageLoader, ProgressBar, SectionTitle } from "@/components/ui";
import { clean, formatDate } from "@/lib/format";

const TYPE_META = {
  cv: { label: "CV", icon: User, tone: "blue" },
  project: { label: "Projet", icon: FolderKanban, tone: "olive" },
  reference: { label: "Référence", icon: FileText, tone: "gray" },
};

function MetaChips({ meta }) {
  const entries = [
    ["Rôle", meta.role], ["Client", meta.client_name], ["Secteur", meta.sector],
    ["Équipe", meta.team_size], ["Durée", meta.duration], ["Budget", meta.budget],
  ].filter(([, v]) => clean(v, ""));
  const techs = (meta.technologies || meta.key_skills || []).filter((x) => clean(x, "")).slice(0, 6);
  return (
    <div className="mt-3 space-y-2">
      {entries.length > 0 && (
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-olive-600">
          {entries.map(([k, v]) => <span key={k}><b className="text-olive-800">{k} :</b> {v}</span>)}
        </div>
      )}
      {techs.length > 0 && <div className="flex flex-wrap gap-1.5">{techs.map((t, i) => <Badge key={i} tone="gray">{t}</Badge>)}</div>}
    </div>
  );
}

export default function KnowledgePage() {
  const fileRef = useRef(null);
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [file, setFile] = useState(null);
  const [docType, setDocType] = useState("auto");
  const [uploading, setUploading] = useState(false);
  const [reindexing, setReindexing] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [searching, setSearching] = useState(false);

  const load = useCallback(async () => {
    try {
      setDocs(await api("/rag/documents"));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const upload = async () => {
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("doc_type", docType);
      await api("/rag/upload", { method: "POST", form });
      setFile(null);
      if (fileRef.current) fileRef.current.value = "";
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  };

  const reindex = async () => {
    setReindexing(true);
    setError("");
    try {
      await api("/rag/ingest/bootstrap", { method: "POST" });
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setReindexing(false);
    }
  };

  const remove = async (doc) => {
    if (!window.confirm(`Supprimer ${doc.title} de la base de connaissances ?`)) return;
    try {
      await api(`/rag/documents/${doc.id}`, { method: "DELETE" });
      await load();
    } catch (e) {
      setError(e.message);
    }
  };

  const search = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    setError("");
    try {
      setResults(await api("/rag/search", { method: "POST", body: { query, top_k: 6 } }));
    } catch (err) {
      setError(err.message);
    } finally {
      setSearching(false);
    }
  };

  const totalChunks = docs.reduce((s, d) => s + d.chunks, 0);

  return (
    <div>
      <PageHeader
        title="Base de connaissances"
        subtitle="CV, projets et rapports OliveSoft indexés dans pgvector. C'est cette base qui alimente le matching des exigences."
        actions={<Button variant="secondary" icon={RefreshCw} loading={reindexing} onClick={reindex}>Indexer le dossier</Button>}
      />
      <ErrorBox message={error} />

      <div className="mt-4 grid gap-6 lg:grid-cols-3">
        <Card className="p-6 lg:col-span-1">
          <SectionTitle icon={Upload} title="Ajouter un document" subtitle="PDF uniquement" />
          <div className="mt-5 space-y-4">
            <button type="button" onClick={() => fileRef.current?.click()}
              className="flex w-full flex-col items-center gap-2 rounded-xl border-2 border-dashed border-olive-200 bg-olive-50/50 px-4 py-8 text-center transition hover:border-olive-500 hover:bg-olive-50">
              <Upload className="h-7 w-7 text-olive-600" />
              <span className="text-sm font-semibold text-olive-800">{file ? file.name : "Choisir un fichier PDF"}</span>
              <span className="text-xs text-olive-500">CV, rapport de PFE ou fiche projet</span>
            </button>
            <input ref={fileRef} type="file" accept="application/pdf" className="hidden" onChange={(e) => setFile(e.target.files?.[0] || null)} />
            <select className="input-field" value={docType} onChange={(e) => setDocType(e.target.value)}>
              <option value="auto">Type détecté automatiquement</option>
              <option value="cv">CV</option>
              <option value="project">Projet ou PFE</option>
              <option value="reference">Référence</option>
            </select>
            <Button className="w-full" icon={Database} disabled={!file} loading={uploading} onClick={upload}>Indexer le document</Button>
            {uploading && <p className="text-xs text-olive-500">Extraction des métadonnées et calcul des embeddings en cours, cela peut prendre une minute.</p>}
          </div>
          <div className="mt-6 grid grid-cols-2 gap-3 border-t border-olive-100 pt-5 text-center">
            <div><p className="text-2xl font-extrabold text-olive-900">{docs.length}</p><p className="text-xs text-olive-500">Documents</p></div>
            <div><p className="text-2xl font-extrabold text-olive-900">{totalChunks}</p><p className="text-xs text-olive-500">Passages</p></div>
          </div>
        </Card>

        <Card className="p-6 lg:col-span-2">
          <SectionTitle icon={Search} title="Tester la recherche sémantique" subtitle="Tapez une compétence ou une exigence, par exemple FastAPI ou conformité bancaire" />
          <form onSubmit={search} className="mt-5 flex gap-3">
            <input className="input-field" placeholder="Exemple : développement backend FastAPI" value={query} onChange={(e) => setQuery(e.target.value)} />
            <Button type="submit" icon={Search} loading={searching}>Rechercher</Button>
          </form>
          <div className="mt-5 max-h-[420px] space-y-3 overflow-y-auto pr-1">
            {results === null && <p className="py-8 text-center text-sm text-olive-500">Les passages les plus proches apparaîtront ici avec leur score de similarité.</p>}
            {results && results.length === 0 && <p className="py-8 text-center text-sm text-olive-500">Aucun résultat. La base est peut-être vide.</p>}
            {results && results.map((r, i) => (
              <div key={i} className="rounded-xl border border-olive-100 p-4">
                <div className="mb-2 flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <Badge tone={(TYPE_META[r.doc_type] || TYPE_META.reference).tone}>{(TYPE_META[r.doc_type] || TYPE_META.reference).label}</Badge>
                    <span className="truncate text-sm font-semibold text-olive-900">{r.document_title}</span>
                  </div>
                  <span className="text-sm font-bold text-olive-800">{Math.round(r.score * 100)}%</span>
                </div>
                <ProgressBar value={r.score * 100} className="mb-3" />
                <p className="line-clamp-4 text-xs leading-relaxed text-olive-700">{r.content}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="mt-8">
        <h2 className="mb-4 flex items-center gap-2 text-lg font-bold text-olive-900"><Layers className="h-5 w-5 text-olive-600" /> Documents indexés</h2>
        {loading ? <PageLoader /> : docs.length === 0 ? (
          <EmptyState title="Base vide" text="Ajoutez vos CV et projets, ou placez-les dans backend/data/internal_docs puis cliquez sur Indexer le dossier." />
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {docs.map((d) => {
              const meta = TYPE_META[d.doc_type] || TYPE_META.reference;
              const Icon = meta.icon;
              return (
                <Card key={d.id} className="p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex min-w-0 items-center gap-3">
                      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-olive-700 text-white"><Icon className="h-5 w-5" /></span>
                      <div className="min-w-0">
                        <p className="truncate text-sm font-bold text-olive-900" title={d.title}>{d.title}</p>
                        <p className="text-xs text-olive-500">{d.chunks} passages, ajouté le {formatDate(d.created_at)}</p>
                      </div>
                    </div>
                    <button type="button" onClick={() => remove(d)} className="rounded-lg p-2 text-olive-400 transition hover:bg-red-50 hover:text-red-600" title="Supprimer">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                  <div className="mt-3"><Badge tone={meta.tone}>{meta.label}</Badge></div>
                  <MetaChips meta={d.metadata || {}} />
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}