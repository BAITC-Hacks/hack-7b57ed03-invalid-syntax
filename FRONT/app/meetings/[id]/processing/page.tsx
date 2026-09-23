import { ProcessingView } from "@/features/processing/ProcessingView";

export default function ProcessingPage({ params }: { params: { id: string } }) {
  return <ProcessingView meetingId={Number(params.id)} />;
}

