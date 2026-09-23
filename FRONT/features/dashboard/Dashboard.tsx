"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { EmptyState } from "@/components/EmptyState";
import { StatusBadge } from "@/components/StatusBadge";
import { formatDate } from "@/lib/format";
import { api } from "@/services/api";
import type { MeetingListItem } from "@/types/meeting";

export function Dashboard() {
  const [meetings, setMeetings] = useState<MeetingListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.listMeetings().then(setMeetings).catch((e: Error) => setError(e.message)).finally(() => setLoading(false));
  }, []);

  const stats = useMemo(() => ({
    total: meetings.length,
    tasks: meetings.filter((m) => m.status === "completed").length * 2,
    processing: meetings.filter((m) => m.status === "processing").length,
  }), [meetings]);

  return (
    <div className="mx-auto max-w-7xl">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div><p className="text-sm font-semibold text-moss">Центр протоколов</p><h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">Добрый день</h1><p className="mt-2 text-sm text-stone-500">Все решения и поручения команды — в одном месте.</p></div>
        <p className="text-xs font-medium uppercase tracking-[.18em] text-stone-400">Данные обновлены сейчас</p>
      </div>

      <section className="mt-8 grid gap-4 md:grid-cols-3">
        {[
          ["Всего совещаний", stats.total, "за всё время"],
          ["Поручений найдено", stats.tasks, "в mock-протоколах"],
          ["В обработке", stats.processing, stats.processing ? "pipeline работает" : "очередь свободна"],
        ].map(([label, value, note], i) => (
          <article key={String(label)} className={`rounded-3xl p-6 ${i === 0 ? "bg-ink text-white" : "border border-line bg-white"}`}>
            <p className={`text-xs font-semibold uppercase tracking-[.15em] ${i === 0 ? "text-white/55" : "text-stone-400"}`}>{label}</p>
            <div className="mt-5 flex items-end justify-between"><strong className="text-4xl font-bold">{value}</strong><span className={`text-xs ${i === 0 ? "text-lime" : "text-stone-400"}`}>{note}</span></div>
          </article>
        ))}
      </section>

      <section className="mt-10">
        <div className="mb-4 flex items-center justify-between"><h2 className="text-xl font-bold">Последние совещания</h2><span className="text-xs text-stone-400">{meetings.length} записей</span></div>
        {loading ? <div className="h-64 animate-pulse rounded-[2rem] bg-white" /> : error ? <div className="rounded-3xl bg-red-50 p-6 text-sm text-red-700">{error}. Проверьте, что backend запущен.</div> : meetings.length === 0 ? <EmptyState /> : (
          <div className="overflow-hidden rounded-[2rem] border border-line bg-white">
            {meetings.map((meeting, index) => (
              <Link key={meeting.id} href={meeting.status === "processing" ? `/meetings/${meeting.id}/processing` : `/meetings/${meeting.id}`} className={`group flex flex-col gap-4 p-5 transition hover:bg-cream/70 sm:flex-row sm:items-center ${index ? "border-t border-line" : ""}`}>
                <div className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-cream text-sm font-bold text-moss">{meeting.id.toString().padStart(2, "0")}</div>
                <div className="min-w-0 flex-1"><h3 className="truncate font-bold group-hover:text-moss">{meeting.title}</h3><p className="mt-1 text-xs text-stone-400">{formatDate(meeting.meeting_date)} · {meeting.source_filename ?? "файл не загружен"}</p></div>
                {meeting.status === "processing" && <div className="w-28"><div className="h-1.5 overflow-hidden rounded-full bg-stone-100"><div className="h-full bg-lime" style={{ width: `${meeting.progress}%` }} /></div><p className="mt-1 text-[10px] text-stone-400">{meeting.progress}%</p></div>}
                <StatusBadge status={meeting.status} />
                <span className="text-stone-300 transition group-hover:translate-x-1 group-hover:text-ink">→</span>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

