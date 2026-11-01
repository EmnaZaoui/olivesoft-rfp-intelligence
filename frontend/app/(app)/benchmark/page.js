"use client";

import { useCallback, useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Play, Target, Medal, Info, CheckCircle2, XCircle } from "lucide-react";
import { api } from "@/lib/api";
import { Badge, Button, Card, EmptyState, ErrorBox, Gauge, PageHeader, PageLoader, SectionTitle } from "@/components/ui";
import { formatDateTime } from "@/lib/format";

const RANKS = [[1, 1], [2, 0.5], [3, 0.33], [5, 0.2]];

export default function BenchmarkPage() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [topK, setTopK] = useState(5);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setHistory(await api("/rag/benchmark/history"));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const run = async () => {
    setRunning(true);
    setError("");
    try {
      const data = await api(`/rag/benchmark/run?top_k=${topK}`, { method: "POST" });
      if (data.error) throw new Error(data.error);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  };

  const latest = history[0];
  const chartData = [...history].reverse().map((h) => ({
    date: formatDateTime(h.run_at), recall: h.recall_at_k, mrr: h.mrr,
  }));

  return (
    <div>
      <PageHeader
        title="Benchmark RAG"
        subtitle="Mesure objective de la précision du retrieval : retrouve-t-on le bon CV ou le bon projet pour chaque besoin ?"
        actions={
          <>
            <select className="input-field w-36" value={topK} onChange={(e) => setTopK(Number(e.target.value))}>
              {[1, 3, 5, 10].map((k) => <option key={k} value={k}>Top {k}</option>)}
            </select>
            <Button icon={Play} loading={running} onClick={run}>Lancer le benchmark</Button>
          </>
        }
      />
      <ErrorBox message={error} />

      {loading ? <PageLoader /> : !latest ? (
        <div className="mt-4">
          <EmptyState icon={Target} title="Aucun benchmark exécuté"
            text="Le jeu de test se trouve dans backend/data/rag_benchmark/test_set.json. Lancez le benchmark pour calculer Recall et MRR." />
        </div>
      ) : (
        <>
          <div className="mt-4 grid gap-6 md:grid-cols-3">
            <Card className="flex flex-col items-center p-6 text-center">
              <Gauge value={(latest.recall_at_k || 0) * 100} size={140} stroke={13} display={(latest.recall_at_k || 0).toFixed(2)} label="recall" />
              <p className="mt-4 font-bold text-olive-900">Recall at k</p>
              <p className="mt-1 text-xs text-olive-500">Part des documents attendus retrouvés dans les k premiers résultats</p>
            </Card>
            <Card className="flex flex-col items-center p-6 text-center">
              <Gauge value={(latest.mrr || 0) * 100} size={140} stroke={13} display={(latest.mrr || 0).toFixed(2)} label="mrr" color="#8A9A5B" />
              <p className="mt-4 font-bold text-olive-900">MRR</p>
              <p className="mt-1 text-xs text-olive-500">Rang moyen du premier bon document, plus c'est proche de 1 mieux c'est</p>
            </Card>
            <Card className="p-6">
              <SectionTitle icon={Info} title="Comment lire le MRR" />
              <p className="mt-3 text-xs text-olive-600">Un bon document en première position vaut 1, en deuxième 0,5, et ainsi de suite.</p>
              <div className="mt-4 space-y-2.5">
                {RANKS.map(([rank, value]) => (
                  <div key={rank} className="flex items-center gap-3 text-xs">
                    <span className="w-14 font-semibold text-olive-700">Rang {rank}</span>
                    <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-olive-100"><div className="h-full rounded-full bg-olive-600" style={{ width: `${value * 100}%` }} /></div>
                    <span className="w-9 text-right font-bold text-olive-800">{value}</span>
                  </div>
                ))}
              </div>
              <p className="mt-4 text-xs text-olive-500">Dernier run : {formatDateTime(latest.run_at)}, {latest.queries} requêtes</p>
            </Card>
          </div>

          {history.length > 1 && (
            <Card className="mt-6 p-6">
              <SectionTitle icon={Medal} title="Évolution des scores" subtitle="Comparez vos optimisations d'un run à l'autre" />
              <div className="mt-4 h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid stroke="#ECEFDF" vertical={false} />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#6E7F44" }} axisLine={false} tickLine={false} />
                    <YAxis domain={[0, 1]} tick={{ fontSize: 11, fill: "#6E7F44" }} axisLine={false} tickLine={false} />
                    <Tooltip />
                    <Line type="monotone" dataKey="recall" name="Recall" stroke="#4B5D2E" strokeWidth={3} dot={{ r: 4 }} />
                    <Line type="monotone" dataKey="mrr" name="MRR" stroke="#C4B170" strokeWidth={3} dot={{ r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>
          )}

          <Card className="mt-6 overflow-hidden">
            <div className="p-6 pb-4"><SectionTitle icon={Target} title="Détail par requête" subtitle="Vert : document attendu retrouvé. Gris : autre document" /></div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-olive-50 text-xs uppercase tracking-wider text-olive-600">
                  <tr><th className="px-6 py-3">Requête</th><th className="px-4 py-3">Attendu</th><th className="px-4 py-3">Résultats</th><th className="px-4 py-3">Recall</th><th className="px-6 py-3">Rang inverse</th></tr>
                </thead>
                <tbody className="divide-y divide-olive-100">
                  {latest.details.map((d, i) => (
                    <tr key={i} className="align-top">
                      <td className="max-w-xs px-6 py-4 font-medium text-olive-900">{d.query}</td>
                      <td className="px-4 py-4"><div className="flex flex-wrap gap-1.5">{d.expected.map((e) => <Badge key={e} tone="olive">{e}</Badge>)}</div></td>
                      <td className="px-4 py-4">
                        <div className="flex flex-wrap gap-1.5">
                          {d.retrieved.map((r, j) => <Badge key={j} tone={d.expected.includes(r) ? "green" : "gray"}>{r}</Badge>)}
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        {d.recall >= 1 ? <CheckCircle2 className="h-5 w-5 text-emerald-600" /> : d.recall > 0 ? <span className="font-bold text-amber-600">{d.recall}</span> : <XCircle className="h-5 w-5 text-red-500" />}
                      </td>
                      <td className="px-6 py-4 font-bold text-olive-800">{d.reciprocal_rank}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}