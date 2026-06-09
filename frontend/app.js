const state = {
  events: [],
  incidents: [],
  faces: [],
  facesFingerprint: "",
  camera: {
    stream: null,
    scanTimer: null,
    scanning: false,
    speakingEnabled: true,
    attendanceCooldownMs: 12_000,
    lastAttendanceByPerson: {},
    policy: null,
    selectedEventType: "check_in",
  },
  pendingPhotoPersonId: null,
  facePhotoVersions: {},
  reportEvents: [],
  reportSummary: {
    total: 0,
    check_ins: 0,
    check_outs: 0,
    duplicates: 0,
    rejected: 0,
  },
  registerProgressTimer: null,
  registerElapsedTimer: null,
  toastTimer: null,
  registerInProgress: false,
  backgroundRefreshPaused: false,
  refreshTimer: null,
};

const apiBaseInput = document.querySelector("#api-base");
const toast = document.querySelector("#toast");
const registerResult = document.querySelector("#face-register-result");
const faceRegisterForm = document.querySelector("#face-register-form");
const faceRegisterSubmit = document.querySelector("#face-register-submit");
const registerStatus = document.querySelector("#register-status");
const registerStatusTitle = document.querySelector("#register-status-title");
const registerStatusDetail = document.querySelector("#register-status-detail");
const registerProgress = document.querySelector("#register-progress");
const registerProgressBar = document.querySelector("#register-progress-bar");
const registerFilesSummary = document.querySelector("#register-files-summary");
const cameraPreview = document.querySelector("#face-camera-preview");
const cameraCanvas = document.querySelector("#face-camera-canvas");
const startCameraBtn = document.querySelector("#start-camera-btn");
const stopCameraBtn = document.querySelector("#stop-camera-btn");
const scanCameraBtn = document.querySelector("#scan-camera-btn");
const scanCheckInBtn = document.querySelector("#scan-check-in-btn");
const scanCheckOutBtn = document.querySelector("#scan-check-out-btn");
const scanModeCheckInBtn = document.querySelector("#scan-mode-check-in");
const scanModeCheckOutBtn = document.querySelector("#scan-mode-check-out");
const scanModeLabel = document.querySelector("#scan-mode-label");
const autoScanInput = document.querySelector("#camera-auto-scan");
const livenessEnabledInput = document.querySelector("#liveness-enabled");
const livenessStepsEl = document.querySelector("#liveness-steps");
const cameraStatus = document.querySelector("#camera-status");
const cameraNextAction = document.querySelector("#camera-next-action");
const cameraFacesCount = document.querySelector("#camera-faces-count");
const scanOverlay = document.querySelector("#scan-overlay");
const scanPreviewWrap = document.querySelector(".camera-preview-wrap");
const scanResultCard = document.querySelector("#scan-result-card");
const scanResultIcon = document.querySelector("#scan-result-icon");
const scanResultTitle = document.querySelector("#scan-result-title");
const scanResultDetail = document.querySelector("#scan-result-detail");
const userEditDialog = document.querySelector("#user-edit-dialog");
const userEditForm = document.querySelector("#user-edit-form");
const showInactiveUsersInput = document.querySelector("#show-inactive-users");
const userPhotoInput = document.querySelector("#user-photo-input");
const eventEditDialog = document.querySelector("#event-edit-dialog");
const eventEditForm = document.querySelector("#event-edit-form");

document.querySelector("#today-label").textContent = new Intl.DateTimeFormat("es-PE", {
  weekday: "long",
  year: "numeric",
  month: "long",
  day: "numeric",
}).format(new Date());

const viewTitles = {
  overview: "Panel de asistencia facial",
  attendance: "Registro de asistencia",
  register: "Registrar rostro",
  scan: "Escanear y marcar asistencia",
  users: "Usuarios registrados",
  reports: "Reporte de entradas y salidas",
  incidents: "Incidencias de salida",
};

const viewSubtitles = {
  overview: "Resumen en tiempo real de tu operacion",
  attendance: "Registro manual y validacion de salidas",
  register: "Perfil facial multi-pose para reconocimiento robusto",
  scan: "Reconocimiento facial en vivo con anti-spoofing",
  users: "Colaboradores con perfil facial activo",
  reports: "Consulta, filtra y corrige marcas de asistencia",
  incidents: "Salidas anticipadas y violaciones de politica",
};

function setViewHeader(viewKey) {
  const title = document.querySelector(".topbar h1");
  const subtitle = document.querySelector("#view-subtitle");
  if (title) title.textContent = viewTitles[viewKey] || "IA Facial";
  if (subtitle) subtitle.textContent = viewSubtitles[viewKey] || "";
}

document.querySelectorAll(".nav-item").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
    button.classList.add("active");
    document.querySelector(`#view-${button.dataset.view}`).classList.add("active");
    setViewHeader(button.dataset.view);
    if (button.dataset.view !== "scan") {
      stopCamera();
    }
  });
});

document.querySelector("#refresh-btn").addEventListener("click", refreshAll);
document.querySelector("#reload-incidents").addEventListener("click", refreshIncidents);
document.querySelector("#reload-reports")?.addEventListener("click", refreshReport);
document.querySelector("#report-filters")?.addEventListener("submit", handleReportFilterSubmit);
document.querySelector("#report-table-wrap")?.addEventListener("click", handleReportTableAction);
eventEditForm?.addEventListener("submit", submitEventEdit);
document.querySelector("#event-edit-cancel")?.addEventListener("click", closeEventEditDialog);
document.querySelector("#event-form").addEventListener("submit", submitAttendanceEvent);
document.querySelector("#exit-form").addEventListener("submit", submitExitAttempt);
document.querySelector("#face-register-form").addEventListener("submit", submitFaceRegister);
faceRegisterForm?.addEventListener("change", handleRegisterFormChange);
startCameraBtn?.addEventListener("click", startCamera);
stopCameraBtn?.addEventListener("click", stopCamera);
scanCameraBtn?.addEventListener("click", () => scanFromCamera());
scanCheckInBtn?.addEventListener("click", () => scanWithEventType("check_in"));
scanCheckOutBtn?.addEventListener("click", () => scanWithEventType("check_out"));
scanModeCheckInBtn?.addEventListener("click", () => setScanEventType("check_in"));
scanModeCheckOutBtn?.addEventListener("click", () => setScanEventType("check_out"));
autoScanInput?.addEventListener("change", toggleAutoScan);
setScanEventType("check_in");
document.querySelector("#registered-users")?.addEventListener("click", handleUserCardAction);
userEditForm?.addEventListener("submit", submitUserEdit);
document.querySelector("#user-edit-cancel")?.addEventListener("click", closeUserEditDialog);
showInactiveUsersInput?.addEventListener("change", renderRegisteredUsers);
userPhotoInput?.addEventListener("change", handleQuickPhotoSelected);

refreshAll();
setViewHeader("overview");
state.refreshTimer = window.setInterval(() => {
  refreshAll().catch(() => {});
}, 30_000);
if (faceRegisterForm) updateRegisterFilesSummary(faceRegisterForm);

function pauseBackgroundRefresh(paused) {
  state.backgroundRefreshPaused = paused;
}

function apiBase() {
  return apiBaseInput.value.replace(/\/$/, "");
}

async function refreshAll() {
  if (state.backgroundRefreshPaused || state.registerInProgress) return;
  const activeView = document.querySelector(".nav-item.active")?.dataset.view || "";
  const tasks = [refreshHealth(), refreshEvents(), refreshIncidents()];
  if (activeView !== "scan") {
    tasks.push(refreshFaces());
  }
  if (activeView === "reports") {
    tasks.push(refreshReport());
  }
  if (activeView === "scan" || state.camera.stream) {
    tasks.push(refreshAttendancePolicy());
  }
  await Promise.allSettled(tasks);
  renderDashboard();
}

async function refreshAttendancePolicy() {
  try {
    state.camera.policy = await requestJson("/api/v1/attendance/policy");
  } catch (error) {
    state.camera.policy = null;
  }
}

