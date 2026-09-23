"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Logo } from "@/components/Logo";

const links = [
  { href: "/", label: "Совещания", icon: "▦" },
  { href: "/meetings/new", label: "Новая запись", icon: "+" },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-[248px] flex-col border-r border-line bg-white px-5 py-7 lg:flex">
      <div className="px-2"><Logo /></div>
      <nav className="mt-12 space-y-2">
        {links.map((link) => {
          const active = link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
          return (
            <Link key={link.href} href={link.href} className={`flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-semibold transition ${active ? "bg-ink text-white" : "text-stone-500 hover:bg-cream hover:text-ink"}`}>
              <span className={`grid h-7 w-7 place-items-center rounded-lg text-base ${active ? "bg-white/10 text-lime" : "bg-stone-100"}`}>{link.icon}</span>
              {link.label}
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto rounded-3xl bg-cream p-4">
        <div className="mb-3 flex items-center gap-2 text-xs font-semibold text-moss"><span className="h-2 w-2 rounded-full bg-emerald-500" /> Локальный режим</div>
        <p className="text-xs leading-5 text-stone-500">Записи и транскрипты не покидают ваш контур.</p>
      </div>
    </aside>
  );
}

