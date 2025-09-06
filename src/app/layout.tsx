import type { Metadata } from "next";
import localFont from "next/font/local";
import Script from 'next/script'
import { GA_TRACKING_ID, isGAEnabled } from '@/lib/gtag'
import Analytics from '@/components/analytics'
import "./globals.css";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "Exhibit Board - 展示情報掲示板",
  description: "個展・グループ展の開催情報を共有する掲示板サービス",
  openGraph: {
    title: "Exhibit Board - 展示情報掲示板",
    description: "個展・グループ展の開催情報を共有する掲示板サービス",
    url: "https://exhibit-board.vercel.app",
    siteName: "Exhibit Board",
    images: [
      {
        url: "/images/og-image.jpg",
        width: 1200,
        height: 630,
        alt: "Exhibit Board - 展示情報掲示板",
      },
    ],
    locale: "ja_JP",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Exhibit Board - 展示情報掲示板",
    description: "個展・グループ展の開催情報を共有する掲示板サービス",
    images: ["/images/og-image.jpg"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja">
      <head>
        {/* Google Analytics */}
        {isGAEnabled && GA_TRACKING_ID && (
          <>
            <Script
              strategy="afterInteractive"
              src={`https://www.googletagmanager.com/gtag/js?id=${GA_TRACKING_ID}`}
            />
            <Script
              id="google-analytics"
              strategy="afterInteractive"
              dangerouslySetInnerHTML={{
                __html: `
                  window.dataLayer = window.dataLayer || [];
                  function gtag(){dataLayer.push(arguments);}
                  gtag('js', new Date());
                  gtag('config', '${GA_TRACKING_ID}');
                `,
              }}
            />
          </>
        )}
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <Analytics />
        {children}
      </body>
    </html>
  );
}
