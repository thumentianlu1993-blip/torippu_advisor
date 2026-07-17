import type { Metadata } from "next";
import { Inter, Libre_Caslon_Text } from "next/font/google";
import { cn } from "@/lib/utils";
import "./globals.css";
import ClientToaster from "./components/ClientToaster";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const libreCaslon = Libre_Caslon_Text({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-libre-caslon",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Travel Planner",
  description: "Plan your next trip with curated experiences and collaborative decisions.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" className={cn(inter.variable, libreCaslon.variable)}>
      <body className="min-h-screen bg-background font-sans text-foreground antialiased">
        {children}
        <ClientToaster />
      </body>
    </html>
  );
}
