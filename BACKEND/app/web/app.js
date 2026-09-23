const API = "/api/v1";
const state = { meetingId: null, file: null, meeting: null, pollTimer: null, meetings: [] };

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const esc = (value) => String(value ?? "")
  .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;").replaceAll("'", "&#039;");

function localDate() {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60000;
  return new Date(now - offset).toISOString().slice(0, 10);
}

function stamp(seconds) {
  const value = Math.max(0, Math.floor(Number(seconds) || 0));
  const hours = String(Math.floor(value / 3600)).padStart(2, "0");
  const minutes = String(Math.floor(value / 60) % 60).padStart(2, "0");
  const secs = String(value % 60).padStart(2, "0");
  return `${hours}:${minutes}:${secs}`;
}

async function request(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail || body);
    } catch (_) { /* keep HTTP fallback */ }
    throw new Error(detail);
  }
  const type = response.headers.get("content-type") || "";
  return type.includes("application/json") ? response.json() : response;
}

function showError(error, title = "Не удалось выполнить операцию.") {
  $("#errorPanel strong").textContent = title;
  $("#errorText").textContent = error instanceof Error ? error.message : String(error);
  $("#errorPanel").classList.remove("hidden");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function hideError() { $("#errorPanel").classList.add("hidden"); }
function toast(message) {
  const node = $("#toast");
  node.textContent = message;
  node.classList.add("show");
  setTimeout(() => node.classList.remove("show"), 2400);
}

function showView(name) {
  $$(".view").forEach((view) => view.classList.remove("active"));
  $(`#${name}View`).classList.add("active");
}

async function loadMode() {
  try {
    const health = await request("/health");
    const real = health.mode === "real_ai";
    const pill = $("#modePill");
    pill.className = `mode-pill ${real ? "mode-real" : "mode-demo"}`;
    pill.innerHTML = `<span></span>${real ? "REAL AI" : "DEMO MODE"}`;
    const notice = $("#modeNotice");
    notice.className = `notice ${real ? "notice-real" : "notice-demo"}`;
    notice.textContent = real
      ? "REAL AI: запись будет отправлена в OpenAI для транскрибации со спикерами и структурного анализа."
      : "DEMO MODE: OpenAI API key не настроен. Можно пройти весь сценарий на демонстрационных данных.";
  } catch (error) {
    showError(error, "Backend недоступен.");
  }
}

const statusLabels = {
  created: "Создано", uploaded: "Файл загружен", processing: "Обработка", completed: "Готово",
  partial: "Готово с предупреждениями", failed: "Ошибка",
};

async function loadMeetings() {
  try {
    state.meetings = await request(`${API}/meetings`);
    renderMeetings();
  } catch (error) { showError(error); }
}

function renderMeetings() {
  const root = $("#meetingList");
  if (!state.meetings.length) {
    root.innerHTML = '<div class="empty-small">Здесь появятся ваши протоколы</div>';
    return;
  }
  root.innerHTML = state.meetings.map((item) => `
    <button class="meeting-item ${item.id === state.meetingId ? "active" : ""}" data-id="${item.id}" type="button">
      <strong>${esc(item.title)}</strong>
      <small><span>${esc(item.meeting_date)}</span><span class="status-dot ${item.status === "failed" ? "status-failed" : ""}">${esc(statusLabels[item.status] || item.status)}</span></small>
    </button>`).join("");
  root.querySelectorAll(".meeting-item").forEach((button) => button.addEventListener("click", () => openMeeting(Number(button.dataset.id))));
}

function selectFile(file) {
  if (!file) return;
  const extension = `.${file.name.split(".").pop().toLowerCase()}`;
  const allowed = [".flac", ".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".ogg", ".wav", ".webm"];
  if (!allowed.includes(extension)) {
    showError(new Error("Поддерживаются FLAC, MP3, MP4, MPEG, MPGA, M4A, OGG, WAV и WEBM."), "Формат файла не поддерживается.");
    return;
  }
  if (file.size > 25 * 1024 * 1024) {
    showError(new Error("Выберите файл размером не более 25 МБ."), "Файл слишком большой.");
    return;
  }
  hideError();
  state.file = file;
  $("#dropZone").classList.add("has-file");
  $("#dropTitle").textContent = file.name;
  $("#dropSubtitle").textContent = `${(file.size / 1024 / 1024).toFixed(1)} МБ · готов к обработке`;
  $("#startButton").disabled = false;
  if (!$("#meetingTitle").value.trim()) $("#meetingTitle").value = file.name.replace(/\.[^.]+$/, "");
}

function resetCreate() {
  clearTimeout(state.pollTimer);
  state.meetingId = null;
  state.meeting = null;
  state.file = null;
  $("#meetingForm").reset();
  $("#meetingDate").value = localDate();
  $("#dropZone").classList.remove("has-file");
  $("#dropTitle").textContent = "Перетащите запись сюда";
  $("#dropSubtitle").textContent = "или нажмите, чтобы выбрать файл";
  $("#startButton").disabled = true;
  $("#startButton span").textContent = "Начать обработку";
  hideError();
  showView("create");
  renderMeetings();
}

async function startProcessing(event) {
  event.preventDefault();
  if (!state.file) return;
  hideError();
  const button = $("#startButton");
  button.disabled = true;
  button.querySelector("span").textContent = "Загружаем…";
  try {
    const meeting = await request(`${API}/meetings`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: $("#meetingTitle").value.trim(), meeting_date: $("#meetingDate").value }),
    });
    state.meetingId = meeting.id;
    const form = new FormData();
    form.append("file", state.file, state.file.name);
    await request(`${API}/meetings/${meeting.id}/upload`, { method: "POST", body: form });
    showView("processing");
    $("#processingTitle").textContent = meeting.title;
    $("#processingFile").textContent = state.file.name;
    renderProgress({ stage: "uploaded", progress: 5, status: "uploaded" });
    await request(`${API}/meetings/${meeting.id}/process`, { method: "POST" });
    await loadMeetings();
    pollStatus();
  } catch (error) {
    button.disabled = false;
    button.querySelector("span").textContent = "Начать обработку";
    showError(error, "Не удалось запустить обработку.");
    showView("create");
  }
}

