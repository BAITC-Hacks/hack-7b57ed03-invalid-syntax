import { MeetingResult } from "@/features/meeting/MeetingResult";

export default function MeetingPage({ params }: { params: { id: string } }) {
  return <MeetingResult meetingId={Number(params.id)} />;
}

