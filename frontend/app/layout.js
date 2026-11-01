import { Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";

const jakarta = Plus_Jakarta_Sans({ subsets: ["latin"], variable: "--font-jakarta" });

export const metadata = {
  title: "OliveSoft RFP Intelligence",
  description: "Détection d'appels d'offres, matching RAG et génération de propositions commerciales.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="fr">
      <body className={`${jakarta.variable} font-sans`}>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}