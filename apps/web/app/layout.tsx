import type { Metadata } from "next";
import { AuthProvider } from "./lib/auth";
import "./globals.css";

export const metadata: Metadata = {
  title: "FabriControl",
  description: "Controle de produção industrial: ordens, apontamento e indicadores",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
