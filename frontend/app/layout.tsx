import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL || "http://127.0.0.1:3000"
  ),
  title: "RealAI - The Limitless AI Assistant",
  description:
    "A professional AI chat interface powered by RealAI - multi-model, multi-capability, always available.",
  applicationName: "RealAI",
  icons: {
    icon: [{ url: "/favicon.svg", type: "image/svg+xml" }],
    shortcut: ["/favicon.svg"],
    apple: [{ url: "/favicon.svg" }],
  },
  manifest: "/site.webmanifest",
  openGraph: {
    title: "RealAI",
    description: "Multi-model AI assistant with 17+ capabilities",
    type: "website",
    siteName: "RealAI",
    images: [{ url: "/og.jpg" }],
  },
  twitter: {
    card: "summary",
    title: "RealAI",
    images: ["/og.jpg"],
  },
};

export const viewport: Viewport = {
  themeColor: "#07070b",
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
