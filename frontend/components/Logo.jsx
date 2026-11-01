"use client";

import { useState } from "react";

export function LeafMark({ className = "h-10 w-10" }) {
  return (
    <svg viewBox="0 0 48 48" className={className} fill="none" aria-hidden="true">
      <defs>
        <linearGradient id="leafGrad" x1="8" y1="6" x2="40" y2="42" gradientUnits="userSpaceOnUse">
          <stop stopColor="#1DE9B6" />
          <stop offset="1" stopColor="#84C441" />
        </linearGradient>
      </defs>
      <path d="M38 8C22 8 10 17 10 30c0 4 1.5 7 3 8.5 2.5 1.5 5 2 8 2C34 40.5 40 26 38 8Z" fill="url(#leafGrad)" />
      <path d="M13 39c4.5-8.5 11-14.5 19-18.5" stroke="#03224C" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

/**
 * variant "color" : /logo.png (fond blanc), variant "dark" : /logo-dark.png (fond sombre).
 * Si l'image est absente, un logo SVG de secours est affiché.
 */
export default function Logo({ variant = "color", className = "h-12" }) {
  const [failed, setFailed] = useState(false);
  const src = variant === "dark" ? "/logo-dark.png" : "/logo.png";

  if (failed) {
    const light = variant === "dark";
    return (
      <div className="flex items-center gap-2.5">
        <LeafMark className="h-10 w-10" />
        <span className={`text-xl font-extrabold tracking-tight ${light ? "text-white" : "text-olive-900"}`}>
          Olive<span className="text-brand-lime">Soft</span>
        </span>
      </div>
    );
  }
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={src} alt="OliveSoft" className={`${className} w-auto object-contain`} onError={() => setFailed(true)} />;
}