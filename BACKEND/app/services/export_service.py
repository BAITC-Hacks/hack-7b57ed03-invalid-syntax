import io
import json
from xml.sax.saxutils import escape

from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from app.models.meeting import Meeting


class ExportService:
    @staticmethod
    def _lines(meeting: Meeting) -> list[tuple[str, str]]:
        summary = meeting.summary
        points = json.loads(summary.key_points_json) if summary else []
        decisions = json.loads(summary.decisions_json) if summary else []
        return [
            ("ПРОТОКОЛ СОВЕЩАНИЯ", meeting.title),
            ("Дата", meeting.meeting_date.isoformat()),
            ("Участники", ", ".join(p.display_name for p in meeting.participants)),
            ("Тема", summary.topic if summary else "—"),
            ("Ключевые вопросы", "\n".join(f"• {x}" for x in points)),
            ("Решения", "\n".join(f"• {x}" for x in decisions)),
            ("Поручения", "\n".join(
                f"• {t.task} — {t.responsible}; срок: {t.deadline_normalized or t.deadline_raw or 'не указан'}"
                for t in meeting.tasks
            )),
            ("Полный транскрипт", "\n".join(f"{s.speaker_name}: {s.text}" for s in meeting.transcript)),
        ]

    def docx(self, meeting: Meeting) -> bytes:
        document = Document()
        for index, (heading, body) in enumerate(self._lines(meeting)):
            document.add_heading(heading, 0 if index == 0 else 1)
            for line in body.splitlines() or ["—"]:
                document.add_paragraph(line)
        output = io.BytesIO()
        document.save(output)
        return output.getvalue()

    def pdf(self, meeting: Meeting) -> bytes:
        output = io.BytesIO()
        font_name = "Helvetica"
        for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf"):
            try:
                pdfmetrics.registerFont(TTFont("ProtocolFont", path))
                font_name = "ProtocolFont"
                break
            except Exception:
                continue
        styles = getSampleStyleSheet()
        for style in styles.byName.values():
            style.fontName = font_name
        story = []
        for index, (heading, body) in enumerate(self._lines(meeting)):
            story.append(Paragraph(escape(heading), styles["Title"] if index == 0 else styles["Heading2"]))
            for line in body.splitlines() or ["—"]:
                story.append(Paragraph(escape(line), styles["BodyText"]))
            story.append(Spacer(1, 10))
        SimpleDocTemplate(output, pagesize=A4).build(story)
        return output.getvalue()