async function refreshHealth() {
  if (state.backgroundRefreshPaused || state.registerInProgress || state.camera.scanning) {
    return;
  }
  try {
    await requestJson("/api/v1/health", { timeoutMs: 8000 });
    setApiStatus(true);
  } catch (error) {
    if (!state.camera.scanning && !state.registerInProgress) {
      setApiStatus(false);
    }
  }
}

async function refreshEvents() {
  const data = await requestJson("/api/v1/attendance/events?limit=50");
  state.events = data.events || [];
  renderEvents();
}

async function refreshReport() {
  const form = document.querySelector("#report-filters");
  const params = new URLSearchParams({ limit: "300" });
  if (form) {
    const filters = new FormData(form);
    const personId = String(filters.get("person_id") || "").trim();
    const eventType = String(filters.get("event_type") || "").trim();
    const dateFrom = String(filters.get("date_from") || "").trim();
    const dateTo = String(filters.get("date_to") || "").trim();
    if (personId) params.set("person_id", personId);
    if (eventType) params.set("event_type", eventType);
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
  }
  const data = await requestJson(`/api/v1/attendance/events?${params.toString()}`);
  state.reportEvents = data.events || [];
  state.reportSummary = data.summary || state.reportSummary;
  renderReport();
}

function handleReportFilterSubmit(event) {
  event.preventDefault();
  refreshReport().catch(() => showToast("No se pudo cargar el reporte"));
}

function renderReport() {
  const wrap = document.querySelector("#report-table-wrap");
  if (!wrap) return;

  document.querySelector("#report-total").textContent = state.reportSummary.total ?? 0;
  document.querySelector("#report-check-ins").textContent = state.reportSummary.check_ins ?? 0;
  document.querySelector("#report-check-outs").textContent = state.reportSummary.check_outs ?? 0;
  document.querySelector("#report-duplicates").textContent = state.reportSummary.duplicates ?? 0;
  document.querySelector("#report-rejected").textContent = state.reportSummary.rejected ?? 0;

  if (!state.reportEvents.length) {
    wrap.className = "report-table-wrap empty";
    wrap.innerHTML = `
      <div class="empty-state">
        <span class="empty-icon">📋</span>
        <p>Sin marcas para los filtros seleccionados</p>
        <small>Prueba otros filtros o escanea para generar registros</small>
      </div>`;
    return;
  }

  wrap.className = "report-table-wrap";
  wrap.innerHTML = `
    <table class="report-table">
      <thead>
        <tr>
          <th>Fecha y hora</th>
          <th>Empleado</th>
          <th>Codigo</th>
          <th>Tipo</th>
          <th>Dispositivo</th>
          <th>Estado</th>
          <th>Accion</th>
        </tr>
      </thead>
      <tbody>
        ${state.reportEvents
          .map((event) => {
            const typeLabel = event.event_type === "check_out" ? "Salida" : "Entrada";
            const typeClass = event.event_type === "check_out" ? "check-out" : "check-in";
            const status = getEventStatusLabel(event);
            const rowClass = !event.accepted || event.duplicate ? "row-bad" : "";
            return `
              <tr class="${rowClass}">
                <td>${formatDate(event.captured_at)}</td>
                <td>${escapeHtml(event.employee_name || "-")}</td>
                <td><code>${escapeHtml(event.person_id)}</code></td>
                <td><span class="event-type ${typeClass}">${typeLabel}</span></td>
                <td>${escapeHtml(event.device_id)}</td>
                <td>${status}</td>
                <td class="report-actions">
                  <button class="ghost-btn" type="button" data-report-action="edit" data-event-id="${escapeHtml(event.event_id)}">Editar</button>
                  <button class="danger-btn" type="button" data-report-action="delete" data-event-id="${escapeHtml(event.event_id)}">Eliminar</button>
                </td>
              </tr>
            `;
          })
          .join("")}
      </tbody>
    </table>
  `;
}

function getEventStatusLabel(event) {
  if (event.duplicate) return '<span class="badge warn">Duplicado</span>';
  if (!event.accepted) return '<span class="badge bad">Rechazado</span>';
  return '<span class="badge ok">Aceptado</span>';
}

function handleReportTableAction(event) {
  const button = event.target.closest("[data-report-action]");
  if (!button) return;
  const eventId = button.dataset.eventId;
  const attendanceEvent = state.reportEvents.find((item) => item.event_id === eventId);
  if (!attendanceEvent) return;
  if (button.dataset.reportAction === "edit") {
    openEventEditDialog(attendanceEvent);
    return;
  }
  if (button.dataset.reportAction === "delete") {
    deleteAttendanceEvent(attendanceEvent);
  }
}

async function deleteAttendanceEvent(event) {
  const label = event.employee_name || event.person_id;
  const tipo = event.event_type === "check_out" ? "salida" : "entrada";
  const confirmed = window.confirm(
    `¿Eliminar la marca de ${tipo} de ${label}?\n${formatDate(event.captured_at)}\nEsta accion no se puede deshacer.`,
  );
  if (!confirmed) return;

  const eventId = event.event_id;
  const prevReportEvents = state.reportEvents.slice();
  const prevEvents = state.events.slice();
  const prevSummary = { ...state.reportSummary };

  state.reportEvents = state.reportEvents.filter((item) => item.event_id !== eventId);
  state.events = state.events.filter((item) => item.event_id !== eventId);
  if (state.reportSummary.total > 0) {
    state.reportSummary.total -= 1;
    if (event.event_type === "check_in") state.reportSummary.check_ins -= 1;
    if (event.event_type === "check_out") state.reportSummary.check_outs -= 1;
    if (event.duplicate) state.reportSummary.duplicates -= 1;
    if (!event.accepted) state.reportSummary.rejected -= 1;
  }
  renderReport();
  renderEvents();
  renderDashboard();

  try {
    const data = await requestJson(
      `/api/v1/attendance/events/${encodeURIComponent(eventId)}`,
      { method: "DELETE" },
    );
    if (event.person_id) {
      delete state.camera.lastAttendanceByPerson[event.person_id];
    }
    showToast(data.message || "Marca eliminada");
  } catch (error) {
    state.reportEvents = prevReportEvents;
    state.events = prevEvents;
    state.reportSummary = prevSummary;
    renderReport();
    renderEvents();
    renderDashboard();
    showToast("No se pudo eliminar la marca");
  }
}

function openEventEditDialog(event) {
  if (!eventEditForm || !eventEditDialog) return;
  eventEditForm.event_id.value = event.event_id;
  eventEditForm.person_id.value = event.person_id;
  eventEditForm.employee_name.value = event.employee_name || "";
  eventEditForm.event_type.value = event.event_type;
  eventEditForm.captured_at.value = toDatetimeLocalValue(event.captured_at);
  eventEditForm.device_id.value = event.device_id || "";
  eventEditForm.source.value = event.source || "";
  eventEditForm.evidence_ref.value = event.evidence_ref || "";
  eventEditForm.accepted.checked = Boolean(event.accepted);
  eventEditForm.duplicate.checked = Boolean(event.duplicate);
  const meta = document.querySelector("#event-edit-meta");
  if (meta) {
    meta.textContent = `ID evento: ${event.event_id}`;
  }
  eventEditDialog.showModal();
}

function closeEventEditDialog() {
  eventEditDialog?.close();
}

