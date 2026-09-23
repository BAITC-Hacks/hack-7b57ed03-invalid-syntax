import type { MeetingStatus } from "@/types/meeting";

const labels: Record<MeetingStatus, string> = {
  created: "Черновик",
  uploaded: "Загружено",
  processing: "Обработка",
  completed: "Готово",
  failed: "Ошибка",
};

export function StatusBadge({ status }: { status: MeetingStatus }) {
  const style = status === "completed" ? "bg-emerald-50 text-emerald-700" : status === "failed" ? "bg-red-50 text-red-700" : status === "processing" ? "bg-amber-50 text-amber-700" : "bg-stone-100 text-stone-600";
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide ${style}`}>{labels[status]}</span>;
}

