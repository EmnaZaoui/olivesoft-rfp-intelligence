import { api } from "./api";

export const STEP_LABEL = {
  extract: "Extraction",
  qualify: "Qualification et matching",
  research: "Recherche du prospect",
  insights: "Budget et concurrence",
  generate: "Génération de la proposition",
};

const PATH = {
  extract: (id) => `/tenders/${id}/extract`,
  qualify: (id) => `/tenders/${id}/qualify`,
  research: (id) => `/tenders/${id}/research`,
  insights: (id) => `/tenders/${id}/competitor-insights`,
  generate: (id) => `/proposals/tenders/${id}/generate`,
};

const STOP_REASON = {
  drafted: "Proposition déjà générée",
  rejected_low_score: "Rejeté : le score de qualification est insuffisant",
  rejected_expired: "Rejeté : la date limite est dépassée",
  rejected_irrelevant: "Rejeté : appel d'offres hors périmètre IT",
  extraction_failed: "Extraction impossible : texte source insuffisant",
};

/**
 * Lit le statut du tender et exécute uniquement les étapes restantes.
 * onStep(step, phase) est appelé avec phase "start" puis "done".
 * Retourne { status, finished, message }.
 */
export async function runPipeline(id, onStep = () => {}) {
  let insightsDone = false;

  for (let guard = 0; guard < 8; guard += 1) {
    const tender = await api(`/tenders/${id}`);
    const status = tender.status;
    let step = null;

    if (status === "new") step = "extract";
    else if (status === "extracted") step = "qualify";
    else if (status === "qualified") step = "research";
    else if (status === "researched") {
      if (!insightsDone) insightsDone = Boolean(await api(`/tenders/${id}/insights`));
      step = insightsDone ? "generate" : "insights";
    } else {
      return { status, finished: status === "drafted", message: STOP_REASON[status] || `Statut ${status}` };
    }

    onStep(step, "start");
    await api(PATH[step](id), { method: "POST" });
    if (step === "insights") insightsDone = true;
    onStep(step, "done");
  }
  return { status: "unknown", finished: false, message: "Nombre maximal d'étapes atteint" };
}