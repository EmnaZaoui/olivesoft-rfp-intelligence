"use client";

import { useState } from "react";
import { Presentation, FileType, Download, Info } from "lucide-react";
import { apiDownload } from "@/lib/api";
import { Button, Card, EmptyState, ErrorBox } from "../ui";

const FORMATS = [
  {
    key: "pptx", icon: Presentation, title: "Présentation PowerPoint",
    text: "Deck éditable aux couleurs OliveSoft : synthèse chiffrée, sections de la proposition, matrice de couverture colorée.",
  },
  {
    key: "pdf", icon: FileType, title: "Document PDF",
    text: "Même contenu converti en PDF via LibreOffice, prêt à être envoyé au client.",
  },
];

export default function ExportsTab({ proposal }) {
  const [loading, setLoading] = useState(null);
  const [error, setError] = useState("");

  if (!proposal) {
    return <EmptyState icon={Download} title="Rien à exporter pour l'instant" text="Générez d'abord la proposition pour débloquer les exports PPTX et PDF." />;
  }

  const download = async (key) => {
    setLoading(key);
    setError("");
    try {
      await apiDownload(`/exports/proposals/${proposal.id}/${key}`, `proposition_olivesoft.${key}`);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-6 md:grid-cols-2">
        {FORMATS.map(({ key, icon: Icon, title, text }) => (
          <Card key={key} className="flex flex-col p-8">
            <span className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-olive-700 text-white shadow-lg">
              <Icon className="h-8 w-8" />
            </span>
            <h4 className="text-lg font-bold text-olive-900">{title}</h4>
            <p className="mt-2 flex-1 text-sm leading-relaxed text-olive-600">{text}</p>
            <Button size="lg" className="mt-6" icon={Download} loading={loading === key} onClick={() => download(key)}>
              Télécharger le {key.toUpperCase()}
            </Button>
          </Card>
        ))}
      </div>
      <ErrorBox message={error} />
      <p className="flex items-start gap-2 text-xs text-olive-500">
        <Info className="mt-0.5 h-4 w-4 shrink-0" />
        Les exports utilisent la version actuelle de la proposition, y compris vos modifications manuelles et réécritures IA.
      </p>
    </div>
  );
}