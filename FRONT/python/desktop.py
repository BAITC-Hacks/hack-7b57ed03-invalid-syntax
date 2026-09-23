"""ALEM / Aqylman native desktop. No browser, JavaScript or cloud API."""
import argparse
import json
import os
import sys
from datetime import date
from html import escape
from pathlib import Path

os.environ.setdefault('QT_MEDIA_BACKEND', 'ffmpeg')

from PySide6.QtCore import QDate, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDateEdit, QDialog, QDialogButtonBox,
    QFileDialog, QFormLayout, QFrame, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QListWidget, QMainWindow, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QScrollArea, QSplitter, QStackedWidget,
    QStyle, QTableWidget, QTableWidgetItem, QTabWidget, QTextBrowser,
    QVBoxLayout, QWidget,
)

from api import Api
from audio import Player, Recorder, icon_button, timestamp
from jobs import Jobs

BASE = Path(__file__).resolve().parent
DATA = BASE.parent / '.desktop-data'
STATES = {'created': 'Черновик', 'uploaded': 'Запись загружена', 'processing': 'Обработка',
          'completed': 'Готово', 'failed': 'Ошибка'}
TASK_STATES = {'open': 'На проверке', 'confirmed': 'Проверено', 'done': 'Выполнено'}
FORMATS = 'Аудио и видео (*.mp3 *.wav *.m4a *.ogg *.mp4 *.mov *.webm *.mkv)'


def label(text, name='', wrap=False):
    widget = QLabel(text)
    widget.setObjectName(name)
    widget.setWordWrap(wrap)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    return widget


def button(text, callback, primary=False, icon=None):
    widget = QPushButton(text)
    widget.clicked.connect(callback)
    if primary:
        widget.setObjectName('primary')
    if icon is not None:
        widget.setIcon(widget.style().standardIcon(icon))
    return widget


def table(headers):
    widget = QTableWidget(0, len(headers))
    widget.setHorizontalHeaderLabels(headers)
    widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    widget.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
    widget.setAlternatingRowColors(True)
    widget.setShowGrid(False)
    widget.verticalHeader().hide()
    widget.verticalHeader().setDefaultSectionSize(57)
    widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    widget.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    return widget


class NewMeeting(QDialog):
    def __init__(self, window, path=''):
        super().__init__(window)
        self.window = window
        self.path = path
        self.created_id = None
        self.busy = False
        self.setWindowTitle('Новое совещание')
        self.setMinimumWidth(540)
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.addWidget(label('Новое совещание', 'section'))
        form = QFormLayout()
        self.title = QLineEdit(Path(path).stem if path else '')
        self.title.setPlaceholderText('Например: Планирование пилотного проекта')
        self.title.setMaxLength(240)
        self.day = QDateEdit(QDate.currentDate())
        self.day.setCalendarPopup(True)
        self.day.setDisplayFormat('dd.MM.yyyy')
        form.addRow('Название', self.title)
        form.addRow('Дата встречи', self.day)
        layout.addLayout(form)
        self.file_label = label(Path(path).name if path else 'Файл не выбран', 'muted', True)
        layout.addWidget(self.file_label)
        self.choose = button('Выбрать запись', self.choose_file, icon=QStyle.StandardPixmap.SP_DialogOpenButton)
        layout.addWidget(self.choose)
        self.message = label('MP3, WAV, M4A, OGG, MP4, MOV, WEBM, MKV. До 500 МБ.', 'muted', True)
        layout.addWidget(self.message)
        self.save = button('Создать совещание', self.create, True)
        layout.addWidget(self.save)

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Запись совещания', '', FORMATS)
        if path:
            self.path = path
            self.file_label.setText(Path(path).name)
            if not self.title.text().strip():
                self.title.setText(Path(path).stem)

    def create(self):
        title = self.title.text().strip()
        if len(title) < 2 or not self.path:
            self.message.setText('Укажите название (от 2 символов) и выберите запись.')
            return
        path = Path(self.path)
        if not path.is_file() or not 0 < path.stat().st_size <= 500 * 1024 * 1024:
            self.message.setText('Нужен непустой файл размером до 500 МБ.')
            return
        day = self.day.date().toString('yyyy-MM-dd')
        self.busy = True
        for control in [self.title, self.day, self.choose, self.save]:
            control.setEnabled(False)
        self.message.setText('Сохраняем запись в локальном backend…')

        def work():
            if self.created_id is None:
                self.created_id = self.window.api.create(title, day)['id']
            self.window.api.upload(self.created_id, path)
            return self.created_id

        def success(meeting_id):
            self.busy = False
            self.accept()
            self.window.open_meeting(meeting_id)

        def failure(message):
            self.busy = False
            # Keep the ID on upload failure; retry must not create another meeting.
            self.choose.setEnabled(True)
            self.save.setEnabled(True)
            self.title.setEnabled(self.created_id is None)
            self.day.setEnabled(self.created_id is None)
            self.message.setText(message + ' Можно повторить загрузку.')

        self.window.jobs.submit(work, success, failure)

    def reject(self):
        if not self.busy:
            super().reject()


