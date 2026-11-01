import { Radar, ScanSearch, ShieldCheck, Brain, FileText, Check, X } from "lucide-react";
import { cx } from "../ui";

const STEPS = [
  { label: "Détection", icon: Radar },
  { label: "Extraction", icon: ScanSearch },
  { label: "Qualification", icon: ShieldCheck },
  { label: "Prospect", icon: Brain },
  { label: "Proposition", icon: FileText },
];

function progress(status) {
  switch (status) {
    case "extracted": return { done: 2, failedAt: null };
    case "qualified": return { done: 3, failedAt: null };
    case "researched": return { done: 4, failedAt: null };
    case "drafted": return { done: 5, failedAt: null };
    case "rejected_low_score":
    case "rejected_expired": return { done: 2, failedAt: 2 };
    case "rejected_irrelevant":
    case "extraction_failed": return { done: 1, failedAt: 1 };
    default: return { done: 1, failedAt: null };
  }
}

export default function PipelineStepper({ status }) {
  const { done, failedAt } = progress(status);
  return (
    <div className="flex items-center overflow-x-auto py-2">
      {STEPS.map(({ label, icon: Icon }, i) => {
        const state = failedAt === i ? "failed" : i < done ? "done" : i === done ? "current" : "pending";
        const circle = {
          done: "bg-olive-700 text-white",
          current: "bg-sand-300 text-olive-900 ring-4 ring-sand-200",
          failed: "bg-red-600 text-white",
          pending: "bg-olive-100 text-olive-400",
        }[state];
        return (
          <div key={label} className="flex items-center">
            <div className="flex flex-col items-center gap-2 px-2">
              <span className={cx("flex h-11 w-11 items-center justify-center rounded-full transition", circle)}>
                {state === "done" ? <Check className="h-5 w-5" /> : state === "failed" ? <X className="h-5 w-5" /> : <Icon className="h-5 w-5" />}
              </span>
              <span className={cx("text-xs font-semibold", state === "pending" ? "text-olive-400" : "text-olive-800")}>{label}</span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={cx("mb-6 h-0.5 w-10 sm:w-16", i < done - 1 ? "bg-olive-600" : "bg-olive-100")} />
            )}
          </div>
        );
      })}
    </div>
  );
}