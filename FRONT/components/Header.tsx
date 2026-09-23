import Link from "next/link";
import { Logo } from "@/components/Logo";

export function Header() {
  return (
    <header className="sticky top-0 z-20 flex h-20 items-center justify-between border-b border-line/70 bg-cream/90 px-5 backdrop-blur lg:px-10">
      <div className="lg:hidden"><Logo /></div>
      <div className="hidden lg:block">
        <p className="text-xs font-semibold uppercase tracking-[.18em] text-stone-400">Рабочее пространство</p>
        <p className="mt-1 text-sm font-medium text-ink">Команда цифровой трансформации</p>
      </div>
      <Link href="/meetings/new" className="rounded-xl bg-ink px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-moss">+ Новое совещание</Link>
    </header>
  );
}

