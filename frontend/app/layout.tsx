import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import BackgroundCanvas from "@/components/BackgroundCanvas";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "chord_ai",
  description: "음원 분석 + AI 편곡",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" className={`${inter.variable} h-full antialiased`}>
      <body className="min-h-full bg-black text-white">
        <BackgroundCanvas />
        <div className="relative z-10 min-h-screen flex flex-col">{children}</div>
      </body>
    </html>
  );
}
