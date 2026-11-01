"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Mail, Lock, User, UserPlus, Loader2 } from "lucide-react";
import AuthShell, { Field } from "@/components/AuthShell";
import { ErrorBox } from "@/components/ui";
import { useAuth } from "@/lib/auth";

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({ name: "", email: "", password: "", confirm: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const set = (key) => (e) => setForm((prev) => ({ ...prev, [key]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (form.password !== form.confirm) return setError("Les deux mots de passe ne correspondent pas.");
    setLoading(true);
    try {
      await register(form.name, form.email, form.password);
      router.replace("/dashboard");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell title="Créer un compte" subtitle="Rejoignez la plateforme et pilotez vos réponses aux appels d'offres.">
      <form onSubmit={submit} className="space-y-4">
        <Field icon={User} label="Nom complet" type="text" required placeholder="Prénom et nom" value={form.name} onChange={set("name")} autoComplete="name" />
        <Field icon={Mail} label="Adresse email" type="email" required placeholder="prenom.nom@olivesoft.com" value={form.email} onChange={set("email")} autoComplete="email" />
        <Field icon={Lock} label="Mot de passe" type="password" required placeholder="8 caractères minimum" value={form.password} onChange={set("password")} autoComplete="new-password" />
        <Field icon={Lock} label="Confirmer le mot de passe" type="password" required placeholder="Répétez le mot de passe" value={form.confirm} onChange={set("confirm")} autoComplete="new-password" />
        <ErrorBox message={error} />
        <button type="submit" disabled={loading} className="btn-brand">
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />}
          Créer mon compte
        </button>
      </form>
      <p className="mt-6 text-center text-sm text-olive-600">
        Vous avez déjà un compte ?{" "}
        <Link href="/login" className="font-bold text-olive-800 underline decoration-brand-teal decoration-2 underline-offset-4">Se connecter</Link>
      </p>
    </AuthShell>
  );
}