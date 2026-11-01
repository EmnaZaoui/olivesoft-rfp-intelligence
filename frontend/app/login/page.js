"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Mail, Lock, Eye, EyeOff, LogIn, Loader2 } from "lucide-react";
import AuthShell, { Field } from "@/components/AuthShell";
import { ErrorBox } from "@/components/ui";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login(email, password);
      router.replace("/dashboard");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell title="Bon retour" subtitle="Connectez-vous pour accéder à votre espace commercial.">
      <form onSubmit={submit} className="space-y-5">
        <Field icon={Mail} label="Adresse email" type="email" required placeholder="prenom.nom@olivesoft.com"
          value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
        <Field
          icon={Lock} label="Mot de passe" type={show ? "text" : "password"} required placeholder="Votre mot de passe"
          value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password"
          right={
            <button type="button" onClick={() => setShow(!show)} className="absolute right-4 top-1/2 -translate-y-1/2 text-olive-400 hover:text-olive-700">
              {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          }
        />
        <ErrorBox message={error} />
        <button type="submit" disabled={loading} className="btn-brand">
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <LogIn className="h-4 w-4" />}
          Se connecter
        </button>
      </form>
      <p className="mt-6 text-center text-sm text-olive-600">
        Pas encore de compte ?{" "}
        <Link href="/register" className="font-bold text-olive-800 underline decoration-brand-teal decoration-2 underline-offset-4">Créer un compte</Link>
      </p>
    </AuthShell>
  );
}