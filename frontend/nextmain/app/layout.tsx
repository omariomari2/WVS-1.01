import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "WVS - Web Vun Scan",
  description:
    "WVS - Web Vun Scan - Convert your single-page HTML projects to industry-standard React/TypeScript projects instantly. Format HTML, convert to JSX, and export complete TSX projects without npm commands.",
  keywords:
    "HTML to React, HTML to JSX, HTML to TypeScript, HTML formatter, JSX converter, React converter, TypeScript converter, HTML WVS",
  authors: [{ name: "WVS" }],
  robots: "index, follow",
  openGraph: {
    title: "WVS - Web Vun Scan",
    description:
      "Convert your single-page HTML projects to industry-standard React/TypeScript projects instantly. No npm commands required.",
    type: "website",
    siteName: "WVS",
  },
  twitter: {
    card: "summary_large_image",
    title: "WVS - Web Vun Scan",
    description:
      "Convert your single-page HTML projects to industry-standard React/TypeScript projects instantly. No npm commands required.",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
