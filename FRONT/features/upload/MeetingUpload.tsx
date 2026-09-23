"use client";

import { DragEvent, FormEvent, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/services/api";

const allowed = ".mp3,.wav,.m4a,.ogg,.mp4,.mov,.webm,.mkv";

export function MeetingUpload() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [title, setTitle] = useState("");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const selectDropped = (event: DragEvent) => {
    event.preventDefault();
    setDragging(false);
    const next = event.dataTransfer.files[0];
    if (next) setFile(next);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!file) return setError("Выберите аудио- или видеофайл");
    setBusy(true); setError("");
    try {
      const meeting = await api.createMeeting(title, date);
      await api.upload(meeting.id, file);
      await api.process(meeting.id);
      router.push(`/meetings/${meeting.id}/processing`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось начать обработку");
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl">
      <div className="max-w-2xl"><p className="text-sm font-semibold text-moss">Новая запись</p><h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">Превратим разговор в результат</h1><p className="mt-3 text-sm leading-6 text-stone-500">Добавьте запись совещания. Aqylman выделит спикеров, решения, риски и поручения.</p></div>
      <form onSubmit={submit} className="mt-8 grid gap-6 lg:grid-cols-[1fr_300px]">
        <section className="rounded-[2rem] border border-line bg-white p-6 shadow-soft sm:p-8">
          <div className="grid gap-5 sm:grid-cols-[1fr_190px]">
            <label className="block"><span className="mb-2 block text-xs font-bold uppercase tracking-wider text-stone-400">Название совещания</span><input required minLength={2} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Например, Статус пилотного проекта" className="w-full rounded-xl border border-line bg-cream/50 px-4 py-3 text-sm outline-none transition focus:border-moss focus:ring-2 focus:ring-moss/10" /></label>
            <label className="block"><span className="mb-2 block text-xs font-bold uppercase tracking-wider text-stone-400">Дата</span><input required type="date" value={date} onChange={(e) => setDate(e.target.value)} className="w-full rounded-xl border border-line bg-cream/50 px-4 py-3 text-sm outline-none focus:border-moss" /></label>
          </div>

          <div onDragOver={(e) => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={selectDropped} onClick={() => inputRef.current?.click()} className={`mt-7 cursor-pointer rounded-[1.5rem] border-2 border-dashed px-6 py-12 text-center transition ${dragging ? "border-moss bg-emerald-50" : file ? "border-lime bg-lime/10" : "border-stone-200 bg-cream/50 hover:border-moss/50"}`}>
            <input ref={inputRef} hidden type="file" accept={allowed} onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-white text-2xl shadow-sm">{file ? "✓" : "↑"}</div>
            {file ? <><p className="mt-4 font-bold text-ink">{file.name}</p><p className="mt-1 text-xs text-stone-400">{(file.size / 1024 / 1024).toFixed(1)} МБ · нажмите, чтобы заменить</p></> : <><p className="mt-4 font-bold">Перетащите запись сюда</p><p className="mt-2 text-sm text-stone-400">или нажмите, чтобы выбрать файл</p><p className="mt-5 text-[11px] font-semibold uppercase tracking-wider text-stone-400">MP3 · WAV · M4A · MP4 · WEBM · до 500 МБ</p></>}
          </div>
          {error && <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
          <button disabled={busy} className="mt-6 w-full rounded-xl bg-ink px-5 py-3.5 text-sm font-bold text-white transition hover:bg-moss disabled:cursor-wait disabled:opacity-60">{busy ? "Загружаем и запускаем…" : "Начать обработку →"}</button>
        </section>

        <aside className="space-y-4">
          <div className="rounded-3xl bg-ink p-6 text-white"><p className="text-xs font-bold uppercase tracking-[.17em] text-lime">Приватность</p><h2 className="mt-4 text-lg font-bold">Ваши данные остаются вашими</h2><p className="mt-3 text-sm leading-6 text-white/60">Mock и будущие AI-модели работают локально. Внешние облачные API не обязательны.</p></div>
          <div className="rounded-3xl border border-line bg-white p-5"><p className="text-xs font-bold uppercase tracking-wider text-stone-400">Что получится</p><ul className="mt-4 space-y-3 text-sm text-stone-600">{["Транскрипт со спикерами", "Список поручений и сроков", "Краткое резюме и решения", "Экспорт PDF и DOCX"].map((item) => <li key={item} className="flex gap-3"><span className="text-moss">✓</span>{item}</li>)}</ul></div>
        </aside>
      </form>
    </div>
  );
}

