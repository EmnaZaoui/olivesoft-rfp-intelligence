export const clean = (value, fallback = "Non précisé") => {
  if (value === null || value === undefined) return fallback;
  const text = String(value).trim();
  return ["", "unknown", "none", "null"].includes(text.toLowerCase()) ? fallback : text;
};

export const formatDate = (iso) =>
  iso ? new Date(iso).toLocaleDateString("fr-FR", { day: "2-digit", month: "long", year: "numeric" }) : "Non précisée";

export const formatDateTime = (iso) =>
  iso
    ? new Date(iso).toLocaleString("fr-FR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })
    : "Non précisé";

export function daysLeft(iso) {
  if (!iso) return null;
  return Math.ceil((new Date(iso).getTime() - Date.now()) / 86400000);
}

export const initials = (name = "") =>
  name.split(" ").filter(Boolean).slice(0, 2).map((p) => p[0].toUpperCase()).join("") || "OS";

export const STATUS = {
  new: { label: "Nouveau", tone: "gray" },
  extracted: { label: "Extrait", tone: "blue" },
  qualified: { label: "Qualifié", tone: "green" },
  researched: { label: "Prospect analysé", tone: "olive" },
  drafted: { label: "Proposition prête", tone: "green" },
  rejected_low_score: { label: "Score insuffisant", tone: "red" },
  rejected_expired: { label: "Expiré", tone: "red" },
  rejected_irrelevant: { label: "Hors périmètre", tone: "red" },
  extraction_failed: { label: "Extraction échouée", tone: "red" },
  archived: { label: "Archivé", tone: "gray" },
};

export const STATUS_GROUPS = [
  { key: "qualified", label: "Qualifiés", color: "#84C441", statuses: ["qualified", "researched", "drafted"] },
  { key: "pending", label: "En attente", color: "#0E5A9E", statuses: ["new", "extracted"] },
  {
    key: "rejected", label: "Rejetés", color: "#B3402F",
    statuses: ["rejected_low_score", "rejected_expired", "rejected_irrelevant", "extraction_failed"],
  },
];

export const SOURCE_LABELS = {
  apify_search: "Apify",
  dynamic_search: "Serper",
  worldbank_api: "Banque mondiale",
  manual_upload: "Saisie manuelle",
  manual: "Saisie manuelle",
  ted_api: "TED",
};

export const sourceLabel = (s) => SOURCE_LABELS[s] || s || "Inconnue";