async function submitEventEdit(formEvent) {
  formEvent.preventDefault();
  const form = new FormData(eventEditForm);
  const eventId = String(form.get("event_id") || "").trim();
  const payload = {
    employee_name: String(form.get("employee_name") || "").trim() || null,
    event_type: String(form.get("event_type") || "").trim(),
    captured_at: fromDatetimeLocalValue(String(form.get("captured_at") || "")),
    device_id: String(form.get("device_id") || "").trim(),
    source: String(form.get("source") || "").trim() || null,
    evidence_ref: String(form.get("evidence_ref") || "").trim() || null,
    accepted: form.get("accepted") === "on",
    duplicate: form.get("duplicate") === "on",
  };
  try {
    const data = await requestJson(`/api/v1/attendance/events/${encodeURIComponent(eventId)}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    closeEventEditDialog();
    showToast(data.message || "Marca corregida");
    const updated = data.event;
    if (updated?.event_id) {
      state.reportEvents = state.reportEvents.map((item) =>
        item.event_id === updated.event_id ? { ...item, ...updated } : item,
      );
      state.events = state.events.map((item) =>
        item.event_id === updated.event_id ? { ...item, ...updated } : item,
      );
      renderReport();
      renderEvents();
      renderDashboard();
    }
  } catch (error) {
    showToast("No se pudo corregir la marca");
  }
}

function toDatetimeLocalValue(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function fromDatetimeLocalValue(value) {
  if (!value) return new Date().toISOString();
  return new Date(value).toISOString();
}

async function refreshIncidents() {
  const data = await requestJson("/api/v1/attendance/incidents");
  state.incidents = data.incidents || [];
  renderIncidents();
  renderDashboard();
}

async function refreshFaces() {
  const data = await requestJson("/api/v1/faces/registered");
  const fingerprint = (data.faces || [])
    .map((face) => `${face.person_id}:${face.is_active}:${face.embedding_count}:${face.created_at}`)
    .join("|");
  if (fingerprint === state.facesFingerprint) return;
  state.facesFingerprint = fingerprint;
  state.faces = data.faces || [];
  renderDashboard();
  renderRegisteredUsers();
  updateFacesCountLabel();
}

function renderRegisteredUsers() {
  const container = document.querySelector("#registered-users");
  const countLabel = document.querySelector("#users-count-label");
  const noPhotoAlert = document.querySelector("#users-no-photo-alert");
  if (!container) return;

  const showInactive = showInactiveUsersInput?.checked !== false;
  const visibleFaces = state.faces.filter(
    (face) => showInactive || face.is_active !== false,
  );
  const count = visibleFaces.length;
  const activeCount = state.faces.filter((face) => face.is_active !== false).length;
  const withoutPhoto = visibleFaces.filter((face) => !hasFacePhoto(face)).length;
  if (countLabel) {
    countLabel.textContent =
      count === 1
        ? `1 persona (${activeCount} activos)`
        : `${count} personas (${activeCount} activos)`;
  }
  if (noPhotoAlert) {
    if (count > 0 && withoutPhoto > 0) {
      noPhotoAlert.classList.remove("hidden");
      noPhotoAlert.textContent =
        `${withoutPhoto} usuario(s) sin foto. Usa el boton "Subir foto" en cada tarjeta para agregar la imagen desde aqui.`;
    } else {
      noPhotoAlert.classList.add("hidden");
      noPhotoAlert.textContent = "";
    }
  }

  if (!count) {
    container.className = "users-grid empty";
    container.innerHTML = `
      <div class="empty-state">
        <span class="empty-icon">${state.faces.length ? "🔍" : "👤"}</span>
        <p>${state.faces.length
          ? "No hay usuarios activos visibles"
          : "Sin usuarios registrados"}</p>
        <small>${state.faces.length
          ? "Marca 'Mostrar inactivos' para verlos"
          : "Ve a Registrar rostro y guarda el primer perfil facial"}</small>
      </div>`;
    return;
  }

  container.className = "users-grid";
  container.innerHTML = visibleFaces
    .map((face) => {
      const photoUrl = resolveFaceImageUrl(face);
      const initials = getInitials(face.name || face.person_id);
      const photoMarkup = photoUrl
        ? `<img class="user-card-photo" src="${escapeHtml(photoUrl)}" alt="Foto de ${escapeHtml(face.name)}" loading="lazy" data-initials="${escapeHtml(initials)}" onerror="handleUserPhotoError(this)" />`
        : `<div class="user-card-photo missing">Sin foto<br><small>Pulsa Subir foto</small></div>`;
      const isInactive = face.is_active === false;
      const statusBadge = isInactive ? "bad" : "ok";
      const statusLabel = isInactive ? "Inactivo" : "Activo";
      const toggleAction = isInactive ? "activate" : "deactivate";
      const toggleLabel = isInactive ? "Reactivar" : "Desactivar";
      return `
        <article class="user-card${isInactive ? " inactive" : ""}">
          <div class="user-card-photo-wrap">${photoMarkup}</div>
          <div class="user-card-body">
            <strong>${escapeHtml(face.name)}</strong>
            <div class="user-card-meta">
              <span><b>Codigo:</b> ${escapeHtml(face.employee_code || face.person_id)}</span>
              <span><b>ID:</b> ${escapeHtml(face.person_id)}</span>
              <span><b>Correo:</b> ${escapeHtml(face.email || "Sin correo")}</span>
              <span><b>Modelo:</b> ${escapeHtml(face.model)}</span>
              <span><b>Embeddings:</b> ${face.embedding_count ?? 1}</span>
              <span><b>Registro:</b> ${formatDate(face.created_at)}</span>
            </div>
            <div class="user-card-status">
              <span class="badge ${statusBadge}">${statusLabel}</span>
            </div>
            <div class="user-card-actions">
              <button class="primary-btn" type="button" data-user-action="photo" data-person-id="${escapeHtml(face.person_id)}">${photoUrl ? "Cambiar foto" : "Subir foto"}</button>
              <button class="ghost-btn" type="button" data-user-action="edit" data-person-id="${escapeHtml(face.person_id)}">Editar</button>
              <button class="${isInactive ? "ghost-btn" : "danger-btn"}" type="button" data-user-action="${toggleAction}" data-person-id="${escapeHtml(face.person_id)}">${toggleLabel}</button>
            </div>
          </div>
        </article>
      `;
    })
    .join("");
}

function handleUserCardAction(event) {
  const button = event.target.closest("[data-user-action]");
  if (!button) return;

  const personId = button.dataset.personId;
  const action = button.dataset.userAction;
  const face = state.faces.find((item) => item.person_id === personId);
  if (!face) return;

  if (action === "photo") {
    openQuickPhotoPicker(personId);
    return;
  }
  if (action === "edit") {
    openUserEditDialog(face);
    return;
  }
  if (action === "deactivate") {
    toggleEmployeeStatus(face, false);
    return;
  }
  if (action === "activate") {
    toggleEmployeeStatus(face, true);
  }
}

function openQuickPhotoPicker(personId) {
  if (!userPhotoInput) return;
  state.pendingPhotoPersonId = personId;
  userPhotoInput.value = "";
  userPhotoInput.click();
}

async function handleQuickPhotoSelected(event) {
  const file = event.target.files?.[0];
  const personId = state.pendingPhotoPersonId;
  state.pendingPhotoPersonId = null;
  if (!file || !personId) return;
  await uploadEmployeePhoto(personId, file);
  event.target.value = "";
}

async function uploadEmployeePhoto(personId, file) {
  const form = new FormData();
  form.append("file", file);
  try {
    showToast("Subiendo foto...", 4000, "info");
    const data = await requestForm(
      `/api/v1/faces/employees/${encodeURIComponent(personId)}/photo`,
      form,
      { silent: true },
    );
    state.facePhotoVersions[personId] = Date.now();
    showToast(data.message || "Foto actualizada", 4000, "success");
    await refreshFaces();
  } catch (error) {
    showToast(parseApiError(error), 6000, "error");
  }
}

function openUserEditDialog(face) {
  if (!userEditForm || !userEditDialog) return;
  userEditForm.person_id.value = face.person_id;
  userEditForm.name.value = face.name || "";
  userEditForm.employee_code.value = face.employee_code || face.person_id || "";
  userEditForm.email.value = face.email || "";
  if (userEditForm.photo) {
    userEditForm.photo.value = "";
  }
  const idLabel = document.querySelector("#user-edit-id-label");
  if (idLabel) {
    idLabel.textContent = `ID interno: ${face.person_id}`;
  }
  userEditDialog.showModal();
}

function closeUserEditDialog() {
  userEditDialog?.close();
}

async function submitUserEdit(event) {
  event.preventDefault();
  const submitBtn = userEditForm?.querySelector('[type="submit"]');
  const defaultLabel = submitBtn?.dataset.defaultLabel || submitBtn?.textContent || "Guardar cambios";
  setButtonLoading(submitBtn, true, "Guardando...", defaultLabel);

  const form = new FormData(userEditForm);
  const personId = String(form.get("person_id") || "").trim();
  const photoFile = form.get("photo");
  const payload = {
    name: String(form.get("name") || "").trim(),
    employee_code: String(form.get("employee_code") || "").trim(),
    email: String(form.get("email") || "").trim() || null,
  };
  try {
    const data = await requestJson(`/api/v1/faces/employees/${encodeURIComponent(personId)}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    if (photoFile instanceof File && photoFile.size > 0) {
      await uploadEmployeePhoto(personId, photoFile);
    } else {
      showToast(data.message || "Empleado actualizado", 4000, "success");
      await refreshFaces();
    }
    closeUserEditDialog();
  } catch (error) {
    showToast(parseApiError(error), 6000, "error");
  } finally {
    setButtonLoading(submitBtn, false, "", defaultLabel);
  }
}

async function toggleEmployeeStatus(face, isActive) {
  const actionLabel = isActive ? "reactivar" : "desactivar";
  const confirmed = window.confirm(
    isActive
      ? `¿Reactivar a ${face.name}? Volvera a poder escanearse.`
      : `¿Desactivar a ${face.name}? No podra escanearse, pero se conserva su historial.`,
  );
  if (!confirmed) return;

  try {
    const data = await requestJson(
      `/api/v1/faces/employees/${encodeURIComponent(face.person_id)}`,
      {
        method: "PATCH",
        body: JSON.stringify({ is_active: isActive }),
      },
    );
    const idx = state.faces.findIndex((item) => item.person_id === face.person_id);
    if (idx >= 0) {
      state.faces[idx] = data.person || { ...state.faces[idx], is_active: isActive };
      state.facesFingerprint = "";
    }
    renderRegisteredUsers();
    updateFacesCountLabel();
    showToast(data.message || `Empleado ${actionLabel}`);
  } catch (error) {
    await refreshFaces();
    showToast(`No se pudo ${actionLabel} el empleado`);
  }
}

function hasFacePhoto(face) {
  return Boolean(face?.image_url);
}

function resolveFaceImageUrl(face) {
  if (!face?.image_url) return null;
  const version = state.facePhotoVersions[face.person_id] || face.created_at || "";
  const cacheBuster = version ? `?v=${encodeURIComponent(version)}` : "";
  if (/^https?:\/\//i.test(face.image_url)) {
    return `${face.image_url}${cacheBuster}`;
  }
  const normalized = face.image_url.startsWith("/") ? face.image_url : `/${face.image_url}`;
  return `${apiBase()}${normalized}${cacheBuster}`;
}

function getInitials(value) {
  const parts = String(value || "?")
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (!parts.length) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0] || ""}${parts[1][0] || ""}`.toUpperCase();
}

function createUserPhotoPlaceholder(initials) {
  const node = document.createElement("div");
  node.className = "user-card-photo placeholder";
  node.textContent = initials;
  return node;
}

function handleUserPhotoError(img) {
  const initials = img?.dataset?.initials || "?";
  img.replaceWith(createUserPhotoPlaceholder(initials));
}

window.handleUserPhotoError = handleUserPhotoError;

function updateFacesCountLabel() {
  if (!cameraFacesCount) return;
  const n = state.faces.length;
  cameraFacesCount.textContent =
    n === 0
      ? "Rostros registrados: 0 (primero guarda un rostro en Registrar rostro)"
      : `Rostros registrados: ${n}`;
}

function renderDashboard() {
  document.querySelector("#metric-events").textContent = state.events.length;
  document.querySelector("#metric-incidents").textContent = state.incidents.length;
  document.querySelector("#metric-faces").textContent = state.faces.length;
  document.querySelector("#last-sync").textContent = `Actualizado ${new Date().toLocaleTimeString()}`;
}

function eventTypeLabel(eventType) {
  return eventType === "check_out" ? "Salida" : "Entrada";
}

function renderEvents() {
  const container = document.querySelector("#recent-events");
  if (!state.events.length) {
    container.className = "event-list empty";
    container.innerHTML = `
      <div class="empty-state">
        <span class="empty-icon">📭</span>
        <p>Sin eventos todavia</p>
        <small>Las marcas apareceran aqui al escanear o registrar manualmente</small>
      </div>`;
    return;
  }

  container.className = "event-list";
  container.innerHTML = state.events
    .slice()
    .reverse()
    .slice(0, 8)
    .map((event) => {
      const status = event.duplicate ? "Duplicado" : "Aceptado";
      const badge = event.duplicate ? "warn" : "ok";
      const typeClass = event.event_type === "check_out" ? "check-out" : "check-in";
      return `
        <article class="event-item">
          <div>
            <strong>${escapeHtml(event.employee_name || event.person_id)}</strong>
            <small>
              <span class="event-type ${typeClass}">${eventTypeLabel(event.event_type)}</span>
              · ${escapeHtml(event.device_id)} · ${formatDate(event.captured_at)}
            </small>
          </div>
          <span class="badge ${badge}">${status}</span>
        </article>
      `;
    })
    .join("");
}

function renderIncidents() {
  const container = document.querySelector("#incident-list");
  if (!state.incidents.length) {
    container.className = "event-list empty";
    container.innerHTML = `
      <div class="empty-state">
        <span class="empty-icon">✓</span>
        <p>Sin incidencias</p>
        <small>Todo en orden — no hay alertas pendientes</small>
      </div>`;
    return;
  }

  container.className = "event-list";
  container.innerHTML = state.incidents
    .slice()
    .reverse()
    .map((incident) => `
      <article class="event-item">
        <div>
          <strong>${escapeHtml(incident.employee_name || incident.person_id)}</strong>
          <small>${escapeHtml(incident.violation_type)} · ${formatDate(incident.created_at)}</small>
        </div>
        <span class="badge bad">${escapeHtml(incident.severity)}</span>
      </article>
    `)
    .join("");
}

async function submitAttendanceEvent(event) {
  event.preventDefault();
  const submitBtn = event.currentTarget.querySelector('[type="submit"]');
  const defaultLabel = submitBtn?.dataset.defaultLabel || submitBtn?.textContent || "Registrar";
  setButtonLoading(submitBtn, true, "Registrando...", defaultLabel);
  const form = new FormData(event.currentTarget);
  const payload = {
    person_id: form.get("person_id"),
    employee_name: form.get("employee_name"),
    device_id: form.get("device_id"),
    event_type: form.get("event_type"),
    confidence: 0.98,
    captured_at: new Date().toISOString(),
    source: "dashboard",
  };
  try {
    const data = await requestJson("/api/v1/attendance/events", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    showToast(data.message || "Evento registrado", 4000, "success");
    await refreshEvents();
  } catch (error) {
    showToast(parseApiError(error), 6000, "error");
  } finally {
    setButtonLoading(submitBtn, false, "", defaultLabel);
  }
}

async function submitExitAttempt(event) {
  event.preventDefault();
  const submitBtn = event.currentTarget.querySelector('[type="submit"]');
  const defaultLabel = submitBtn?.dataset.defaultLabel || submitBtn?.textContent || "Validar";
  setButtonLoading(submitBtn, true, "Validando...", defaultLabel);
  const form = new FormData(event.currentTarget);
  const payload = {
    person_id: form.get("person_id"),
    employee_name: form.get("employee_name"),
    attempted_at: new Date().toISOString(),
    scheduled_exit_time: form.get("scheduled_exit_time"),
    tolerance_minutes: Number(form.get("tolerance_minutes")),
    reason: form.get("reason"),
    source: "dashboard",
  };
  try {
    const data = await requestJson("/api/v1/attendance/exit-attempts", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    document.querySelector("#exit-result").textContent = JSON.stringify(data, null, 2);
    showToast(data.message || "Salida validada", 4000, "success");
    await refreshIncidents();
  } catch (error) {
    showToast(parseApiError(error), 6000, "error");
  } finally {
    setButtonLoading(submitBtn, false, "", defaultLabel);
  }
}

async function submitFaceRegister(event) {
  event.preventDefault();
  if (state.registerInProgress) {
    showToast("Registro en curso. Espera a que termine la IA.", 4000, "info");
    return;
  }

  const formEl = event.currentTarget;

  const validationError = validateRegisterForm(formEl);
  if (validationError) {
    setRegisterStatus("error", "Faltan datos", validationError);
    showToast(validationError, 5000, "error");
    registerStatus?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    return;
  }

  if (!document.querySelector("#api-status-dot")?.classList.contains("ok")) {
    const offlineMsg = "Backend sin conexion. Inicia uvicorn en el puerto 8000 y pulsa Actualizar.";
    setRegisterStatus("error", "Sin conexion", offlineMsg);
    showToast(offlineMsg, 6000, "error");
    return;
  }

  const form = new FormData(formEl);
  const personId = String(form.get("person_id") || "").trim();
  const submitBtn = faceRegisterSubmit || formEl.querySelector('[type="submit"]');
  const defaultLabel = submitBtn?.dataset.defaultLabel || submitBtn?.textContent || "Guardar perfil facial";

  state.registerInProgress = true;
  pauseBackgroundRefresh(true);
  setButtonLoading(submitBtn, true, "Guardando perfil...", defaultLabel);
  setRegisterFormDisabled(formEl, true);
  startRegisterProgressFeedback();
  setRegisterStatus(
    "loading",
    "Guardando perfil facial",
    "La IA puede tardar 1-3 minutos. No cierres la pagina ni pulses de nuevo el boton.",
  );
  registerStatus?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  showToast("Procesando fotos con IA. Espera por favor...", 5000, "info");

  try {
    const data = await requestForm("/api/v1/faces/register-profile", form, {
      silent: true,
      timeoutMs: 300_000,
    });
    await handleRegisterSuccess(data, formEl);
  } catch (error) {
    const recovered = await recoverRegisterIfSaved(personId);
    if (recovered) {
      await handleRegisterSuccess(
        {
          person_id: recovered.person_id,
          name: recovered.name,
          embedding_count: recovered.embedding_count,
          poses_saved: ["front", "left", "right"],
          storage_message: "Recuperado tras corte de red: el servidor si guardo el perfil.",
        },
        formEl,
        true,
      );
      return;
    }

    if (isTransientNetworkError(error)) {
      setRegisterStatus(
        "loading",
        "Reintentando conexion...",
        "La red se interrumpio. Reintentando una vez (no pulses de nuevo).",
      );
      await sleep(2500);
      try {
        const retryForm = new FormData(formEl);
        const data = await requestForm("/api/v1/faces/register-profile", retryForm, {
          silent: true,
          timeoutMs: 300_000,
        });
        await handleRegisterSuccess(data, formEl);
        return;
      } catch (retryError) {
        const recoveredAfterRetry = await recoverRegisterIfSaved(personId);
        if (recoveredAfterRetry) {
          await handleRegisterSuccess(
            {
              person_id: recoveredAfterRetry.person_id,
              name: recoveredAfterRetry.name,
              embedding_count: recoveredAfterRetry.embedding_count,
              poses_saved: ["front", "left", "right"],
              storage_message: "Recuperado tras reintento: el perfil ya estaba guardado.",
            },
            formEl,
            true,
          );
          return;
        }
        error = retryError;
      }
    }

    const message = parseApiError(error);
    if (registerResult) {
      registerResult.textContent = message;
    }
    setRegisterStatus(
      "error",
      "Conexion interrumpida",
      `${message} Si ves el JSON de exito abajo, el perfil puede estar guardado. Revisa Usuarios.`,
    );
    showToast(message, 8000, "error");
    registerStatus?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } finally {
    state.registerInProgress = false;
    pauseBackgroundRefresh(false);
    stopRegisterProgressFeedback();
    setButtonLoading(submitBtn, false, "", defaultLabel);
    setRegisterFormDisabled(formEl, false);
    window.setTimeout(() => refreshAll().catch(() => {}), 800);
  }
}

async function handleRegisterSuccess(data, formEl, recovered = false) {
  const poses = (data.poses_saved || []).join(", ");
  if (registerResult) {
    registerResult.textContent = JSON.stringify(data, null, 2);
  }
  const detail = recovered
    ? `${data.embedding_count} embeddings. La red fallo pero el servidor guardo el perfil.`
    : `${data.embedding_count} embeddings (${poses || "front, left, right"}). Ya puedes escanear.`;
  setRegisterStatus("success", `Perfil guardado: ${data.name}`, detail);
  showToast(
    recovered ? `Perfil recuperado: ${data.name}` : `Perfil guardado: ${data.name}`,
    5000,
    "success",
  );
  updateRegisterFilesSummary(formEl);
  await refreshFaces();
}

async function recoverRegisterIfSaved(personId) {
  if (!personId) return null;
  try {
    const data = await requestJson("/api/v1/faces/registered");
    const face = (data.faces || []).find((item) => item.person_id === personId);
    if (!face) return null;
    if ((face.embedding_count || 0) < 3) return null;
    return face;
  } catch {
    return null;
  }
}

function isTransientNetworkError(error) {
  const msg = String(error?.message || error || "").toLowerCase();
  return (
    msg.includes("failed to fetch")
    || msg.includes("network")
    || msg.includes("load failed")
    || msg.includes("aborted")
    || msg.includes("err_network")
  );
}

function validateRegisterForm(formEl) {
  const personId = String(new FormData(formEl).get("person_id") || "").trim();
  const name = String(new FormData(formEl).get("name") || "").trim();
  if (!personId) return "Ingresa el codigo del colaborador.";
  if (!name) return "Ingresa el nombre del colaborador.";

  const requiredFiles = [
    { name: "front", label: "frontal" },
    { name: "left", label: "giro izquierda" },
    { name: "right", label: "giro derecha" },
  ];
  const missing = requiredFiles.filter(({ name: fieldName }) => {
    const input = formEl.querySelector(`input[name="${fieldName}"]`);
    return !input?.files?.length;
  });
  if (missing.length) {
    return `Faltan fotos obligatorias: ${missing.map((item) => item.label).join(", ")}.`;
  }
  return null;
}

function handleRegisterFormChange(event) {
  const target = event.target;
  if (!(target instanceof HTMLInputElement) || target.type !== "file") return;

  const slot = target.closest(".pose-slot");
  const preview = slot?.querySelector(".pose-preview");
  const label = slot?.querySelector(".pose-file-label");

  if (target.files?.length) {
    slot?.classList.add("selected");
    const file = target.files[0];
    if (label) label.textContent = file.name;
    if (preview) {
      preview.innerHTML = `<img src="${URL.createObjectURL(file)}" alt="Vista previa" />`;
    }
  } else {
    slot?.classList.remove("selected");
    if (label) label.textContent = "Sin archivo";
    if (preview) preview.innerHTML = "";
  }

  if (faceRegisterForm) updateRegisterFilesSummary(faceRegisterForm);
}

function updateRegisterFilesSummary(formEl) {
  if (!registerFilesSummary) return;
  const required = ["front", "left", "right"];
  const optional = ["with_glasses", "without_glasses"];
  const labels = {
    front: "frontal",
    left: "izquierda",
    right: "derecha",
    with_glasses: "con lentes",
    without_glasses: "sin lentes",
  };

  const picked = [...required, ...optional].filter((field) => {
    const input = formEl.querySelector(`input[name="${field}"]`);
    return input?.files?.length;
  });

  const missingRequired = required.filter((field) => {
    const input = formEl.querySelector(`input[name="${field}"]`);
    return !input?.files?.length;
  });

  if (missingRequired.length) {
    registerFilesSummary.className = "register-files-summary warn";
    registerFilesSummary.textContent = `Faltan obligatorias: ${missingRequired.map((f) => labels[f]).join(", ")}.`;
    return;
  }

  registerFilesSummary.className = "register-files-summary ok";
  registerFilesSummary.textContent = `Listo: ${picked.map((f) => labels[f]).join(", ")} (${picked.length} foto(s)).`;
}

function setRegisterStatus(mode, title, detail) {
  if (!registerStatus) return;
  registerStatus.classList.remove("idle", "loading", "success", "error");
  registerStatus.classList.add(mode);
  const icons = { idle: "○", loading: "◌", success: "✓", error: "✕" };
  const icon = registerStatus.querySelector(".register-status-icon");
  if (icon) icon.textContent = icons[mode] || "○";
  if (registerStatusTitle) registerStatusTitle.textContent = title;
  if (registerStatusDetail) registerStatusDetail.textContent = detail;
}

function startRegisterProgressFeedback() {
  stopRegisterProgressFeedback();
  registerProgress?.classList.remove("hidden");
  if (registerProgressBar) registerProgressBar.style.width = "8%";

  const messages = [
    "Subiendo fotos al servidor...",
    "Detectando rostro frontal...",
    "Generando embedding frontal...",
    "Procesando giro izquierda...",
    "Procesando giro derecha...",
    "Guardando en base de datos...",
  ];
  let step = 0;
  const startedAt = Date.now();

  state.registerProgressTimer = window.setInterval(() => {
    step = Math.min(step + 1, messages.length - 1);
    const pct = Math.min(92, 8 + step * 14);
    if (registerProgressBar) registerProgressBar.style.width = `${pct}%`;
    if (registerStatusDetail) {
      const secs = Math.floor((Date.now() - startedAt) / 1000);
      registerStatusDetail.textContent = `${messages[step]} (${secs}s)`;
    }
  }, 7000);

  state.registerElapsedTimer = window.setInterval(() => {
    if (!registerStatusDetail || !registerStatus?.classList.contains("loading")) return;
    const secs = Math.floor((Date.now() - startedAt) / 1000);
    const current = registerStatusDetail.textContent.replace(/\(\d+s\)$/, "").trim();
    registerStatusDetail.textContent = `${current} (${secs}s)`;
  }, 1000);
}

function stopRegisterProgressFeedback() {
  if (state.registerProgressTimer) {
    window.clearInterval(state.registerProgressTimer);
    state.registerProgressTimer = null;
  }
  if (state.registerElapsedTimer) {
    window.clearInterval(state.registerElapsedTimer);
    state.registerElapsedTimer = null;
  }
  if (registerProgressBar) registerProgressBar.style.width = "100%";
  window.setTimeout(() => registerProgress?.classList.add("hidden"), 400);
}

function setRegisterFormDisabled(formEl, disabled) {
  formEl.querySelectorAll("input, button, select, textarea").forEach((el) => {
    el.disabled = disabled;
  });
}

function setButtonLoading(button, loading, loadingText = "Procesando...", defaultText = "") {
  if (!button) return;
  if (!button.dataset.defaultLabel) {
    button.dataset.defaultLabel = defaultText || button.textContent.trim();
  }
  button.classList.toggle("loading", loading);
  button.disabled = loading;
  button.textContent = loading ? loadingText : button.dataset.defaultLabel;
}

function parseApiError(error) {
  const raw = String(error?.message || error || "Error desconocido");
  try {
    const parsed = JSON.parse(raw);
    if (parsed.detail) {
      if (typeof parsed.detail === "string") return parsed.detail;
      if (Array.isArray(parsed.detail)) {
        return parsed.detail.map((item) => item.msg || JSON.stringify(item)).join(". ");
      }
    }
  } catch {
    // texto plano del servidor
  }
  if (raw.includes("Failed to fetch") || raw.includes("NetworkError") || raw.includes("ERR_NETWORK")) {
    return (
      "La conexion se corto mientras la IA procesaba las fotos (ERR_NETWORK_CHANGED). " +
      "Espera 10 segundos y revisa el menu Usuarios: el perfil puede haberse guardado igual. " +
      "Evita pulsar el boton varias veces. Si usas uvicorn --reload, prueba sin --reload."
    );
  }
  return raw.length > 240 ? `${raw.slice(0, 240)}...` : raw;
}

const LIVENESS_STEP_LABELS = {
  front: "Mirar",
  movement: "Girar",
  blink: "Parpadeo",
  smile: "Sonrisa",
  validate: "Validar",
};

function formatLivenessChecks(checks) {
  if (!checks || typeof checks !== "object") return "";
  const labels = {
    movement: "giro",
    blink: "parpadeo",
    same_person: "misma persona",
    anti_spoof: "anti-spoof",
    texture: "textura",
    eyes_open_front: "ojos abiertos",
    smile: "sonrisa",
  };
  const failed = Object.entries(checks)
    .filter(([, ok]) => ok === false)
    .map(([key]) => labels[key] || key);
  return failed.length ? `fallo: ${failed.join(", ")}` : "";
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function renderLivenessSteps(steps) {
  if (!livenessStepsEl) return;
  const labels = steps.map((s) => LIVENESS_STEP_LABELS[s.type] || s.type);
  livenessStepsEl.innerHTML = labels
    .map(
      (label, index) =>
        `<span class="liveness-step" data-step="${index + 1}">${index + 1}. ${label}</span>`,
    )
    .concat(
      `<span class="liveness-step" data-step="${labels.length + 1}">${labels.length + 1}. Validar</span>`,
    )
    .join("");
}

function setLivenessStepActive(stepNumber) {
  if (!livenessStepsEl) return;
  livenessStepsEl.classList.remove("hidden");
  livenessStepsEl.querySelectorAll(".liveness-step").forEach((el) => {
    const n = Number(el.dataset.step);
    el.classList.toggle("active", n === stepNumber);
    el.classList.toggle("done", n < stepNumber);
  });
}

function hideLivenessSteps() {
  livenessStepsEl?.classList.add("hidden");
  livenessStepsEl?.querySelectorAll(".liveness-step").forEach((el) => {
    el.classList.remove("active", "done");
  });
}

const LIVENESS_STEP_TIMING = {
  front: { prepMs: 1200, countdownSec: 2, actionCue: null, burst: false },
  movement: { prepMs: 1500, countdownSec: 2, actionCue: "Gira la cabeza ahora", burst: false },
  blink: { prepMs: 1400, countdownSec: 2, actionCue: "Parpadea ahora", burst: true },
  smile: { prepMs: 1400, countdownSec: 2, actionCue: "Sonrie ahora", burst: true },
};
const LIVENESS_ACTION_HOLD_MS = 400;
const LIVENESS_BURST_INTERVAL_MS = 180;
const CAMERA_FRAME_QUALITY = 0.9;

function setLivenessOverlayText(text) {
  if (scanOverlay) scanOverlay.textContent = text;
  setCameraStatus(text);
}

async function countdownWithActionCue(seconds, actionCue) {
  for (let remaining = seconds; remaining >= 1; remaining -= 1) {
    const isActionSecond = actionCue && remaining === 1;
    const label = isActionSecond ? actionCue : `Captura en ${remaining}...`;
    setLivenessOverlayText(label);
    if (isActionSecond) {
      speak(actionCue);
    }
    await sleep(1000);
  }
}

async function captureLivenessStep(step) {
  const timing = LIVENESS_STEP_TIMING[step.type] || LIVENESS_STEP_TIMING.front;
  setScanResult("scanning", step.prompt, "Preparate, la captura es automatica...");
  setLivenessOverlayText(step.prompt);
  speak(step.prompt);
  await sleep(timing.prepMs);

  await countdownWithActionCue(timing.countdownSec, timing.actionCue);
  if (timing.actionCue) {
    await sleep(LIVENESS_ACTION_HOLD_MS);
  }
  setLivenessOverlayText("Capturando...");
  if (timing.burst) {
    return captureCameraBurst(2, LIVENESS_BURST_INTERVAL_MS);
  }
  await sleep(250);
  return captureCameraFrame();
}

async function captureCameraBurst(count = 2, intervalMs = 180) {
  let lastBlob = null;
  for (let index = 0; index < count; index += 1) {
    const blob = await captureCameraFrame();
    if (blob) lastBlob = blob;
    if (index < count - 1) await sleep(intervalMs);
  }
  return lastBlob;
}

async function runLivenessChallenge() {
  const challenge = await requestJson("/api/v1/faces/liveness/challenge");
  renderLivenessSteps(challenge.steps || []);
  const form = new FormData();
  form.append("challenge_id", challenge.challenge_id || "");
  showLivenessCaptureOverlay();

  for (let index = 0; index < challenge.steps.length; index += 1) {
    const step = challenge.steps[index];
    setLivenessStepActive(index + 1);
    const blob = await captureLivenessStep(step);
    if (!blob) {
      throw new Error("La camara no capturo imagen. Espera un momento e intenta de nuevo.");
    }
    form.append(step.form_field, blob, `${step.form_field}.jpg`);
    await sleep(250);
  }

  showScanOverlay();
  setLivenessStepActive((challenge.steps?.length || 3) + 1);
  setScanResult("scanning", "Validando rostro real...", "Anti-spoofing avanzado en curso");
  if (scanOverlay) scanOverlay.textContent = "Validando rostro real...";
  speak("Validando rostro real.");
  return requestForm("/api/v1/faces/liveness/verify", form, {
    silent: true,
    timeoutMs: 300_000,
  });
}

async function startCamera() {
  if (state.camera.stream) return;
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: "user",
        width: { ideal: 1280, min: 640 },
        height: { ideal: 720, min: 480 },
      },
      audio: false,
    });
    state.camera.stream = stream;
    cameraPreview.srcObject = stream;
    await waitForCameraReady();
    await sleep(800);
    startCameraBtn.disabled = true;
    stopCameraBtn.disabled = false;
    scanCameraBtn.disabled = false;
    scanCheckInBtn.disabled = false;
    scanCheckOutBtn.disabled = false;
    await refreshFaces();
    updateScanModeUi();
    setScanResult("idle", "Camara lista", "Elige Entrada o Salida y pulsa el boton correspondiente.");
    setCameraStatus("Camara activa. Selecciona el tipo de marca antes de escanear.");
    await refreshAttendancePolicy();
    speak(`${getWelcomeSpeech()} Elige entrada o salida y escanea para marcar asistencia.`);
    if (autoScanInput?.checked) {
      startAutoScan();
    }
  } catch (error) {
    setCameraStatus("No se pudo abrir la camara. Revisa permisos.");
    showToast("Error al iniciar camara");
  }
}

function stopCamera() {
  stopAutoScan();
  if (!state.camera.stream) return;
  state.camera.stream.getTracks().forEach((track) => track.stop());
  state.camera.stream = null;
  cameraPreview.srcObject = null;
  startCameraBtn.disabled = false;
  stopCameraBtn.disabled = true;
  scanCameraBtn.disabled = true;
  scanCheckInBtn.disabled = true;
  scanCheckOutBtn.disabled = true;
  setCameraStatus("Camara apagada");
  setScanResult("idle", "Listo para escanear", "Inicia la camara para comenzar");
  hideScanOverlay();
}

function waitForCameraReady() {
  return new Promise((resolve) => {
    if (cameraPreview.readyState >= 2 && cameraPreview.videoWidth > 0) {
      resolve();
      return;
    }
    const onReady = () => {
      cameraPreview.removeEventListener("loadeddata", onReady);
      resolve();
    };
    cameraPreview.addEventListener("loadeddata", onReady);
    window.setTimeout(resolve, 3000);
  });
}

function setScanEventType(eventType) {
  state.camera.selectedEventType = eventType;
  updateScanModeUi();
}

function updateScanModeUi() {
  const isCheckIn = state.camera.selectedEventType === "check_in";
  scanModeCheckInBtn?.classList.toggle("active", isCheckIn);
  scanModeCheckOutBtn?.classList.toggle("active", !isCheckIn);
  if (scanModeLabel) {
    scanModeLabel.textContent = isCheckIn
      ? "Modo seleccionado: Entrada"
      : "Modo seleccionado: Salida";
  }
  setCameraNextAction(
    isCheckIn
      ? "Listo para marcar ENTRADA"
      : "Listo para marcar SALIDA",
  );
}

function scanWithEventType(eventType) {
  setScanEventType(eventType);
  return scanFromCamera(eventType);
}

async function scanFromCamera(forcedEventType = null) {
  if (!state.camera.stream) {
    showToast("Primero inicia la camara", 4000);
    setScanResult("warn", "Camara apagada", "Pulsa 1. Iniciar camara");
    return;
  }
  if (state.faces.length === 0) {
    setScanResult("warn", "Sin rostros registrados", "Guarda un rostro en Registrar rostro primero");
    showToast("Primero registra tu rostro", 4000);
    return;
  }
  if (state.camera.scanning) return;
  state.camera.scanning = true;
  pauseBackgroundRefresh(true);
  showScanOverlay();
  setScanResult("scanning", "Escaneando...", "Analizando tu rostro, espera unos segundos");
  setCameraStatus(`Escaneando... ${new Date().toLocaleTimeString()}`);

  try {
    let identifyData = null;

    if (livenessEnabledInput?.checked) {
      const liveness = await runLivenessChallenge();
      const faceResult = document.querySelector("#face-result");
      if (faceResult) {
        faceResult.textContent = JSON.stringify({ liveness }, null, 2);
      }
      if (!liveness.passed) {
        const checksDetail = formatLivenessChecks(liveness.checks);
        const detail = checksDetail
          ? `${liveness.message || "Repite el desafio."} (${checksDetail})`
          : (liveness.message || "Repite el desafio de vida");
        setScanResult("bad", "Rostro no validado", detail);
        setCameraStatus(liveness.message || "Liveness fallido");
        showToast(liveness.message || "No se valido rostro vivo", 6000, "error");
        speak(liveness.message || "Repite el desafio.");
        return;
      }
      if (liveness.candidate?.person_id) {
        identifyData = {
          matched: true,
          candidate: liveness.candidate,
        };
      } else {
        setScanResult("scanning", "Rostro validado", "Identificando persona...");
        if (scanOverlay) scanOverlay.textContent = "Identificando...";
      }
    }

    if (!identifyData?.matched) {
      const blob = await captureCameraFrame();
      if (!blob) {
        setScanResult("warn", "Camara no lista", "Espera 2 segundos y vuelve a intentar");
        showToast("La camara aun no captura imagen", 4000);
        return;
      }
      const form = new FormData();
      form.append("file", blob, "camera-scan.jpg");
      identifyData = await requestForm("/api/v1/faces/identify", form);
    }

    const faceResult = document.querySelector("#face-result");
    if (faceResult && identifyData) {
      faceResult.textContent = JSON.stringify(identifyData, null, 2);
    }
    const data = identifyData;
    if (data.matched) {
      const personName = data.candidate?.name || data.candidate?.person_id || "colaborador";
      const conf = Math.round((data.candidate?.confidence || 0) * 100);
      setScanResult("ok", `Verificado: ${personName}`, `Coincidencia ${conf}%`);
      setCameraStatus(`Verificado: ${personName} (${conf}%)`);
      showToast(`Verificado: ${personName}`, 4000);
      const eventType = forcedEventType || state.camera.selectedEventType || "check_in";
      await registerAttendanceAfterScan(data, personName, eventType);
    } else {
      const near = data.near_miss;
      if (near?.name || near?.person_id) {
        const conf = Math.round((near.confidence || 0) * 100);
        const label = near.name || near.person_id;
        setScanResult(
          "warn",
          "No reconocido",
          `Mas parecido: ${label} (${conf}%). Acercate, mira de frente y mejora la luz`
        );
        setCameraStatus(`Casi: ${label} (${conf}%) - intenta de nuevo`);
        showToast(`Casi te reconoci como ${label} (${conf}%)`, 5000);
      } else {
        setScanResult("bad", "No reconocido", "Registra mas fotos o mejora la luz");
        setCameraStatus("Sin coincidencia - intenta de nuevo");
        showToast("No te reconoci. Registra otra foto o acercate mas.", 4000);
      }
      speak("No hay coincidencia. Intenta de nuevo.");
    }
  } catch (error) {
    setScanResult("bad", "Error al escanear", "Revisa que el backend este activo");
    setCameraStatus("Error al escanear");
    showToast("Error al escanear. Mira consola o backend.", 5000);
  } finally {
    state.camera.scanning = false;
    pauseBackgroundRefresh(false);
    hideScanOverlay();
    hideLivenessSteps();
    if (scanOverlay) scanOverlay.textContent = "Analizando rostro...";
  }
}

async function registerAttendanceAfterScan(identifyData, personName, eventType) {
  const personId = identifyData.candidate?.person_id;
  if (!personId) return;

  const eventLabel = eventType === "check_out" ? "salida" : "entrada";
  const now = Date.now();
  const last = state.camera.lastAttendanceByPerson[personId] || 0;
  if (now - last < state.camera.attendanceCooldownMs) {
    const secs = Math.ceil((state.camera.attendanceCooldownMs - (now - last)) / 1000);
    setScanResult("ok", `Ya verificado: ${personName}`, `Espera ${secs}s para volver a marcar`);
    setCameraStatus(`Verificado. Espera ${secs}s antes de otra marca.`);
    return;
  }

  const payload = {
    person_id: personId,
    employee_name: identifyData.candidate?.name || personId,
    device_id: "dashboard-camera-001",
    event_type: eventType,
    confidence: Number(identifyData.candidate?.confidence || 0.98),
    captured_at: new Date().toISOString(),
    source: "dashboard-camera",
  };

  try {
    const response = await requestJson("/api/v1/attendance/events", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.camera.lastAttendanceByPerson[personId] = now;

    if (response.event?.duplicate) {
      const duplicateMessage =
        response.message ||
        (eventType === "check_out"
          ? `${personName}: ya registraste salida hoy.`
          : `${personName}: ya registraste entrada hoy. Si saliste, cambia a Salida.`);
      setScanResult("warn", `${personName}: ya registrado`, duplicateMessage);
      setCameraStatus(duplicateMessage);
      showToast(duplicateMessage, 6000, "info");
      speak(duplicateMessage);
      if (eventType === "check_in") {
        setScanEventType("check_out");
      }
      return;
    }

    prependAttendanceEvent(response.event);
    renderDashboard();
    const successMessage =
      response.message ||
      (eventType === "check_out"
        ? "Salida registrada correctamente."
        : "Entrada registrada correctamente.");

    setScanResult("ok", `Asistencia guardada (${eventLabel})`, successMessage);
    setCameraStatus(successMessage);
    showToast(successMessage, 5000);
    speak(
      `Escaneo completado. Verificado ${personName}. Marcado de asistencia de ${eventLabel}.`,
    );
    updateScanModeUi();
  } catch (error) {
    const detail = parseApiError(error);
    setScanResult(
      "warn",
      `Verificado: ${personName}`,
      `Rostro reconocido, pero no se guardo la asistencia. ${detail}`,
    );
    setCameraStatus("Verificado. Error al guardar asistencia.");
    showToast(`No se guardo asistencia: ${detail}`, 7000, "error");
    speak("Verificado, pero no se pudo guardar asistencia.");
  }
}

function prependAttendanceEvent(event) {
  if (!event?.event_id) return;
  state.events = [event, ...state.events.filter((item) => item.event_id !== event.event_id)].slice(0, 50);
  renderEvents();
}

async function captureCameraFrame() {
  if (!cameraPreview.videoWidth || !cameraPreview.videoHeight) {
    return null;
  }
  const maxWidth = 960;
  const scale = Math.min(1, maxWidth / cameraPreview.videoWidth);
  cameraCanvas.width = Math.round(cameraPreview.videoWidth * scale);
  cameraCanvas.height = Math.round(cameraPreview.videoHeight * scale);
  const ctx = cameraCanvas.getContext("2d");
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(cameraPreview, 0, 0, cameraCanvas.width, cameraCanvas.height);

  return new Promise((resolve) => {
    cameraCanvas.toBlob(
      (blob) => resolve(blob),
      "image/jpeg",
      CAMERA_FRAME_QUALITY,
    );
  });
}

function toggleAutoScan() {
  if (!state.camera.stream) return;
  if (autoScanInput.checked) {
    startAutoScan();
  } else {
    stopAutoScan();
    setCameraStatus("Camara activa. Escaneo continuo desactivado.");
  }
}

function startAutoScan() {
  stopAutoScan();
  const intervalMs = livenessEnabledInput?.checked ? 12_000 : 5_000;
  state.camera.scanTimer = window.setInterval(() => {
    if (state.camera.scanning) return;
    scanFromCamera().catch(() => {});
  }, intervalMs);
  const modeLabel = state.camera.selectedEventType === "check_out" ? "salida" : "entrada";
  setCameraStatus(`Escaneo automatico cada ${intervalMs / 1000}s (modo: ${modeLabel})`);
}

function stopAutoScan() {
  if (state.camera.scanTimer) {
    window.clearInterval(state.camera.scanTimer);
    state.camera.scanTimer = null;
  }
}

async function requestJson(path, options = {}) {
  const { timeoutMs = 30_000, ...fetchOptions } = options;
  const response = await fetchWithTimeout(`${apiBase()}${path}`, {
    headers: { "Content-Type": "application/json", ...(fetchOptions.headers || {}) },
    ...fetchOptions,
  }, timeoutMs);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

async function requestForm(path, form, options = {}) {
  const { silent = false, timeoutMs = 120_000 } = options;
  let response;
  try {
    response = await fetchWithTimeout(`${apiBase()}${path}`, {
      method: "POST",
      body: form,
    }, timeoutMs);
  } catch (error) {
    if (!silent) showToast(parseApiError(error), 6000, "error");
    throw error;
  }
  if (!response.ok) {
    const message = await response.text();
    if (!silent) showToast(parseApiError(new Error(message)), 6000, "error");
    throw new Error(message);
  }
  return response.json();
}

async function fetchWithTimeout(url, options, timeoutMs) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } catch (error) {
    if (error?.name === "AbortError") {
      throw new Error(
        `Tiempo de espera agotado (${Math.round(timeoutMs / 1000)}s). El servidor puede seguir procesando; revisa Usuarios.`,
      );
    }
    throw error;
  } finally {
    window.clearTimeout(timer);
  }
}

function setApiStatus(ok) {
  const dot = document.querySelector("#api-status-dot");
  const label = document.querySelector("#api-status-label");
  dot.classList.toggle("ok", ok);
  dot.classList.toggle("bad", !ok);
  label.textContent = ok ? "Conectado" : "Sin conexion";
}

function showToast(message, durationMs = 3200, tone = "info") {
  if (!toast) return;
  toast.textContent = message;
  toast.classList.remove("show", "success", "error", "info");
  toast.classList.add("show", tone);
  window.clearTimeout(state.toastTimer);
  state.toastTimer = window.setTimeout(() => {
    toast.classList.remove("show", "success", "error", "info");
  }, durationMs);
}

function setScanResult(mode, title, detail) {
  if (!scanResultCard) return;
  scanResultCard.className = `scan-result-card ${mode}`;
  const icons = { idle: "○", scanning: "◌", ok: "✓", bad: "✕", warn: "!" };
  if (scanResultIcon) scanResultIcon.textContent = icons[mode] || "○";
  if (scanResultTitle) scanResultTitle.textContent = title;
  if (scanResultDetail) scanResultDetail.textContent = detail;
}

function showScanOverlay() {
  scanOverlay?.classList.remove("hidden");
  scanPreviewWrap?.classList.remove("liveness-capture");
  scanPreviewWrap?.classList.add("scanning");
}

function showLivenessCaptureOverlay() {
  scanOverlay?.classList.remove("hidden");
  scanPreviewWrap?.classList.add("scanning", "liveness-capture");
}

function hideScanOverlay() {
  scanOverlay?.classList.add("hidden");
  scanPreviewWrap?.classList.remove("scanning", "liveness-capture");
}

function setCameraStatus(message) {
  if (cameraStatus) {
    cameraStatus.textContent = message;
  }
}

function setCameraNextAction(message) {
  if (cameraNextAction) {
    cameraNextAction.textContent = message;
  }
}

function getWelcomeSpeech() {
  const hour = new Date().getHours();
  if (hour < 12) return "Buenos dias.";
  if (hour < 19) return "Buenas tardes.";
  return "Buenas noches.";
}

function speak(message) {
  if (!state.camera.speakingEnabled || !("speechSynthesis" in window)) return;
  if (!message) return;

  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(message);
  utterance.lang = "es-PE";
  utterance.rate = 1;
  utterance.pitch = 1;
  window.speechSynthesis.speak(utterance);
}

function formatDate(value) {
  if (!value) return "Sin fecha";
  return new Date(value).toLocaleString();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

