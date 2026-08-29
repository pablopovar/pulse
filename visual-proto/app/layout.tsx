import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'povarchik.com — Observer Intelligence Audit',
  description: 'Interactive view of the August 22, 2026 SEO, GEO, and AEO audit for povarchik.com.',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
