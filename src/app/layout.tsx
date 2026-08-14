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
  metadataBase: new URL("https://exhibit.iruagaru.com"),
  title: "Exhibit Board｜全国の写真展・写真祭情報",
  description: "全国の写真展・写真祭を、会期・都道府県・展示タイプから探せる情報サイト。個展・グループ展から美術館の企画展、写真祭まで掲載しています。",
  alternates: {
    canonical: "/",
  },
  openGraph: {
    title: "Exhibit Board｜全国の写真展・写真祭情報",
    description: "個展・グループ展から美術館の企画展まで、全国の写真展を会期・地域から探せます。",
    url: "https://exhibit.iruagaru.com",
    siteName: "Exhibit Board",
    images: [
      {
        url: "/images/og-image.jpg",
        width: 1200,
        height: 630,
        alt: "Exhibit Board｜全国の写真展・写真祭情報",
      },
    ],
    locale: "ja_JP",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Exhibit Board｜全国の写真展・写真祭情報",
    description: "個展・グループ展から美術館の企画展まで、全国の写真展を会期・地域から探せます。",
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
                  gtag('config', '${GA_TRACKING_ID}', { send_page_view: false });
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