const stageMap = {
  created: ["upload", "Подготовка", 0], uploaded: ["upload", "Файл загружен", 5], queued: ["speech", "Запуск обработки", 8],
  file_validation: ["speech", "Проверка записи", 10], audio_extraction: ["speech", "Извлечение аудио", 15],
  audio_preprocessing: ["speech", "Подготовка аудио", 20], speech_to_text: ["speech", "Распознавание речи", 35],
  speaker_diarization: ["speakers", "Определение спикеров", 60], merge_transcript: ["speakers", "Сборка транскрипта", 70],
  speaker_mapping: ["speakers", "Сопоставление участников", 75], task_extraction: ["analysis", "Анализ поручений", 82],
  deadline_normalization: ["analysis", "Проверка дедлайнов", 88], summarization: ["protocol", "Формирование резюме", 94],
  saving_results: ["protocol", "Сохранение протокола", 98], completed: ["done", "Готово", 100],
  completed_with_warnings: ["done", "Готово с предупреждениями", 100], failed: ["analysis", "Ошибка обработки", 100],
};
const progressOrder = ["upload", "speech", "speakers", "analysis", "protocol", "done"];

function renderProgress(status) {
  const [active, label, fallback] = stageMap[status.stage] || stageMap[status.status] || ["speech", status.stage, status.progress];
  const value = Math.max(Number(status.progress) || 0, fallback || 0);
  $("#progressStage").textContent = label;
  $("#progressValue").textContent = `${value}%`;
  $("#progressBar").style.width = `${value}%`;
  const activeIndex = progressOrder.indexOf(active);
  $$("#progressSteps li").forEach((item) => {
    const index = progressOrder.indexOf(item.dataset.key);
    item.classList.toggle("done", index < activeIndex || value === 100);
    item.classList.toggle("active", index === activeIndex && value < 100);
  });
}

async function pollStatus() {
  try {
    const status = await request(`${API}/meetings/${state.meetingId}/status`);
    renderProgress(status);
    if (["completed", "partial"].includes(status.status)) {
      await new Promise((resolve) => setTimeout(resolve, 450));
      await openMeeting(state.meetingId);
      return;
    }
    if (status.status === "failed") {
      showError(new Error(status.error || "Неизвестная ошибка pipeline."), "Не удалось обработать запись.");
      await loadMeetings();
      return;
    }
    state.pollTimer = setTimeout(pollStatus, 900);
  } catch (error) {
    showError(error, "Потеряно соединение с backend.");
  }
}

