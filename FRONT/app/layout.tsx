import type { Metadata } from "next";
import { Header } from "@/components/Header";
import { Sidebar } from "@/components/Sidebar";
import "./globals.css";

export const metadata: Metadata = {
  title: "Aqylman — протоколы совещаний",
  description: "Локальная система автопротоколирования совещаний",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ru">
      <body>
        <Sidebar />
        <div className="min-h-screen lg:pl-[248px]">
          <Header />
          <main className="px-5 py-8 lg:px-10 lg:py-10">{children}</main>
        </div>
      </body>
    </html>
  );
}

