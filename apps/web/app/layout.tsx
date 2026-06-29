import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "@/components/AppShell";

export const metadata: Metadata = {
  title: "Australian University Intelligence",
  description: "Local-first public-data university intelligence prototype"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-AU">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
