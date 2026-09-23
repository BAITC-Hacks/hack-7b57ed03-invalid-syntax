import Link from "next/link";

export default function NotFound() {
  return <div className="mx-auto max-w-xl py-24 text-center"><p className="text-sm font-bold text-moss">404</p><h1 className="mt-3 text-3xl font-bold">Страница не найдена</h1><Link href="/" className="mt-6 inline-block rounded-xl bg-ink px-5 py-3 text-sm font-semibold text-white">На главную</Link></div>;
}