async function openMeeting(id) {
  clearTimeout(state.pollTimer);
  state.meetingId = id;
  hideError();
  try {
    const meeting = await request(`${API}/meetings/${id}`);
    state.meeting = meeting;
    renderMeetings();
    if (["created", "uploaded", "processing"].includes(meeting.status)) {
      showView("processing");
      $("#processingTitle").textContent = meeting.title;
      $("#processingFile").textContent = meeting.source_filename || "";
      renderProgress(meeting);
      pollStatus();
      return;
    }
    if (meeting.status === "failed") {
      showView("processing");
      renderProgress(meeting);
      showError(new Error(meeting.error || "Неизвестная ошибка pipeline."), "Не удалось обработать запись.");
      return;
    }
    renderResult(meeting);
    showView("result");
  } catch (error) { showError(error, "Не удалось открыть совещание."); }
}

const list = (items) => items?.length ? `<ul>${items.map((item) => `<li>${esc(item)}</li>`).join("")}</ul>` : '<p class="muted">Не выявлено</p>';

function renderResult(meeting) {
  const summary = meeting.summary || { topic: "Не определена", summary_text: "Резюме не сформировано", key_points: [], decisions: [], problems: [] };
  $("#resultTitle").textContent = meeting.title;
  $("#resultMeta").textContent = `${meeting.meeting_date} · ${meeting.source_filename || "без файла"}`;
  $("#taskCount").textContent = meeting.tasks.length;
  $("#downloadDocx").href = `${API}/meetings/${meeting.id}/export/docx`;
  $("#downloadPdf").href = `${API}/meetings/${meeting.id}/export/pdf`;

  $("#overviewTab").innerHTML = `
    <div class="summary-grid">
      <section class="info-block info-block-wide"><p class="eyebrow">ТЕМА</p><h3>${esc(summary.topic)}</h3><p>${esc(summary.summary_text)}</p></section>
      <section class="info-block"><h3>Ключевые моменты</h3>${list(summary.key_points)}</section>
      <section class="info-block"><h3>Принятые решения</h3>${list(summary.decisions)}</section>
      <section class="info-block info-block-wide"><h3>Проблемы</h3>${list(summary.problems)}</section>
    </div>`;
  renderTasks(meeting.tasks);
  renderParticipants(meeting.participants);
  renderTranscript(meeting.transcript);
  renderProtocol(meeting);
  switchTab("overview");
}

function renderTasks(tasks) {
  const root = $("#tasksTab");
  if (!tasks.length) {
    root.innerHTML = '<div class="empty-state"><h3>Поручения не выявлены</h3><p>Система не добавляет задачи, которых не было в разговоре.</p></div>';
    return;
  }
  root.innerHTML = `<div class="task-grid">${tasks.map((task, index) => `
    <article class="task-card" data-task="${task.id}">
      <div class="task-top"><strong>${index + 1}. ${esc(task.task)}</strong><span class="confidence">${Math.round(task.confidence * 100)}% confidence</span></div>
      <div class="edit-grid">
        <label>Задача<input data-field="task" value="${esc(task.task)}"></label>
        <label>Ответственный<input data-field="responsible" value="${esc(task.responsible)}"></label>
        <label>Кто поручил<input data-field="assigned_by" value="${esc(task.assigned_by)}"></label>
        <label>Срок<input data-field="deadline_normalized" type="date" value="${esc(task.deadline_normalized || "")}"></label>
      </div>
      <p class="source-quote">«${esc(task.original_text)}»</p>
      <button class="button button-secondary save-task" type="button">Сохранить изменения</button>
    </article>`).join("")}</div>`;
  root.querySelectorAll(".save-task").forEach((button) => button.addEventListener("click", saveTask));
}

async function saveTask(event) {
  const card = event.currentTarget.closest(".task-card");
  const payload = {};
  card.querySelectorAll("[data-field]").forEach((input) => { payload[input.dataset.field] = input.value.trim() || null; });
  if (!payload.task || !payload.responsible || !payload.assigned_by) {
    showError(new Error("Задача, ответственный и автор поручения не могут быть пустыми."));
    return;
  }
  try {
    await request(`${API}/meetings/${state.meetingId}/tasks/${card.dataset.task}`, {
      method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    });
    toast("Поручение сохранено");
    await openMeeting(state.meetingId);
    switchTab("tasks");
  } catch (error) { showError(error, "Не удалось сохранить поручение."); }
}

function renderParticipants(participants) {
  const root = $("#participantsTab");
  if (!participants.length) {
    root.innerHTML = '<div class="empty-state">Участники пока не определены</div>';
    return;
  }
  root.innerHTML = `<div class="participant-grid">${participants.map((person) => `
    <div class="participant-row" data-participant="${person.id}">
      <span class="speaker-label">${esc(person.speaker_label)}</span>
      <input data-field="display_name" aria-label="Имя участника" value="${esc(person.display_name)}">
      <input data-field="role" aria-label="Роль участника" placeholder="Должность / роль" value="${esc(person.role || "")}">
      <button class="button button-secondary save-participant" type="button">Сохранить</button>
    </div>`).join("")}</div>`;
  root.querySelectorAll(".save-participant").forEach((button) => button.addEventListener("click", saveParticipant));
}

