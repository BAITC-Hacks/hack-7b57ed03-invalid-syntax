import Link from "next/link";

export function EmptyState() {
  return (
    <div className="rounded-[2rem] border border-dashed border-stone-300 bg-white px-6 py-20 text-center">
      <div className="mx-auto grid h-16 w-16 place-items-center rounded-3xl bg-cream text-3xl">◉</div>
      <h2 className="mt-5 text-xl font-bold text-ink">Здесь появятся протоколы</h2>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-stone-500">Загрузите первую запись — система подготовит транскрипт, саммари и список поручений.</p>
      <Link href="/meetings/new" className="mt-6 inline-block rounded-xl bg-ink px-5 py-3 text-sm font-semibold text-white">Создать совещание</Link>
    </div>
  );
}

