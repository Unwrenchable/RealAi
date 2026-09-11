import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RealAI Console",
  description: "Local-first RealAI bot. You are the provider.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
