export function Logo() {
  return (
    <div className="flex items-center gap-3">
      <div className="grid h-10 w-10 place-items-center rounded-2xl bg-ink text-lime shadow-sm">
        <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M5 7h14M5 12h9M5 17h6" strokeLinecap="round" />
          <path d="m16 15 3 2-3 2v-4Z" fill="currentColor" stroke="none" />
        </svg>
      </div>
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-[.24em] text-stone-400">AI protocol</p>
        <p className="text-lg font-bold tracking-tight text-ink">AQYLMAN</p>
      </div>
    </div>
  );
}

