"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Bot, Send, X, Loader2, MessageCircle } from "lucide-react";
import { api } from "@/lib/api";

const SUGGESTIONS = [
  "Comment fonctionne la qualification ?",
  "Que signifie le score de couverture ?",
  "Comment reprendre un tender bloqué ?",
  "Quels tenders sont qualifiés ?",
];

const WELCOME = {
  role: "assistant",
  content: "Bonjour, je suis l'assistant OliveSoft RFP Intelligence. Je réponds aux questions sur la plateforme et sur vos appels d'offres.",
};

export default function Chatbot() {
  const [mounted, setMounted] = useState(false);
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([WELCOME]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);

  useEffect(() => setMounted(true), []);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, busy, open]);

  const send = async (text) => {
    const message = (text ?? input).trim();
    if (!message || busy) return;
    const history = messages.filter((m) => m !== WELCOME).slice(-6);
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setInput("");
    setBusy(true);
    try {
      const data = await api("/assistant/chat", { method: "POST", body: { message, history } });
      setMessages((prev) => [...prev, { role: "assistant", content: data.answer }]);
    } catch (e) {
      setMessages((prev) => [...prev, { role: "assistant", content: `Je n'ai pas pu répondre : ${e.message}` }]);
    } finally {
      setBusy(false);
    }
  };

  const panel = open && (
    <div className="fixed bottom-4 left-4 z-[60] flex h-[34rem] w-[calc(100vw-2rem)] max-w-[24rem] flex-col overflow-hidden rounded-2xl border border-olive-100 bg-white shadow-2xl animate-fade-up lg:left-[19rem]">
      <div className="brand-pattern flex items-center justify-between px-4 py-3.5 text-white">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-brand-teal to-brand-lime text-brand-ink">
            <Bot className="h-5 w-5" />
          </span>
          <div className="leading-tight">
            <p className="text-sm font-bold">Assistant OliveSoft</p>
            <p className="text-[11px] text-brand-teal">Limité au contexte de la plateforme</p>
          </div>
        </div>
        <button type="button" onClick={() => setOpen(false)} className="rounded-lg p-1.5 text-white/80 hover:bg-white/10">
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto bg-sand-50 p-4">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[85%] whitespace-pre-line rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
              m.role === "user" ? "rounded-br-sm bg-olive-800 text-white" : "rounded-bl-sm border border-olive-100 bg-white text-olive-900"}`}>
              {m.content}
            </div>
          </div>
        ))}
        {busy && (
          <div className="flex items-center gap-2 text-xs text-olive-500">
            <Loader2 className="h-4 w-4 animate-spin" /> L'assistant réfléchit
          </div>
        )}
        {messages.length === 1 && (
          <div className="flex flex-wrap gap-2 pt-1">
            {SUGGESTIONS.map((s) => (
              <button key={s} type="button" onClick={() => send(s)}
                className="rounded-full border border-olive-200 bg-white px-3 py-1.5 text-xs font-semibold text-olive-700 transition hover:border-brand-cyan hover:bg-olive-50">
                {s}
              </button>
            ))}
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form onSubmit={(e) => { e.preventDefault(); send(); }} className="flex items-center gap-2 border-t border-olive-100 bg-white p-3">
        <input className="input-field rounded-full" placeholder="Posez votre question" value={input} onChange={(e) => setInput(e.target.value)} maxLength={600} />
        <button type="submit" disabled={busy || !input.trim()}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-r from-brand-teal to-brand-cyan text-brand-ink transition hover:brightness-105 disabled:opacity-50">
          <Send className="h-4 w-4" />
        </button>
      </form>
    </div>
  );

  return (
    <>
      <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-white">
          <Bot className="h-4 w-4 text-brand-teal" /> Assistant OliveSoft
        </div>
        <p className="mt-1.5 text-xs leading-relaxed text-olive-200">
          Une question sur la plateforme, un score ou le pipeline ? Posez-la ici.
        </p>
        <button type="button" onClick={() => setOpen(true)}
          className="mt-3 flex w-full items-center justify-center gap-2 rounded-full bg-gradient-to-r from-brand-teal to-brand-cyan px-4 py-2 text-xs font-extrabold uppercase tracking-wider text-brand-ink transition hover:brightness-105">
          <MessageCircle className="h-4 w-4" /> Discuter
        </button>
      </div>
      {mounted && panel ? createPortal(panel, document.body) : null}
    </>
  );
}