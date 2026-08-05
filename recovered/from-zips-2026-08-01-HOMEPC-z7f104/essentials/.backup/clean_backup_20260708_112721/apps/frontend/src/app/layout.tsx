import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RealAI – The Limitless AI Assistant",
  description:
    "A professional AI chat interface powered by RealAI — multi-model, multi-capability, always available.",
  openGraph: {
    title: "RealAI",
    description: "Multi-model AI assistant with 17+ capabilities",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark h-full">
      <body className="h-full bg-slate-950 text-slate-100 antialiased font-sans overflow-hidden">
        {children}
      </body>
    </html>
  );
}
