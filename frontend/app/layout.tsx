import type { Metadata } from "next";

import { AppShell } from "@/components/app-shell";
import "./globals.css";


export const metadata: Metadata = {
  title: "ResearchMind",
  description: "AI knowledge engine with document indexing, hybrid search, and grounded Q&A.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
