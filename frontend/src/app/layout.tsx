import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VenomAI - OWASP Top 10 Security Scanner",
  description: "Scan web applications for OWASP Top 10 vulnerabilities with AI-powered explanations",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[var(--background)] text-[var(--foreground)] antialiased">
        <nav className="border-b border-[var(--card-border)] bg-[var(--card)]">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="flex h-14 items-center justify-between">
              <a href="/" className="flex items-center gap-2 font-bold text-lg">
                <span className="text-[var(--accent)]">Venom</span>
                <span>AI</span>
              </a>
              <div className="flex items-center gap-4">
                <a
                  href="/scans"
                  className="text-sm text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
                >
                  Scan History
                </a>
              </div>
            </div>
          </div>
        </nav>
        <main>{children}</main>
      </body>
    </html>
  );
}
