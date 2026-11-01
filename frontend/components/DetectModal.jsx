"use client";

import { useState } from "react";
import { Globe2, Search, Radar, PenLine } from "lucide-react";
import { api } from "@/lib/api";
import { Button, ErrorBox, Modal, cx } from "./ui";

const SOURCES = [
  { key: "opendata", icon: Globe2, title: "Banque mondiale", text: "API ouverte, avis datés et structurés. Le plus fiable." },
  { key: "apify", icon: Radar, title: "Apify", text: "Recherche Google, crawler et classifieur d'avis." },
  { key: "legacy", icon: Search, title: "Serper et Playwright", text: "Recherche ciblée sur vos technologies, scraping local." },
  { key: "manual", icon: PenLine, title: "Saisie manuelle", text: "Collez le texte d'un appel d'offres." },
];

const ENDPOINTS = {
  opendata: (n) => `/tenders/ingest/opendata?max_tenders=${n}`,
  apify: (n) => `/tenders/ingest/apify?max_tenders=${n}&pre_extract=true&source=google`,
  legacy: (n) => `/tenders/ingest/dynamic?max_tenders=${n}`,
};

export default function DetectModal({ open, onClose, onDone }) {
  const [source, setSource] = useState("opendata");
  const [count, setCount] = useState(5);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const submit = async () => {
    setLoading(true);
    setError("");
    setMessage("");
    try {
      if (source === "manual") {
        if (text.trim().length < 150) throw new Error("Collez le texte complet (au moins 150 caractères).");
        const created = await api("/tenders/ingest/manual", {
          method: "POST", body: { source: "manual_upload", raw_text: text },
        });
        onDone(created);
      } else {
        const created = await api(ENDPOINTS[source](count), { method: "POST" });
        if (!created.length) {
          setMessage("Aucun nouveau tender pertinent trouvé. Essayez une autre source ou relancez plus tard.");
        } else {
          onDone(null);
          onClose();
        }
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Détecter de nouveaux appels d'offres" wide>
      <div className="grid gap-3 sm:grid-cols-2">
        {SOURCES.map(({ key, icon: Icon, title, text: desc }) => (
          <button
            key={key}
            type="button"
            onClick={() => setSource(key)}
            className={cx(
              "flex items-start gap-3 rounded-xl border p-4 text-left transition",
              source === key ? "border-olive-600 bg-olive-50 ring-2 ring-olive-200" : "border-olive-100 hover:bg-olive-50/60"
            )}
          >
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-olive-700 text-white">
              <Icon className="h-5 w-5" />
            </span>
            <span>
              <span className="block text-sm font-bold text-olive-900">{title}</span>
              <span className="block text-xs text-olive-600">{desc}</span>
            </span>
          </button>
        ))}
      </div>

      <div className="mt-5">
        {source === "manual" ? (
          <textarea
            className="input-field min-h-[160px]"
            placeholder="Collez ici le texte complet de l'appel d'offres, avec la date limite et les exigences."
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        ) : (
          <label className="flex items-center gap-4 text-sm font-semibold text-olive-800">
            Nombre maximum de tenders
            <input
              type="number" min={1} max={20} value={count}
              onChange={(e) => setCount(Math.max(1, Math.min(20, Number(e.target.value) || 1)))}
              className="input-field w-24"
            />
          </label>
        )}
      </div>

      {source !== "manual" && (
        <p className="mt-3 text-xs text-olive-500">
          La détection inclut l'extraction par le LLM local. Comptez plusieurs minutes selon la source.
        </p>
      )}

      <div className="mt-4 space-y-3">
        <ErrorBox message={error} />
        {message && <p className="rounded-xl bg-sand-100 px-4 py-3 text-sm text-olive-800">{message}</p>}
      </div>

      <div className="mt-6 flex justify-end gap-3">
        <Button variant="secondary" onClick={onClose}>Fermer</Button>
        <Button icon={Radar} loading={loading} onClick={submit}>
          {source === "manual" ? "Ajouter le tender" : "Lancer la détection"}
        </Button>
      </div>
    </Modal>
  );
}