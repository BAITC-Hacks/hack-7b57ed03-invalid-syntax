"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useMeetingStatus } from "@/hooks/useMeetingStatus";

const stages = [
  ["audio_preprocessing", "Подготовка аудио", "Шумоподавление и нормализация"],
  ["speech_to_text", "Распознавание речи", "Русская и казахская речь"],
  ["speaker_diarization", "Определение спикеров", "Разделение голосов участников"],
  ["task_extraction", "Анализ поручений", "Ответственные и сроки"],
  ["summarization", "Создание саммари", "Решения, вопросы и выводы"],
  ["protocol_generation", "Сборка протокола", "Финальная структура документа"],
];
const stageOrder = ["file_validation", "audio_extraction", "audio_preprocessing", "speech_to_text", "speaker_diarization", "merge_transcript", "speaker_mapping", "task_extraction", "deadline_normalization", "summarization", "saving_results", "protocol_generation", "completed"];

export function ProcessingView({ meetingId }: { meetingId: number }) {
  const router = useRouter();
  const { data, error } = useMeetingStatus(meetingId);
  useEffect(() => { if (data?.status === "completed") { const timer = setTimeout(() => router.push(`/meetings/${meetingId}`), 700); return () => clearTimeout(timer); } }, [data?.status, meetingId, router]);
  const currentIndex = stageOrder.indexOf(data?.stage ?? "file_validation");

  return (
    <div className="mx-auto max-w-4xl py-4">
      <div className="text-center"><p className="text-sm font-semibold text-moss">Совещание #{meetingId}</p><h1 className="mt-2 text-3xl font-bold tracking-tight">Собираем смысл разговора</h1><p className="mt-3 text-sm text-stone-500">Можно оставить эту страницу открытой — результат появится автоматически.</p></div>
      <section className="mt-9 overflow-hidden rounded-[2rem] border border-line bg-white shadow-soft">
        <div className="bg-ink px-6 py-8 text-white sm:px-10">
          <div className="flex items-center gap-6"><div className="processing-ring grid h-20 w-20 shrink-0 place-items-center rounded-full border-[7px] border-white/15 border-t-lime text-lg font-bold">{data?.progress ?? 0}%</div><div><p className="text-xs font-bold uppercase tracking-[.18em] text-lime">{data?.status === "completed" ? "Готово" : "AI pipeline"}</p><h2 className="mt-2 text-xl font-bold">{data?.status === "completed" ? "Протокол сформирован" : "Обработка записи"}</h2><p className="mt-1 text-sm text-white/50">Этап: {(data?.stage ?? "инициализация").replaceAll("_", " ")}</p></div></div>
          <div className="mt-7 h-1.5 overflow-hidden rounded-full bg-white/10"><div className="h-full rounded-full bg-lime transition-all duration-500" style={{ width: `${data?.progress ?? 0}%` }} /></div>
        </div>
        <div className="divide-y divide-line px-6 sm:px-10">
          {stages.map(([key, title, detail], index) => {
            const stepIndex = stageOrder.indexOf(key);
            const nextKey = stages[index + 1]?.[0];
            const nextIndex = nextKey ? stageOrder.indexOf(nextKey) : stageOrder.length;
            const done = currentIndex > stepIndex || data?.status === "completed";
            const active = currentIndex >= stepIndex && currentIndex < nextIndex;
            return <div key={key} className="flex items-center gap-4 py-5"><div className={`grid h-9 w-9 shrink-0 place-items-center rounded-full text-xs font-bold ${done ? "bg-moss text-white" : active ? "bg-lime text-ink" : "bg-stone-100 text-stone-400"}`}>{done ? "✓" : index + 1}</div><div className="flex-1"><p className={`text-sm font-bold ${active ? "text-moss" : "text-ink"}`}>{title}</p><p className="mt-0.5 text-xs text-stone-400">{detail}</p></div>{active && !done && <span className="text-xs font-semibold text-moss">в процессе…</span>}</div>;
          })}
        </div>
      </section>
      {(error || data?.status === "failed") && <div className="mt-5 rounded-2xl bg-red-50 p-5 text-sm text-red-700">{error ?? data?.error}<br/><Link href="/meetings/new" className="mt-2 inline-block font-bold underline">Попробовать снова</Link></div>}
    </div>
  );
}
