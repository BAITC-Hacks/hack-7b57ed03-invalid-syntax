import type { Meeting, MeetingListItem, Participant, ProcessingStatus } from "@/types/meeting";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { ...init, cache: "no-store" });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Ошибка соединения с сервером" }));
    throw new Error(error.detail ?? "Не удалось выполнить запрос");
  }
  return response.json() as Promise<T>;
}

export const api = {
  listMeetings: () => request<MeetingListItem[]>("/meetings"),
  getMeeting: (id: number) => request<Meeting>(`/meetings/${id}`),
  getStatus: (id: number) => request<ProcessingStatus>(`/meetings/${id}/status`),
  createMeeting: (title: string, meetingDate: string) =>
    request<MeetingListItem>("/meetings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, meeting_date: meetingDate }),
    }),
  upload: (id: number, file: File) => {
    const data = new FormData();
    data.append("file", file);
    return request<{ meeting_id: number; filename: string; status: string }>(`/meetings/${id}/upload`, {
      method: "POST",
      body: data,
    });
  },
  process: (id: number) => request(`/meetings/${id}/process`, { method: "POST" }),
  renameParticipant: (meetingId: number, participantId: number, displayName: string) =>
    request<Participant>(`/meetings/${meetingId}/participants/${participantId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ display_name: displayName }),
    }),
  exportUrl: (id: number, format: "pdf" | "docx") => `${API_URL}/meetings/${id}/export/${format}`,
};