async function saveParticipant(event) {
  const row = event.currentTarget.closest(".participant-row");
  const name = row.querySelector('[data-field="display_name"]').value.trim();
  const role = row.querySelector('[data-field="role"]').value.trim();
  if (!name) return showError(new Error("Имя участника не может быть пустым."));
  try {
    await request(`${API}/meetings/${state.meetingId}/participants/${row.dataset.participant}`, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ display_name: name, role: role || null }),
    });
    toast("Участник обновлён во всём протоколе");
    await openMeeting(state.meetingId);
    switchTab("participants");
  } catch (error) { showError(error, "Не удалось изменить участника."); }
}

function renderTranscript(transcript) {
  $("#transcriptTab").innerHTML = transcript.length ? `<div class="transcript">${[...transcript]
    .sort((a, b) => a.start - b.start).map((segment) => `
      <div class="transcript-row"><span class="timecode">${stamp(segment.start)}</span>
        <span class="speaker"><strong>${esc(segment.speaker_name)}</strong><small>${esc(segment.speaker_role || segment.speaker_label)}</small></span>
        <p>${esc(segment.text)}</p></div>`).join("")}</div>` : '<div class="empty-state">Транскрипт отсутствует</div>';
}

function renderProtocol(meeting) {
  const summary = meeting.summary || {};
  const people = meeting.participants.map((person) => esc(person.display_name)).join(", ") || "Не указаны";
  const tasks = meeting.tasks.length ? `<table><thead><tr><th>Поручение</th><th>Ответственный</th><th>Срок</th></tr></thead><tbody>${meeting.tasks.map((task) =>
    `<tr><td>${esc(task.task)}</td><td>${esc(task.responsible)}</td><td>${esc(task.deadline_normalized || task.deadline_raw || "—")}</td></tr>`).join("")}</tbody></table>` : "<p>Поручения не выявлены.</p>";
  $("#protocolTab").innerHTML = `<article class="protocol-sheet">
    <h2>ПРОТОКОЛ СОВЕЩАНИЯ</h2><p><b>Название:</b> ${esc(meeting.title)}</p><p><b>Дата:</b> ${esc(meeting.meeting_date)}</p>
    <p><b>Участники:</b> ${people}</p><h3>Тема</h3><p>${esc(summary.topic || "Не определена")}</p>
    <h3>Краткое содержание</h3><p>${esc(summary.summary_text || "Не сформировано")}</p>
    <h3>Ключевые вопросы</h3>${list(summary.key_points || [])}<h3>Решения</h3>${list(summary.decisions || [])}
    <h3>Поручения</h3>${tasks}</article>`;
}

function switchTab(name) {
  $$("#resultTabs button").forEach((button) => button.classList.toggle("active", button.dataset.tab === name));
  $$(".tab-panel").forEach((panel) => panel.classList.toggle("active", panel.id === `${name}Tab`));
}

function bindEvents() {
  $("#meetingDate").value = localDate();
  $("#dropZone").addEventListener("click", () => $("#mediaFile").click());
  $("#dropZone").addEventListener("keydown", (event) => { if (["Enter", " "].includes(event.key)) $("#mediaFile").click(); });
  $("#mediaFile").addEventListener("change", (event) => selectFile(event.target.files[0]));
  ["dragenter", "dragover"].forEach((name) => $("#dropZone").addEventListener(name, (event) => { event.preventDefault(); $("#dropZone").classList.add("dragover"); }));
  ["dragleave", "drop"].forEach((name) => $("#dropZone").addEventListener(name, (event) => { event.preventDefault(); $("#dropZone").classList.remove("dragover"); }));
  $("#dropZone").addEventListener("drop", (event) => selectFile(event.dataTransfer.files[0]));
  $("#meetingForm").addEventListener("submit", startProcessing);
  $("#newMeetingButton").addEventListener("click", resetCreate);
  $("#refreshMeetings").addEventListener("click", loadMeetings);
  $("#closeError").addEventListener("click", hideError);
  $$("#resultTabs button").forEach((button) => button.addEventListener("click", () => switchTab(button.dataset.tab)));
}

async function init() {
  bindEvents();
  await Promise.all([loadMode(), loadMeetings()]);
}

init();
