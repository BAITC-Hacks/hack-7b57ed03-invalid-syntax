"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { StatusBadge } from "@/components/StatusBadge";
import { formatDate, formatTime } from "@/lib/format";
import { api } from "@/services/api";
import type { Meeting } from "@/types/meeting";

type Tab = "summary" | "tasks" | "transcript" | "participants";

export function MeetingResult({ meetingId }: { meetingId: number }) {
  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [tab, setTab] = useState<Tab>("summary");
  const [error, setError] = useState("");
  useEffect(() => { api.getMeeting(meetingId).then(setMeeting).catch((e: Error) => setError(e.message)); }, [meetingId]);

  const rename = async (participantId: number, current: string) => {
    const displayName = window.prompt("Имя участника", current)?.trim();
    if (!displayName) return;
    await api.renameParticipant(meetingId, participantId, displayName);
    setMeeting(await api.getMeeting(meetingId));
  };

  if (error) return <div className="mx-auto max-w-4xl rounded-3xl bg-red-50 p-6 text-red-700">{error}</div>;
  if (!meeting) return <div className="mx-auto h-[500px] max-w-6xl animate-pulse rounded-[2rem] bg-white" />;
  if (meeting.status === "processing") return <div className="mx-auto max-w-xl rounded-3xl bg-white p-8 text-center"><h1 className="text-xl font-bold">Обработка ещё идёт</h1><Link className="mt-4 inline-block font-semibold text-moss underline" href={`/meetings/${meeting.id}/processing`}>Открыть прогресс</Link></div>;

  const tabs: [Tab, string, number | null][] = [["summary", "Саммари", null], ["tasks", "Поручения", meeting.tasks.length], ["transcript", "Транскрипт", meeting.transcript.length], ["participants", "Участники", meeting.participants.length]];
  return (
    <div className="mx-auto max-w-7xl">
      <div className="flex flex-col justify-between gap-5 xl:flex-row xl:items-start">
        <div><Link href="/" className="text-xs font-semibold text-stone-400 hover:text-moss">← Все совещания</Link><div className="mt-4 flex items-center gap-3"><h1 className="text-3xl font-bold tracking-tight">{meeting.title}</h1><StatusBadge status={meeting.status} /></div><p className="mt-2 text-sm text-stone-500">{formatDate(meeting.meeting_date)} · {meeting.participants.length} участника · {meeting.source_filename}</p></div>
        <div className="flex flex-wrap gap-2"><a href={api.exportUrl(meeting.id, "pdf")} className="rounded-xl border border-line bg-white px-4 py-2.5 text-sm font-semibold hover:border-moss">↓ PDF</a><a href={api.exportUrl(meeting.id, "docx")} className="rounded-xl border border-line bg-white px-4 py-2.5 text-sm font-semibold hover:border-moss">↓ DOCX</a></div>
      </div>

      <div className="mt-8 flex gap-1 overflow-x-auto rounded-2xl border border-line bg-white p-1.5 scrollbar-none">
        {tabs.map(([key, label, count]) => <button key={key} onClick={() => setTab(key)} className={`whitespace-nowrap rounded-xl px-4 py-2.5 text-sm font-semibold transition ${tab === key ? "bg-ink text-white" : "text-stone-500 hover:bg-cream"}`}>{label}{count !== null && <span className={`ml-2 rounded-full px-2 py-0.5 text-[10px] ${tab === key ? "bg-white/15" : "bg-stone-100"}`}>{count}</span>}</button>)}
      </div>

      <section className="mt-5">
        {tab === "summary" && meeting.summary && <div className="grid gap-5 lg:grid-cols-[1.35fr_.65fr]">
          <div className="space-y-5"><article className="rounded-[2rem] bg-ink p-7 text-white sm:p-9"><p className="text-xs font-bold uppercase tracking-[.18em] text-lime">Тема совещания</p><h2 className="mt-4 text-2xl font-bold leading-snug">{meeting.summary.topic}</h2><div className="mt-7 h-px bg-white/10"/><p className="mt-6 text-xs font-bold uppercase tracking-wider text-white/40">Ключевые моменты</p><ul className="mt-4 space-y-4">{meeting.summary.key_points.map((point) => <li key={point} className="flex gap-3 text-sm leading-6 text-white/80"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-lime" />{point}</li>)}</ul></article><article className="rounded-[2rem] border border-line bg-white p-7"><h3 className="font-bold">Принятые решения</h3><ol className="mt-5 space-y-4">{meeting.summary.decisions.map((item, i) => <li key={item} className="flex gap-4 text-sm leading-6 text-stone-600"><span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-lime/40 text-xs font-bold">{i + 1}</span>{item}</li>)}</ol></article></div>
          <aside className="space-y-5"><article className="rounded-[2rem] border border-line bg-white p-6"><div className="flex items-center justify-between"><h3 className="font-bold">Поручения</h3><button onClick={() => setTab("tasks")} className="text-xs font-bold text-moss">Все →</button></div><div className="mt-4 space-y-3">{meeting.tasks.map((task) => <div key={task.id} className="rounded-2xl bg-cream p-4"><p className="text-sm font-semibold leading-5">{task.task}</p><div className="mt-3 flex justify-between text-[11px] text-stone-400"><span>{task.responsible}</span><span>{task.deadline_normalized ?? task.deadline_raw}</span></div></div>)}</div></article><article className="rounded-[2rem] border border-amber-100 bg-amber-50 p-6"><p className="text-xs font-bold uppercase tracking-wider text-amber-700">Требует внимания</p><ul className="mt-3 space-y-2 text-sm leading-6 text-amber-900">{meeting.summary.problems.map((problem) => <li key={problem}>• {problem}</li>)}</ul></article></aside>
        </div>}

        {tab === "tasks" && <div className="space-y-3">{meeting.tasks.map((task, i) => <article key={task.id} className="rounded-3xl border border-line bg-white p-6"><div className="flex flex-col gap-4 md:flex-row md:items-start"><span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-lime/40 text-sm font-bold">{i + 1}</span><div className="flex-1"><h3 className="font-bold">{task.task}</h3><p className="mt-2 text-xs italic text-stone-400">«{task.original_text}»</p><div className="mt-5 grid gap-4 sm:grid-cols-3"><div><p className="text-[10px] font-bold uppercase tracking-wider text-stone-400">Ответственный</p><p className="mt-1 text-sm font-semibold">{task.responsible}</p></div><div><p className="text-[10px] font-bold uppercase tracking-wider text-stone-400">Поставил</p><p className="mt-1 text-sm font-semibold">{task.assigned_by}</p></div><div><p className="text-[10px] font-bold uppercase tracking-wider text-stone-400">Срок</p><p className="mt-1 text-sm font-semibold">{task.deadline_normalized ? formatDate(task.deadline_normalized) : task.deadline_raw}</p></div></div></div><span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700">{Math.round(task.confidence * 100)}%</span></div></article>)}</div>}

        {tab === "transcript" && <div className="rounded-[2rem] border border-line bg-white p-6 sm:p-8"><div className="mb-6 flex items-center justify-between"><div><h2 className="font-bold">Полный транскрипт</h2><p className="mt-1 text-xs text-stone-400">{meeting.transcript.length} реплик</p></div><span className="rounded-full bg-cream px-3 py-1 text-xs text-stone-500">RU / KZ</span></div><div className="space-y-6">{meeting.transcript.map((segment) => <div key={segment.id} className="grid gap-2 sm:grid-cols-[70px_160px_1fr]"><span className="text-xs font-medium text-stone-400">{formatTime(segment.start)}</span><span className="text-sm font-bold text-moss">{segment.speaker_name}</span><p className="text-sm leading-7 text-stone-600">{segment.text}</p></div>)}</div></div>}

        {tab === "participants" && <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{meeting.participants.map((participant) => <article key={participant.id} className="rounded-3xl border border-line bg-white p-6"><div className="flex items-center gap-4"><div className="grid h-12 w-12 place-items-center rounded-2xl bg-cream text-lg font-bold text-moss">{participant.display_name.slice(0, 1)}</div><div className="min-w-0 flex-1"><h3 className="truncate font-bold">{participant.display_name}</h3><p className="mt-1 text-xs text-stone-400">{participant.speaker_label} · {Math.round(participant.confidence * 100)}%</p></div><button onClick={() => rename(participant.id, participant.display_name)} title="Изменить имя" className="rounded-lg border border-line px-2.5 py-1.5 text-xs hover:bg-cream">✎</button></div></article>)}</div>}
      </section>
    </div>
  );
}

