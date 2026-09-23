export type MeetingStatus = "created" | "uploaded" | "processing" | "completed" | "partial" | "failed";
export interface Meeting { id:number; title:string; meeting_date:string; status:MeetingStatus; stage:string; progress:number; source_filename:string|null; created_at:string }
export interface Participant { id:number; speaker_label:string; display_name:string; role:string|null; confidence:number }
export interface Transcript { id:number; speaker_label:string; speaker_name:string; speaker_role:string|null; start:number; end:number; text:string; confidence:number }
export interface Task { id:number; task:string; responsible:string; assigned_by:string; deadline_raw:string|null; deadline_normalized:string|null; original_text:string; confidence:number; status:string }
export interface Summary { topic:string; summary_text:string; key_points:string[]; problems:string[]; decisions:string[]; risks:string[]; metrics:string[]; tasks:number[] }
export interface MeetingDetail extends Meeting { participants:Participant[]; transcript:Transcript[]; tasks:Task[]; summary:Summary|null }
export interface Health { status:string; offline:boolean; mock_mode:boolean; ffmpeg:boolean; device:string; models:Record<string,boolean> }
