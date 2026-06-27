import type { Metadata, Viewport } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'SurakshaNet AI — Indian Financial Crime Prevention',
  description:
    'Multi-agent intelligence platform for real-time scam detection, counterfeit currency identification, and police fraud investigation.',
  openGraph: {
    title: 'SurakshaNet AI',
    description: "India's First Unified Fraud Intelligence Platform",
    type: 'website',
  },
  robots: 'index, follow',
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* vis-network CDN — Critical for Police Intelligence Dashboard */}
        <script
          crossOrigin="anonymous"
          src="https://cdn.jsdelivr.net/npm/vis-network@9.1.9/dist/vis-network.min.js"
        />
        {/* Prevent FOUC by injecting minimal theme styles */}
        <style
          dangerouslySetInnerHTML={{
            __html: `
              html {
                color-scheme: dark;
                background-color: #0f172a;
              }
              body {
                background-color: #0f172a;
                color: #f1f5f9;
              }
            `,
          }}
        />
      </head>
      <body className="bg-slate-950 text-slate-50 antialiased">
        <main>{children}</main>
      </body>
    </html>
  );
}
