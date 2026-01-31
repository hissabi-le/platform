import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { Toaster } from "sonner";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const viewport: Viewport = {
  themeColor: "#0f172a",
  width: "device-width",
  initialScale: 1,
};

export const metadata: Metadata = {
  title: {
    default: "Hisabi | SMB Accounting for Lebanon",
    template: "%s | Hisabi",
  },
  description: "AI-powered accounting that speaks your language. Upload documents, get balance sheets, P&L, and inventory reports in seconds.",
  keywords: ["accounting", "SMB", "Lebanon", "bookkeeping", "financial statements", "inventory", "P&L", "balance sheet"],
  authors: [{ name: "Hisabi" }],
  creator: "Hisabi",
  publisher: "Hisabi",
  robots: {
    index: true,
    follow: true,
  },
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://hisabi.com",
    siteName: "Hisabi",
    title: "Hisabi | SMB Accounting for Lebanon",
    description: "AI-powered accounting that speaks your language. Upload documents, get balance sheets, P&L, and inventory reports in seconds.",
  },
  twitter: {
    card: "summary_large_image",
    title: "Hisabi | SMB Accounting for Lebanon",
    description: "AI-powered accounting that speaks your language.",
  },
  icons: {
    icon: "/favicon.ico",
    apple: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`} suppressHydrationWarning>
        <Providers>
          {children}
          <Toaster
            position="top-right"
            richColors
            toastOptions={{
              style: {
                borderRadius: "12px",
              },
            }}
          />
        </Providers>
      </body>
    </html>
  );
}
