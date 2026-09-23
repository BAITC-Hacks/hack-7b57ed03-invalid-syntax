from __future__ import annotations

import calendar
from datetime import date, timedelta
import re

MONTHS = {"января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
          "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12}
WEEKDAYS = {"понедельник": 0, "понедельника": 0, "вторник": 1, "вторника": 1,
            "среду": 2, "среды": 2, "четверг": 3, "четверга": 3,
            "пятницу": 4, "пятницы": 4, "субботу": 5, "субботы": 5, "воскресенье": 6}


def parse_deadline(raw: str | None, meeting_date: date) -> date | None:
    if not raw:
        return None
    text = raw.casefold().strip()
    if "послезавтра" in text:
        return meeting_date + timedelta(days=2)
    if "завтра" in text:
        return meeting_date + timedelta(days=1)
    if "сегодня" in text:
        return meeting_date
    match = re.search(r"\b([0-3]?\d)\s+([а-яё]+)(?:\s+(20\d{2}))?\b", text)
    if match and match.group(2) in MONTHS:
        day, month = int(match.group(1)), MONTHS[match.group(2)]
        year = int(match.group(3) or meeting_date.year)
        if not match.group(3) and (month, day) < (meeting_date.month, meeting_date.day):
            year += 1
        try:
            return date(year, month, day)
        except ValueError:
            return None
    for word, weekday in WEEKDAYS.items():
        if word in text:
            delta = (weekday - meeting_date.weekday()) % 7
            return meeting_date + timedelta(days=delta or 7)
    if "конца недели" in text or "этой неделе" in text or "текущая неделя" in text:
        return meeting_date + timedelta(days=6 - meeting_date.weekday())
    if "следующая неделя" in text:
        return meeting_date + timedelta(days=13 - meeting_date.weekday())
    if "две недели" in text:
        return meeting_date + timedelta(days=14)
    if "через неделю" in text or "за неделю" in text:
        return meeting_date + timedelta(days=7)
    if "конца месяца" in text:
        return date(meeting_date.year, meeting_date.month, calendar.monthrange(meeting_date.year, meeting_date.month)[1])
    if "через месяц" in text:
        month = meeting_date.month % 12 + 1
        year = meeting_date.year + (meeting_date.month // 12)
        return date(year, month, min(meeting_date.day, calendar.monthrange(year, month)[1]))
    if "конца квартала" in text:
        month = ((meeting_date.month - 1) // 3 + 1) * 3
        return date(meeting_date.year, month, calendar.monthrange(meeting_date.year, month)[1])
    return None
