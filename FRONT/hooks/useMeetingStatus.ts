"use client";

import { useEffect, useState } from "react";
import { api } from "@/services/api";
import type { ProcessingStatus } from "@/types/meeting";

export function useMeetingStatus(meetingId: number) {
  const [data, setData] = useState<ProcessingStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const result = await api.getStatus(meetingId);
        if (!active) return;
        setData(result);
        if (result.status === "processing") timer = setTimeout(poll, 800);
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : "Неизвестная ошибка");
      }
    };
    poll();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [meetingId]);

  return { data, error };
}

