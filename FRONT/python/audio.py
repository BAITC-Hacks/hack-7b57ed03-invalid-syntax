"""Native file playback and explicit, local microphone capture."""
import math
import struct
import time
import wave
from collections import deque
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QCoreApplication, QMicrophonePermission, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtMultimedia import (
    QAudioBufferOutput, QAudioFormat, QAudioOutput, QAudioSource,
    QMediaDevices, QMediaPlayer, QtAudio,
)
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton,
    QSlider, QStyle, QVBoxLayout, QWidget,
)


def samples(data, fmt):
    kind = fmt.sampleFormat()
    spec = {
        QAudioFormat.SampleFormat.UInt8: ('B', 1, 128),
        QAudioFormat.SampleFormat.Int16: ('h', 2, 32768),
        QAudioFormat.SampleFormat.Int32: ('i', 4, 2147483648),
        QAudioFormat.SampleFormat.Float: ('f', 4, 1),
    }.get(kind)
    if not spec:
        raise ValueError('Неподдерживаемый формат аудиоустройства.')
    code, size, scale = spec
    raw = bytes(data)
    raw = raw[:len(raw) // size * size]
    values = [value[0] for value in struct.iter_unpack('<' + code, raw)]
    if kind == QAudioFormat.SampleFormat.UInt8:
        return [(value - 128) / 128 for value in values]
    return [value / scale if math.isfinite(value) else 0 for value in values]


def pcm16(values, gain=1):
    return b''.join(struct.pack('<h', max(-32768, min(32767, round(v * gain * 32767)))) for v in values)


def timestamp(milliseconds):
    seconds = max(0, int(milliseconds) // 1000)
    return f'{seconds // 60:02}:{seconds % 60:02}'


def icon_button(parent, icon, tooltip, callback):
    button = QPushButton()
    button.setIcon(parent.style().standardIcon(icon))
    button.setFixedSize(38, 36)
    button.setToolTip(tooltip)
    button.setAccessibleName(tooltip)
    button.clicked.connect(callback)
    return button


class Meter(QWidget):
    """Rolling envelope of real decoded/captured samples, never simulated audio."""
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(68)
        self.setMinimumWidth(180)
        self.values = deque([0.] * 100, maxlen=100)
        self.peak = 0.
        self.level = -60.
        self.fresh = 0.
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(45)

    def feed(self, values, gain=1):
        if values:
            self.peak = min(1., max(abs(v) for v in values) * gain)
            rms = math.sqrt(sum(v * v for v in values) / len(values)) * gain
            self.level = max(-60., 20 * math.log10(max(rms, .001)))
            self.fresh = time.monotonic()

    def tick(self):
        if time.monotonic() - self.fresh > .18:
            self.peak *= .7
            self.level = max(-60., self.level - 3)
        self.values.append(self.peak)
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor('#f0f6f3'))
        center = self.height() / 2
        usable = max(20, self.width() - 72)
        step = usable / len(self.values)
        for index, amplitude in enumerate(self.values):
            painter.setPen(QPen(QColor('#b65c4c' if amplitude > .96 else '#4b9c83'), max(1, step * .5)))
            x = int(8 + index * step)
            height = max(1, amplitude * (center - 7))
            painter.drawLine(x, int(center - height), x, int(center + height))
        painter.setPen(QColor('#70897c'))
        painter.drawText(self.width() - 62, int(center), f'{self.level:.0f} dB')


class Player(QFrame):
    def __init__(self, settings=None):
        super().__init__()
        self.setObjectName('audio')
        self.setAccessibleName('Аудиоплеер')
        settings = settings or {}
        self.player = QMediaPlayer(self)
        self.output = QAudioOutput(self)
        self.player.setAudioOutput(self.output)
        self.buffer = QAudioBufferOutput(self)
        self.player.setAudioBufferOutput(self.buffer)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        row = QHBoxLayout()
        self.name = QLabel('Запись не выбрана')
        self.name.setObjectName('section')
        self.name.setWordWrap(True)
        row.addWidget(self.name, 1)
        self.clock = QLabel('00:00 / 00:00')
        self.clock.setMinimumWidth(108)
        self.clock.setAlignment(Qt.AlignmentFlag.AlignRight)
        row.addWidget(self.clock)
        layout.addLayout(row)
        self.meter = Meter()
        layout.addWidget(self.meter)
        self.seek = QSlider(Qt.Orientation.Horizontal)
        self.seek.setAccessibleName('Позиция записи')
        self.seek.setRange(0, 0)
        self.seek.sliderReleased.connect(lambda: self.player.setPosition(self.seek.value()))
        layout.addWidget(self.seek)
        controls = QHBoxLayout()
        controls.addWidget(icon_button(self, QStyle.StandardPixmap.SP_MediaSeekBackward, 'Назад на 10 секунд',
                                       lambda: self.player.setPosition(max(0, self.player.position() - 10000))))
        self.play = icon_button(self, QStyle.StandardPixmap.SP_MediaPlay, 'Воспроизведение / пауза', self.toggle)
        controls.addWidget(self.play)
        controls.addWidget(icon_button(self, QStyle.StandardPixmap.SP_MediaSeekForward, 'Вперёд на 10 секунд',
                                       lambda: self.player.setPosition(self.player.position() + 10000)))
        controls.addStretch()
        self.mute = icon_button(self, QStyle.StandardPixmap.SP_MediaVolume, 'Выключить / включить звук', self.toggle_mute)
        controls.addWidget(self.mute)
        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setFixedWidth(110)
        self.volume.setAccessibleName('Громкость воспроизведения')
        self.volume_label = QLabel()
        self.volume_label.setFixedWidth(39)
        self.volume.valueChanged.connect(self.set_volume)
        self.volume.setValue(settings.get('volume', 70))
        self.set_volume(self.volume.value())
        controls.addWidget(self.volume)
        controls.addWidget(self.volume_label)
        self.speed = QComboBox()
        self.speed.setAccessibleName('Скорость воспроизведения')
        self.speed.setToolTip('Скорость воспроизведения')
        for rate in [.75, 1., 1.25, 1.5, 2.]:
            self.speed.addItem(f'{rate:g}x', rate)
        self.speed.setCurrentIndex(1)
        self.speed.currentIndexChanged.connect(lambda: self.player.setPlaybackRate(self.speed.currentData()))
        controls.addWidget(self.speed)
        layout.addLayout(controls)
        self.error = QLabel('')
        self.error.setWordWrap(True)
        self.error.hide()
        layout.addWidget(self.error)
        self.player.positionChanged.connect(self.position)
        self.player.durationChanged.connect(self.duration)
        self.player.playbackStateChanged.connect(self.state_changed)
        self.player.errorOccurred.connect(lambda *_: self.show_error(self.player.errorString()))
        self.buffer.audioBufferReceived.connect(self.audio_buffer)
        self.setEnabled(False)

    def load(self, url, name):
        self.player.stop()
        self.error.hide()
        self.name.setText(name or 'Запись совещания')
        self.player.setSource(QUrl(url))
        self.setEnabled(bool(url))

    def toggle(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def toggle_mute(self):
        self.output.setMuted(not self.output.isMuted())
        icon = QStyle.StandardPixmap.SP_MediaVolumeMuted if self.output.isMuted() else QStyle.StandardPixmap.SP_MediaVolume
        self.mute.setIcon(self.style().standardIcon(icon))

    def set_volume(self, value):
        self.output.setVolume(value / 100)
        self.volume_label.setText(f'{value}%')

    def position(self, value):
        if not self.seek.isSliderDown():
            self.seek.setValue(value)
        self.clock.setText(f'{timestamp(value)} / {timestamp(self.player.duration())}')

    def duration(self, value):
        self.seek.setRange(0, value)
        self.position(self.player.position())

    def state_changed(self, state):
        icon = QStyle.StandardPixmap.SP_MediaPause if state == QMediaPlayer.PlaybackState.PlayingState else QStyle.StandardPixmap.SP_MediaPlay
        self.play.setIcon(self.style().standardIcon(icon))

    def audio_buffer(self, buffer):
        if buffer.isValid():
            gain = 0 if self.output.isMuted() else self.output.volume()
            self.meter.feed(samples(buffer.constData(), buffer.format()), gain)

    def show_error(self, text):
        self.error.setText('Не удалось воспроизвести запись: ' + text)
        self.error.show()


class Recorder(QWidget):
    recorded = Signal(str)
    active_changed = Signal(bool)

    def __init__(self, recordings: Path):
        super().__init__()
        self.recordings = recordings
        self.source = None
        self.stream = None
        self.file = None
        self.path = None
        self.started = 0
        self.byte_count = 0
        self.remainder = b''
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel('Живая запись')
        title.setObjectName('title')
        layout.addWidget(title)
        subtitle = QLabel('Микрофон и входные аудиоустройства')
        subtitle.setObjectName('muted')
        layout.addWidget(subtitle)
        row = QHBoxLayout()
        self.devices = QComboBox()
        self.devices.setAccessibleName('Устройство записи')
        row.addWidget(self.devices, 1)
        self.refresh = icon_button(self, QStyle.StandardPixmap.SP_BrowserReload, 'Обновить устройства', self.refresh_devices)
        row.addWidget(self.refresh)
        layout.addLayout(row)
        self.meter = Meter()
        self.meter.setMinimumHeight(170)
        layout.addWidget(self.meter)
        self.clock = QLabel('00:00')
        self.clock.setObjectName('metric')
        layout.addWidget(self.clock)
        level = QHBoxLayout()
        level.addWidget(QLabel('Усиление записи'))
        self.gain = QSlider(Qt.Orientation.Horizontal)
        self.gain.setRange(0, 200)
        self.gain.setValue(100)
        self.gain.setAccessibleName('Усиление микрофона')
        level.addWidget(self.gain, 1)
        self.gain_label = QLabel('100%')
        self.gain_label.setFixedWidth(48)
        self.gain.valueChanged.connect(lambda value: self.gain_label.setText(f'{value}%'))
        level.addWidget(self.gain_label)
        layout.addLayout(level)
        self.consent = QCheckBox('Участники предупреждены о записи')
        layout.addWidget(self.consent)
        buttons = QHBoxLayout()
        self.start_button = QPushButton('Начать запись')
        self.start_button.setObjectName('primary')
        self.start_button.clicked.connect(self.request_start)
        buttons.addWidget(self.start_button)
        self.stop_button = QPushButton('Остановить и сохранить')
        self.stop_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop)
        buttons.addWidget(self.stop_button)
        buttons.addStretch()
        layout.addLayout(buttons)
        self.message = QLabel('Готово к записи. Максимум 30 минут или 480 МБ.')
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        note = QLabel('Zoom / Teams: загрузите запись звонка или выберите установленное виртуальное аудиоустройство. '
                      'Подключение к встрече по ссылке и системный звук напрямую пока недоступны.')
        note.setWordWrap(True)
        note.setObjectName('muted')
        layout.addWidget(note)
        layout.addStretch()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.refresh_devices()

    @property
    def active(self):
        return self.source is not None

    def refresh_devices(self):
        self.devices.clear()
        for device in QMediaDevices.audioInputs():
            self.devices.addItem(device.description(), device)
        self.start_button.setEnabled(self.devices.count() > 0)
        if not self.devices.count():
            self.message.setText('Микрофон не найден. Подключите устройство и обновите список.')

    def request_start(self):
        if not self.consent.isChecked():
            self.message.setText('Перед записью предупредите участников и отметьте согласие.')
            return
        permission = QMicrophonePermission()
        application = QCoreApplication.instance()
        status = application.checkPermission(permission)
        if status == Qt.PermissionStatus.Undetermined:
            application.requestPermission(permission, self, self.permission_result)
        elif status == Qt.PermissionStatus.Denied:
            self.message.setText('Нет доступа к микрофону. Разрешите его в настройках конфиденциальности macOS.')
        else:
            self.start()

    def permission_result(self, permission):
        if permission.status() == Qt.PermissionStatus.Granted:
            self.start()
        else:
            self.message.setText('Доступ к микрофону не разрешён. Запись не началась.')

    def start(self):
        if self.active:
            return
        device = self.devices.currentData()
        if device is None:
            return
        fmt = device.preferredFormat()
        if not fmt.isValid():
            self.message.setText('Устройство не предоставило формат записи.')
            return
        self.recordings.mkdir(parents=True, exist_ok=True)
        self.path = self.recordings / f'Запись-{datetime.now():%Y-%m-%d-%H%M%S}-{uuid4().hex[:6]}.wav'
        try:
            self.file = wave.open(str(self.path), 'wb')
            self.file.setnchannels(fmt.channelCount())
            self.file.setsampwidth(2)
            self.file.setframerate(fmt.sampleRate())
            self.format = fmt
            self.byte_count = 0
            self.remainder = b''
            self.source = QAudioSource(device, fmt, self)
            self.stream = self.source.start()
            if self.stream is None or self.source.error() != QtAudio.Error.NoError:
                raise RuntimeError('Устройство не удалось открыть. Проверьте доступ к микрофону.')
            self.stream.readyRead.connect(self.read_audio)
            self.source.stateChanged.connect(self.audio_state)
            self.started = time.monotonic()
            self.devices.setEnabled(False)
            self.refresh.setEnabled(False)
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.consent.setEnabled(False)
            self.message.setText('Идёт запись. Звук не передаётся в интернет.')
            self.timer.start(200)
            self.active_changed.emit(True)
        except Exception as exc:
            self.stop(announce=False)
            self.message.setText(str(exc))

    def read_audio(self):
        if not self.stream or not self.file:
            return
        try:
            raw = self.remainder + bytes(self.stream.readAll())
            frame_size = self.format.bytesPerFrame()
            boundary = len(raw) // frame_size * frame_size
            self.remainder = raw[boundary:]
            values = samples(raw[:boundary], self.format)
            gain = self.gain.value() / 100
            self.meter.feed(values, gain)
            data = pcm16(values, gain)
            self.file.writeframesraw(data)
            self.byte_count += len(data)
            if self.byte_count >= 480 * 1024 * 1024:
                self.stop()
        except Exception as exc:
            self.stop(announce=False)
            self.message.setText('Ошибка записи: ' + str(exc))

    def audio_state(self, state):
        if self.source and state == QtAudio.State.StoppedState and self.source.error() != QtAudio.Error.NoError:
            self.stop(announce=False)
            self.message.setText('Устройство отключено или недоступно. Полученная часть записи сохранена.')

    def tick(self):
        elapsed = time.monotonic() - self.started
        self.clock.setText(timestamp(elapsed * 1000))
        if elapsed >= 1800:
            self.stop()

    def stop(self, _checked=False, announce=True):
        self.timer.stop()
        source, self.source = self.source, None
        if source:
            source.stop()
            source.deleteLater()
        self.stream = None
        if self.file:
            self.file.close()
            self.file = None
        self.devices.setEnabled(True)
        self.refresh.setEnabled(True)
        self.consent.setEnabled(True)
        self.start_button.setEnabled(self.devices.count() > 0)
        self.stop_button.setEnabled(False)
        self.active_changed.emit(False)
        if self.path and self.byte_count:
            self.message.setText('Запись сохранена: ' + str(self.path))
            if announce:
                self.recorded.emit(str(self.path))
        elif self.path:
            self.path.unlink(missing_ok=True)
            self.message.setText('Аудиоданные не получены. Проверьте устройство.')
