import { Shield, Search, MessageSquare, BarChart3 } from "lucide-react";
import { ScanForm } from "@/components/scan-form";

export default function Home() {
  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-16">
      {/* Hero */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          <span className="text-[var(--accent)]">Venom</span>AI
        </h1>
        <p className="mt-4 text-lg text-[var(--muted)] max-w-2xl mx-auto">
          Scan web applications for OWASP Top 10 vulnerabilities. Get findings grouped by severity
          with AI-powered explanations in plain English.
        </p>
      </div>

      {/* Scan Form */}
      <ScanForm />

      {/* Features */}
      <div className="mt-16 grid grid-cols-1 gap-6 sm:grid-cols-3 max-w-4xl mx-auto">
        <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6 text-center">
          <Search className="h-8 w-8 mx-auto text-[var(--accent)] mb-3" />
          <h3 className="font-semibold">OWASP Top 10</h3>
          <p className="text-sm text-[var(--muted)] mt-1">
            Active scanning for all 10 OWASP vulnerability categories
          </p>
        </div>
        <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6 text-center">
          <BarChart3 className="h-8 w-8 mx-auto text-[var(--accent)] mb-3" />
          <h3 className="font-semibold">Severity Grouping</h3>
          <p className="text-sm text-[var(--muted)] mt-1">
            Findings organized from Critical to Informational with evidence
          </p>
        </div>
        <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6 text-center">
          <MessageSquare className="h-8 w-8 mx-auto text-[var(--accent)] mb-3" />
          <h3 className="font-semibold">AI Explanations</h3>
          <p className="text-sm text-[var(--muted)] mt-1">
            Chat with VenomAI to understand any finding in plain English
          </p>
        </div>
      </div>
    </div>
  );
}
