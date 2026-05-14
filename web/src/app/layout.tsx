import type { Metadata } from "next";
import { EB_Garamond, Inter } from "next/font/google";
import { SiteHeader } from "@/components/site-header";
import "./globals.css";

const ebGaramond = EB_Garamond({
  variable: "--font-eb-garamond",
  subsets: ["latin"],
  display: "swap",
});

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Drømmevev — leggetidshistorier dere lager sammen",
  description:
    "Lag personlige bildebøker med barnet i hovedrollen. Drømmevev fra aiakaki.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="nb-NO"
      className={`${ebGaramond.variable} ${inter.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <SiteHeader />
        {children}
      </body>
    </html>
  );
}
