"use client";

import { useRef, useState } from "react";
import { PlayCircle, Square, CheckCircle2, AlertTriangle, Loader2, Clock } from "lucide-react";
import { Badge, Button, Modal } from "./ui";
import { STATUS, clean } from "@/lib/format";
import { STEP_LABEL, runPipeline } from "@/lib/pipeline";

export default function ResumeModal({ open, onClose, tenders, onDone }) {
  const [state, setState] = useState({});
  const [running, setRunning] = useState(false);
  const stopRef = useRef(false);

  const patch = (id, value) => setState((prev) => ({ ...prev, [id]: { ...prev[id], ...value } }));

  const start = async () => {
    stopRef.current = false;
    setRunning(true);
    for (const t of tenders) {
      if (stopRef.current) break;
      patch(t.id, { phase: "running", step: "" });
      try {
        const res = await runPipeline(t.id, (step, phase) => phase === "start" && patch(t.id, { step }));
        patch(t.id, { phase: res.finished ? "done" : "stopped", message: res.message });
      } catch (e) {
        patch(t.id, { phase: "error", message: e.message });
      }
    }
    setRunning(false);
    onDone();
  };

  return (
    <Modal open={open} onClose={running ? () => {} : onClose} title="Reprendre les tenders en attente" wide>
      <p className="mb-4 text-sm text-olive-600">
        Chaque tender reprend à son étape actuelle, les étapes déjà faites ne sont pas refaites. Avec un LLM local, comptez
        plusieurs minutes par tender. Gardez cet onglet ouvert.
      </p>
      <div className="max-h-[50vh] space-y-2 overflow-y-auto pr-1">
        {tenders.length === 0 && <p className="py-8 text-center text-sm text-olive-500">Aucun tender en attente.</p>}
        {tenders.map((t) => {
          const s = STATUS[t.status] || { label: t.status, tone: "gray" };
          const st = state[t.id] || {};
          return (
            <div key={t.id} className="flex items-center justify-between gap-3 rounded-xl border border-olive-100 p-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-olive-900">{clean(t.title, "Tender en cours d'analyse")}</p>
                <p className="truncate text-xs text-olive-500">
                  {st.phase === "running" && (STEP_LABEL[st.step] ? `En cours : ${STEP_LABEL[st.step]}` : "Démarrage")}
                  {st.phase === "done" && "Proposition générée"}
                  {(st.phase === "stopped" || st.phase === "error") && st.message}
                  {!st.phase && clean(t.issuing_organization)}
                </p>
              </div>
              <div className="flex items-center gap-2">
                {st.phase === "running" && <Loader2 className="h-4 w-4 animate-spin text-olive-600" />}
                {st.phase === "done" && <CheckCircle2 className="h-5 w-5 text-emerald-600" />}
                {(st.phase === "stopped" || st.phase === "error") && <AlertTriangle className="h-5 w-5 text-amber-600" />}
                {!st.phase && <Clock className="h-4 w-4 text-olive-400" />}
                <Badge tone={s.tone}>{s.label}</Badge>
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-6 flex justify-end gap-3">
        {running ? (
          <Button variant="danger" icon={Square} onClick={() => { stopRef.current = true; }}>Arrêter après le tender en cours</Button>
        ) : (
          <>
            <Button variant="secondary" onClick={onClose}>Fermer</Button>
            <Button icon={PlayCircle} disabled={tenders.length === 0} onClick={start}>Reprendre tout</Button>
          </>
        )}
      </div>
    </Modal>
  );
}