class Window(QMainWindow):
    def __init__(self, api, data_dir=DATA):
        super().__init__()
        self.api = api
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings_file = self.data_dir / 'settings.json'
        try:
            self.settings = json.loads(self.settings_file.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            self.settings = {}
        self.jobs = Jobs(self)
        self.meetings = []
        self.meeting = None
        self.task_drafts = {}
        self.people_drafts = {}
        self.current_task = None
        self.loading_editor = False
        self.polling = False
        self.saving = False
        self.generation = 0
        self.health_data = {}
        self.setWindowTitle('ALEM PROTOCOL | Aqylman')
        self.resize(1260, 840)
        self.setMinimumSize(980, 700)
        self.setStyleSheet((BASE / 'theme.qss').read_text(encoding='utf-8'))
        root = QWidget()
        self.setCentralWidget(root)
        row = QHBoxLayout(root)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        side = QFrame()
        side.setObjectName('sidebar')
        side.setFixedWidth(210)
        nav = QVBoxLayout(side)
        nav.setContentsMargins(18, 28, 18, 20)
        nav.setSpacing(8)
        nav.addWidget(label('ALEM\nPROTOCOL', 'brand'))
        nav.addWidget(label('AQYLMAN · DESKTOP', 'eyebrow'))
        nav.addSpacing(35)
        nav.addWidget(label('РАБОЧЕЕ ПРОСТРАНСТВО', 'eyebrow'))
        self.nav = []
        for index, (name, icon) in enumerate([
            ('Совещания', QStyle.StandardPixmap.SP_FileDialogDetailedView),
            ('Поручения', QStyle.StandardPixmap.SP_DialogApplyButton),
            ('Живая запись', QStyle.StandardPixmap.SP_MediaVolume),
            ('Настройки', QStyle.StandardPixmap.SP_FileDialogContentsView),
        ]):
            item = button(name, lambda checked=False, i=index: self.navigate(i), icon=icon)
            item.setObjectName('nav')
            item.setCheckable(True)
            nav.addWidget(item)
            self.nav.append(item)
        nav.addStretch()
        nav.addWidget(label('Локальное рабочее место', 'status'))
        nav.addWidget(label('Записи на этом компьютере', 'muted', True))
        row.addWidget(side)
        workspace = QWidget()
        workspace.setObjectName('workspace')
        body = QVBoxLayout(workspace)
        body.setContentsMargins(0, 0, 0, 0)
        header = QHBoxLayout()
        header.setContentsMargins(28, 16, 28, 8)
        header.addWidget(label('Протоколы совещаний', 'muted'))
        header.addStretch()
        self.connection = label('Подключение…', 'status')
        header.addWidget(self.connection)
        body.addLayout(header)
        self.banner = label('Проверяем режим backend…', 'banner', True)
        self.banner.setContentsMargins(20, 0, 20, 0)
        body.addWidget(self.banner)
        self.pages = QStackedWidget()
        body.addWidget(self.pages, 1)
        row.addWidget(workspace, 1)
        self.build_meetings()
        self.build_tasks()
        self.recorder = Recorder(self.data_dir / 'recordings')
        self.recorder.recorded.connect(self.new_meeting)
        self.recorder.active_changed.connect(self.recording_changed)
        self.pages.addWidget(self.recorder)
        self.build_settings()
        self.build_detail()
        self.poll = QTimer(self)
        self.poll.setInterval(1200)
        self.poll.timeout.connect(self.poll_status)
        self.statusBar().showMessage('Готово')
        self.navigate(0)
        self.refresh_health()

    def page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        self.pages.addWidget(widget)
        return widget, layout

    def error(self, message):
        self.statusBar().showMessage(message, 12000)
        QMessageBox.warning(self, 'Не удалось выполнить действие', message)

    def dirty(self):
        return bool(self.task_drafts or self.people_drafts)

    def can_leave(self):
        if self.saving:
            self.statusBar().showMessage('Дождитесь сохранения.', 4000)
            return False
        if self.dirty():
            answer = QMessageBox.question(self, 'Несохранённые изменения',
                                          'Отбросить изменения поручений и участников?',
                                          QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                                          QMessageBox.StandardButton.Cancel)
            if answer != QMessageBox.StandardButton.Discard:
                return False
            self.task_drafts.clear()
            self.people_drafts.clear()
        return True

    def navigate(self, index):
        if self.pages.currentIndex() == 4 and not self.can_leave():
            return
        self.generation += 1
        self.poll.stop() if hasattr(self, 'poll') else None
        if hasattr(self, 'player'):
            self.player.player.pause()
        self.pages.setCurrentIndex(index)
        for i, nav in enumerate(self.nav):
            nav.setChecked(i == index)
        if index == 0:
            self.refresh_meetings()
        elif index == 1:
            self.refresh_tasks()
        elif index == 3:
            self.refresh_health()

    def refresh_health(self):
        def received(data):
            self.health_data = data
            self.connection.setText('Backend подключён')
            mock = data.get('mock_mode', True)
            self.banner.setText('ДЕМОРЕЖИМ BACKEND: результат обработки задан заранее и не является расшифровкой вашей записи.'
                                if mock else 'Локальная обработка. Доступность моделей проверяется при запуске анализа.')
            self.backend_info.setPlainText(
                f'Адрес: {self.api.base}\nРежим: {"демонстрационный (MOCK_MODE)" if mock else "локальные модели"}\n'
                f'Устройство: {data.get("device", "не указано")}\n\n'
                'Фронтенд: Python / PySide6 (Qt)\nBackend: FastAPI / SQLite\n'
                'API NVIDIA и другие облачные сервисы не используются.\n\n'
                'Распознавание RU/KK и диаризация зависят от реализации backend. '
                'В текущем репозитории реальные AI-провайдеры пока не реализованы.\n\n'
                f'Записи микрофона: {self.data_dir / "recordings"}\n'
                'Файлы встреч и база данных: BACKEND/uploads и BACKEND/meeting_protocol.db.')
        def failed(message):
            self.connection.setText('Backend недоступен')
            self.banner.setText(message)
        self.jobs.submit(self.api.health, received, failed)

    def build_meetings(self):
        _page, layout = self.page()
        heading = QHBoxLayout()
        heading.addWidget(label('Совещания', 'title'))
        heading.addStretch()
        heading.addWidget(button('Новое совещание', self.new_meeting, True, QStyle.StandardPixmap.SP_FileIcon))
        layout.addLayout(heading)
        stats = QHBoxLayout()
        self.metrics = []
        for title in ['ВСЕГО ВСТРЕЧ', 'ГОТОВЫЕ ПРОТОКОЛЫ', 'В ОБРАБОТКЕ', 'ОЖИДАЮТ АНАЛИЗА']:
            group = QVBoxLayout()
            number = label('0', 'metric')
            self.metrics.append(number)
            group.addWidget(number)
            group.addWidget(label(title, 'eyebrow'))
            stats.addLayout(group, 1)
        layout.addLayout(stats)
        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText('Поиск по названию и файлу записи')
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.render_meetings)
        filters.addWidget(self.search, 1)
        self.filter = QComboBox()
        self.filter.addItem('Все статусы', None)
        for code, name in STATES.items():
            self.filter.addItem(name, code)
        self.filter.currentIndexChanged.connect(self.render_meetings)
        filters.addWidget(self.filter)
        filters.addWidget(icon_button(self, QStyle.StandardPixmap.SP_BrowserReload, 'Обновить встречи', self.refresh_meetings))
        layout.addLayout(filters)
        self.meeting_table = table(['СОВЕЩАНИЕ', 'ДАТА', 'СТАТУС'])
        self.meeting_table.cellDoubleClicked.connect(self.open_selected_meeting)
        layout.addWidget(self.meeting_table, 1)
        bottom = QHBoxLayout()
        self.empty = label('Загружаем встречи…', 'muted', True)
        bottom.addWidget(self.empty, 1)
        bottom.addWidget(button('Открыть', self.open_selected_meeting, icon=QStyle.StandardPixmap.SP_ArrowForward))
        layout.addLayout(bottom)

    def refresh_meetings(self):
        def received(data):
            self.meetings = data
            self.render_meetings()
        self.jobs.submit(self.api.meetings, received, self.error)

    def render_meetings(self, *_):
        needle = self.search.text().casefold()
        rows = [m for m in self.meetings
                if needle in (m['title'] + ' ' + (m['source_filename'] or '')).casefold()
                and (not self.filter.currentData() or self.filter.currentData() == m['status'])]
        self.visible_meetings = rows
        self.meeting_table.setRowCount(len(rows))
        for index, meeting in enumerate(rows):
            for col, text in enumerate([meeting['title'], meeting['meeting_date'], STATES.get(meeting['status'], meeting['status'])]):
                cell = QTableWidgetItem(text)
                cell.setToolTip(text)
                self.meeting_table.setItem(index, col, cell)
        values = [len(self.meetings), sum(m['status'] == 'completed' for m in self.meetings),
                  sum(m['status'] == 'processing' for m in self.meetings),
                  sum(m['status'] in {'created', 'uploaded'} for m in self.meetings)]
        for widget, value in zip(self.metrics, values):
            widget.setText(str(value))
        self.empty.setText(f'Найдено встреч: {len(rows)}' if rows else 'Встреч пока нет.' if not self.meetings else 'Совпадений нет.')

    def open_selected_meeting(self, *_):
        row = self.meeting_table.currentRow()
        if 0 <= row < len(self.visible_meetings):
            self.open_meeting(self.visible_meetings[row]['id'])

    def new_meeting(self, path=''):
        if not self.can_leave():
            return
        dialog = NewMeeting(self, path if isinstance(path, str) else '')
        dialog.exec()

    def build_tasks(self):
        _page, layout = self.page()
        row = QHBoxLayout()
        row.addWidget(label('Поручения', 'title'), 1)
        row.addWidget(icon_button(self, QStyle.StandardPixmap.SP_BrowserReload, 'Обновить поручения', self.refresh_tasks))
        layout.addLayout(row)
        self.all_tasks = table(['ПОРУЧЕНИЕ', 'ОТВЕТСТВЕННЫЙ', 'СРОК', 'СТАТУС'])
        self.all_tasks.cellDoubleClicked.connect(self.open_task_meeting)
        layout.addWidget(self.all_tasks, 1)
        self.tasks_message = label('Загружаем поручения…', 'muted')
        layout.addWidget(self.tasks_message)
        layout.addWidget(button('Открыть совещание', self.open_task_meeting, icon=QStyle.StandardPixmap.SP_ArrowForward))

    def refresh_tasks(self):
        def work():
            return [(m['id'], task) for m in self.api.meetings() for task in self.api.meeting(m['id'])['tasks']]
        def received(rows):
            self.task_rows = rows
            self.all_tasks.setRowCount(len(rows))
            for row, (_meeting_id, task) in enumerate(rows):
                values = [task['task'], task['responsible'], task['deadline_normalized'] or task['deadline_raw'] or 'Не указан',
                          TASK_STATES.get(task['status'], task['status'])]
                for col, text in enumerate(values):
                    item = QTableWidgetItem(text)
                    item.setToolTip(text)
                    self.all_tasks.setItem(row, col, item)
            self.tasks_message.setText(f'Поручений: {len(rows)}')
        self.jobs.submit(work, received, self.error)

    def open_task_meeting(self, *_):
        row = self.all_tasks.currentRow()
        if 0 <= row < len(getattr(self, 'task_rows', [])):
            self.open_meeting(self.task_rows[row][0])

    def build_settings(self):
        _page, layout = self.page()
        layout.addWidget(label('Настройки и подключение', 'title'))
        self.backend_info = QPlainTextEdit()
        self.backend_info.setReadOnly(True)
        layout.addWidget(self.backend_info, 1)
        row = QHBoxLayout()
        row.addWidget(button('Проверить подключение', self.refresh_health, icon=QStyle.StandardPixmap.SP_BrowserReload))
        row.addWidget(button('Открыть папку записей', self.open_recordings, icon=QStyle.StandardPixmap.SP_DirIcon))
        row.addStretch()
        layout.addLayout(row)

    def open_recordings(self):
        folder = self.data_dir / 'recordings'
        folder.mkdir(exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def build_detail(self):
        _page, layout = self.page()
        row = QHBoxLayout()
        row.addWidget(icon_button(self, QStyle.StandardPixmap.SP_ArrowBack, 'К совещаниям', lambda: self.navigate(0)))
        self.detail_title = label('Совещание', 'title', True)
        row.addWidget(self.detail_title, 1)
        self.pdf = button('PDF', lambda: self.export('pdf'), icon=QStyle.StandardPixmap.SP_DialogSaveButton)
        self.docx = button('DOCX', lambda: self.export('docx'), icon=QStyle.StandardPixmap.SP_DialogSaveButton)
        row.addWidget(self.pdf)
        row.addWidget(self.docx)
        layout.addLayout(row)
        self.detail_meta = label('', 'muted', True)
        layout.addWidget(self.detail_meta)
        self.player = Player(self.settings)
        layout.addWidget(self.player)
        progress_row = QHBoxLayout()
        self.process_label = label('', 'status', True)
        progress_row.addWidget(self.process_label, 1)
        self.progress = QProgressBar()
        self.progress.setFixedWidth(100)
        self.progress.setRange(0, 100)
        progress_row.addWidget(self.progress)
        self.retry_upload = button('Выбрать запись', self.upload_existing, icon=QStyle.StandardPixmap.SP_DialogOpenButton)
        progress_row.addWidget(self.retry_upload)
        self.process_button = button('Обработать запись', self.process, True)
        progress_row.addWidget(self.process_button)
        layout.addLayout(progress_row)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        task_page = QWidget()
        task_layout = QVBoxLayout(task_page)
        task_layout.setContentsMargins(0, 10, 0, 0)
        splitter = QSplitter()
        self.task_list = QListWidget()
        self.task_list.currentRowChanged.connect(self.select_task)
        self.task_list.setMinimumWidth(205)
        self.task_list.setMaximumWidth(350)
        splitter.addWidget(self.task_list)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.editor = QWidget()
        form = QFormLayout(self.editor)
        form.setContentsMargins(20, 5, 5, 5)
        self.task_text = QPlainTextEdit()
        self.task_text.setMaximumHeight(83)
        self.owner = QLineEdit()
        self.assigned = QLineEdit()
        self.deadline = QLineEdit()
        self.deadline.setPlaceholderText('ГГГГ-ММ-ДД или пусто')
        self.task_state = QComboBox()
        for key, value in TASK_STATES.items():
            self.task_state.addItem(value, key)
        self.quote = label('', 'muted', True)
        self.quote.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        form.addRow('Поручение', self.task_text)
        form.addRow('Ответственный', self.owner)
        form.addRow('Постановщик', self.assigned)
        form.addRow('Срок', self.deadline)
        form.addRow('Статус', self.task_state)
        form.addRow('Основание', self.quote)
        scroll.setWidget(self.editor)
        splitter.addWidget(scroll)
        splitter.setStretchFactor(1, 1)
        task_layout.addWidget(splitter, 1)
        save_row = QHBoxLayout()
        self.save_state = label('Нет несохранённых изменений', 'muted')
        save_row.addWidget(self.save_state, 1)
        self.save = button('Сохранить изменения', self.save_changes, True, QStyle.StandardPixmap.SP_DialogSaveButton)
        save_row.addWidget(self.save)
        task_layout.addLayout(save_row)
        self.tabs.addTab(task_page, 'Поручения')
        self.summary = QTextBrowser()
        self.tabs.addTab(self.summary, 'Краткий итог')
        self.transcript = table(['РЕПЛИКА', 'УЧАСТНИК', 'ВРЕМЯ'])
        self.transcript.cellDoubleClicked.connect(self.seek_transcript)
        self.tabs.addTab(self.transcript, 'Транскрипт')
        people_page = QWidget()
        people_layout = QVBoxLayout(people_page)
        self.people = QTableWidget(0, 2)
        self.people.setHorizontalHeaderLabels(['СПИКЕР', 'ИМЯ'])
        self.people.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.people.verticalHeader().hide()
        self.people.itemChanged.connect(self.person_changed)
        people_layout.addWidget(self.people)
        people_layout.addWidget(label('Имя обновится в транскрипте. Ответственных в поручениях проверяйте отдельно.', 'muted', True))
        people_layout.addWidget(button('Сохранить изменения', self.save_changes, True, QStyle.StandardPixmap.SP_DialogSaveButton))
        self.tabs.addTab(people_page, 'Участники')
        self.task_text.textChanged.connect(self.task_changed)
        for edit in [self.owner, self.assigned, self.deadline]:
            edit.textChanged.connect(self.task_changed)
        self.task_state.currentIndexChanged.connect(self.task_changed)

    def open_meeting(self, meeting_id):
        if not self.can_leave():
            return
        self.generation += 1
        generation = self.generation
        self.statusBar().showMessage('Открываем совещание…')
        def received(data):
            if generation != self.generation:
                return
            self.meeting = data
            self.pages.setCurrentIndex(4)
            for nav in self.nav:
                nav.setChecked(False)
            self.render_detail()
            self.poll.start()
            self.statusBar().showMessage('Совещание открыто', 3000)
        self.jobs.submit(lambda: self.api.meeting(meeting_id), received, self.error)

    def render_detail(self, reload_media=True):
        meeting = self.meeting
        self.task_drafts.clear()
        self.people_drafts.clear()
        self.current_task = None
        self.loading_editor = True
        self.detail_title.setText(meeting['title'])
        self.detail_meta.setText(f'{meeting["meeting_date"]}  /  {meeting["source_filename"] or "Без записи"}')
        self.update_progress(meeting)
        if reload_media:
            self.player.load(self.api.media_url(meeting['id']) if meeting['source_filename'] else '', meeting['source_filename'])
        self.task_list.clear()
        for number, task in enumerate(meeting['tasks'], 1):
            self.task_list.addItem(f'{number:02}   {task["task"]}\n       {task["responsible"]}')
        self.editor.setEnabled(bool(meeting['tasks']))
        self.loading_editor = False
        if meeting['tasks']:
            self.task_list.setCurrentRow(0)
        else:
            self.loading_editor = True
            self.task_text.clear()
            self.owner.clear()
            self.assigned.clear()
            self.deadline.clear()
            self.quote.setText('Результаты появятся после обработки записи.')
            self.loading_editor = False
        summary = meeting['summary']
        if summary:
            html = f'<h2>{escape(summary["topic"])}</h2>'
            for name, key in [('Ключевые вопросы', 'key_points'), ('Проблемы', 'problems'), ('Решения', 'decisions')]:
                html += f'<h3>{name}</h3><ul>' + ''.join(f'<li>{escape(item)}</li>' for item in summary[key]) + '</ul>'
            self.summary.setHtml(html)
        else:
            self.summary.setPlainText('Итог ещё не готов.')
        self.transcript.setRowCount(len(meeting['transcript']))
        for row, item in enumerate(meeting['transcript']):
            for col, text in enumerate([item['text'], item['speaker_name'], timestamp(item['start'] * 1000)]):
                cell = QTableWidgetItem(text)
                cell.setToolTip(text)
                self.transcript.setItem(row, col, cell)
        self.transcript.resizeRowsToContents()
        self.people.blockSignals(True)
        self.people.setRowCount(len(meeting['participants']))
        for row, person in enumerate(meeting['participants']):
            cell = QTableWidgetItem(person['speaker_label'])
            cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.people.setItem(row, 0, cell)
            self.people.setItem(row, 1, QTableWidgetItem(person['display_name']))
        self.people.blockSignals(False)
        self.update_dirty()

    def select_task(self, row):
        if self.loading_editor or not self.meeting or not 0 <= row < len(self.meeting['tasks']):
            return
        self.current_task = self.meeting['tasks'][row]
        task = self.task_drafts.get(self.current_task['id'], self.current_task)
        self.loading_editor = True
        self.task_text.setPlainText(task['task'])
        self.owner.setText(task['responsible'])
        self.assigned.setText(task['assigned_by'])
        self.deadline.setText(task['deadline_normalized'] or '')
        index = self.task_state.findData(task['status'])
        if index == -1:
            self.task_state.addItem(task['status'], task['status'])
            index = self.task_state.count() - 1
        self.task_state.setCurrentIndex(index)
        self.quote.setText(f'{self.current_task["original_text"]}\nСрок в речи: {self.current_task["deadline_raw"] or "не указан"}')
        self.loading_editor = False

    def task_changed(self, *_):
        if self.loading_editor or not self.current_task:
            return
        values = {'task': self.task_text.toPlainText(), 'responsible': self.owner.text(),
                  'assigned_by': self.assigned.text(), 'deadline_normalized': self.deadline.text().strip() or None,
                  'status': self.task_state.currentData()}
        if all(values[key] == self.current_task[key] for key in values):
            self.task_drafts.pop(self.current_task['id'], None)
        else:
            self.task_drafts[self.current_task['id']] = values
        self.update_dirty()

    def person_changed(self, item):
        if item.column() != 1 or not self.meeting:
            return
        person = self.meeting['participants'][item.row()]
        if item.text().strip() == person['display_name']:
            self.people_drafts.pop(person['id'], None)
        else:
            self.people_drafts[person['id']] = item.text().strip()
        self.update_dirty()

    def update_dirty(self):
        count = len(self.task_drafts) + len(self.people_drafts)
        self.save_state.setText(f'Несохранённых изменений: {count}' if count else 'Все изменения сохранены')
        self.save.setEnabled(bool(count) and not self.saving)

    def save_changes(self):
        if self.saving or not self.dirty():
            return
        for draft in self.task_drafts.values():
            if not draft['task'].strip() or not draft['responsible'].strip():
                self.error('Поручение и ответственный не должны быть пустыми.')
                return
            if draft['deadline_normalized']:
                try:
                    date.fromisoformat(draft['deadline_normalized'])
                except ValueError:
                    self.error('Укажите срок в формате ГГГГ-ММ-ДД или оставьте его пустым.')
                    return
        if any(not name or len(name) > 240 for name in self.people_drafts.values()):
            self.error('Имя участника должно содержать от 1 до 240 символов.')
            return
        meeting_id = self.meeting['id']
        tasks = {key: dict(value) for key, value in self.task_drafts.items()}
        people = dict(self.people_drafts)
        self.saving = True
        self.tabs.setEnabled(False)
        self.process_button.setEnabled(False)
        self.update_dirty()
        def work():
            for task_id, values in tasks.items():
                self.api.task(meeting_id, task_id, values)
            for person_id, name in people.items():
                self.api.participant(meeting_id, person_id, name)
            return self.api.meeting(meeting_id)
        def received(data):
            self.meeting = data
            self.render_detail(reload_media=False)
            self.statusBar().showMessage('Изменения сохранены в backend', 5000)
        def finished():
            self.saving = False
            self.tabs.setEnabled(True)
            self.update_progress(self.meeting)
            self.update_dirty()
        self.jobs.submit(work, received, self.error, finished)

    def update_progress(self, data):
        state = data['status']
        self.process_label.setText(STATES.get(state, state) + (f' · {data["stage"]}' if state == 'processing' else ''))
        self.progress.setValue(data['progress'])
        self.progress.setVisible(state == 'processing')
        self.process_button.setEnabled(state != 'processing' and bool(self.meeting['source_filename']) and not self.saving)
        self.process_button.setText('Повторить анализ' if state == 'completed' else 'Обработать запись')
        self.retry_upload.setVisible(not self.meeting['source_filename'])
        self.pdf.setEnabled(state == 'completed')
        self.docx.setEnabled(state == 'completed')
        if data.get('error'):
            self.process_label.setText('Ошибка: ' + data['error'])

    def process(self):
        if not self.meeting or not self.can_leave():
            return
        if self.meeting['status'] == 'completed':
            answer = QMessageBox.question(self, 'Повторный анализ',
                'Повторный анализ заменит транскрипт, участников и все исправления поручений. Продолжить?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
        meeting_id = self.meeting['id']
        self.process_button.setEnabled(False)
        def received(_):
            if self.meeting and self.meeting['id'] == meeting_id:
                self.meeting['status'] = 'processing'
                self.update_progress({'status': 'processing', 'stage': 'queued', 'progress': 1})
                self.poll.start()
        def failed(message):
            self.process_button.setEnabled(True)
            self.error(message)
        self.jobs.submit(lambda: self.api.process(meeting_id), received, failed)

    def poll_status(self):
        if self.polling or self.saving or not self.meeting or self.pages.currentIndex() != 4:
            return
        if self.meeting['status'] not in {'processing', 'failed'}:
            return
        self.polling = True
        meeting_id = self.meeting['id']
        generation = self.generation
        def received(data):
            if generation != self.generation:
                return
            self.update_progress(data)
            if data['status'] != 'processing':
                self.poll.stop()
                if data['status'] == 'completed':
                    self.open_meeting(meeting_id)
                else:
                    self.meeting['status'] = data['status']
        def failed(message):
            self.poll.stop()
            self.connection.setText('Backend недоступен')
            self.error(message + ' Откройте встречу заново для обновления статуса.')
        self.jobs.submit(lambda: self.api.status(meeting_id), received, failed, lambda: setattr(self, 'polling', False))

    def upload_existing(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Запись совещания', '', FORMATS)
        if not path:
            return
        meeting_id = self.meeting['id']
        self.retry_upload.setEnabled(False)
        self.jobs.submit(lambda: self.api.upload(meeting_id, path), lambda _: self.open_meeting(meeting_id),
                         self.error, lambda: self.retry_upload.setEnabled(True))

    def seek_transcript(self, row, _column):
        if not self.meeting:
            return
        self.player.player.setPosition(int(self.meeting['transcript'][row]['start'] * 1000))
        self.player.player.play()

    def export(self, kind):
        if not self.meeting:
            return
        if self.dirty() or self.saving:
            self.error('Сначала сохраните изменения, чтобы они попали в документ.')
            return
        meeting_id = self.meeting['id']
        path, _ = QFileDialog.getSaveFileName(self, 'Сохранить протокол',
                                            f'Протокол-{meeting_id}.{kind}', f'{kind.upper()} (*.{kind})')
        if path:
            if not path.lower().endswith('.' + kind):
                path += '.' + kind
            self.jobs.submit(lambda: self.api.export(meeting_id, kind, path),
                             lambda result: self.statusBar().showMessage(f'Протокол сохранён: {result}', 12000), self.error)

    def recording_changed(self, active):
        self.nav[2].setText('Идёт запись…' if active else 'Живая запись')
        if active:
            self.player.player.stop()

    def closeEvent(self, event):
        if self.jobs.active:
            self.statusBar().showMessage('Дождитесь завершения текущего запроса.', 5000)
            event.ignore()
            return
        if not self.can_leave():
            event.ignore()
            return
        if self.recorder.active:
            answer = QMessageBox.question(self, 'Идёт запись', 'Остановить запись, сохранить файл и закрыть приложение?',
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                          QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.recorder.stop(announce=False)
        self.poll.stop()
        self.player.player.stop()
        self.settings['volume'] = self.player.volume.value()
        self.settings_file.write_text(json.dumps(self.settings), encoding='utf-8')
        event.accept()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--api', default='http://127.0.0.1:8000')
    args = parser.parse_args()
    application = QApplication(sys.argv[:1])
    application.setApplicationName('ALEM PROTOCOL')
    application.setOrganizationName('Aqylman')
    window = Window(Api(args.api))
    window.show()
    sys.exit(application.exec())


if __name__ == '__main__':
    main()
