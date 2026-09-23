export type MeetingStatus = "new" | "uploaded" | "processing" | "completed" | "failed";
export interface Meeting { id:number; title:string; meeting_date:string; status:MeetingStatus; stage:string; progress:number; source_filename:string|null; created_at:string }
export interface Participant { id:number; speaker_label:string; display_name:string; confidence:number }
export interface Transcript { id:number; speaker_label:string; speaker_name:string; start:number; end:number; text:string }
export interface Task { id:number; task:string; responsible:string; assigned_by:string; deadline_raw:string|null; deadline_normalized:string|null; original_text:string; confidence:number; status:string }
export interface Summary { topic:string; key_points:string[]; problems:string[]; decisions:string[]; tasks:number[] }
export interface MeetingDetail extends Meeting { participants:Participant[]; transcript:Transcript[]; tasks:Task[]; summary:Summary|null }
