export type MeetingStatus = "created" | "uploaded" | "processing" | "completed" | "failed";

export interface MeetingListItem {
  id: number;
  title: string;
  meeting_date: string;
  status: MeetingStatus;
  stage: string;
  progress: number;
  source_filename: string | null;
  created_at: string;
}

export interface ProcessingStatus {
  meeting_id: number;
  status: MeetingStatus;
  stage: string;
  progress: number;
  error: string | null;
}

export interface Participant {
  id: number;
  speaker_label: string;
  display_name: string;
  confidence: number;
}

export interface TranscriptSegment {
  id: number;
  speaker_label: string;
  speaker_name: string;
  start: number;
  end: number;
  text: string;
}

export interface MeetingTask {
  id: number;
  task: string;
  responsible: string;
  assigned_by: string;
  deadline_raw: string | null;
  deadline_normalized: string | null;
  original_text: string;
  confidence: number;
  status: string;
}

export interface Summary {
  topic: string;
  key_points: string[];
  problems: string[];
  decisions: string[];
  tasks: number[];
}

export interface Meeting extends MeetingListItem {
  participants: Participant[];
  transcript: TranscriptSegment[];
  tasks: MeetingTask[];
  summary: Summary | null;
}

