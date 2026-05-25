const state = {
  events: [],
  incidents: [],
  faces: [],
};

const apiBaseInput = document.querySelector("#api-base");
const toast = document.querySelector("#toast");

document.querySelector("#today-label").textContent = new Intl.DateTimeFormat("es-PE", {
  weekday: "long",
  year: "numeric",
  month: "long",
  day: "numeric",
}).format(new Date());

document.querySelectorAll(".nav-item").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
    button.classList.add("active");
    document.querySelector(`#view-${button.dataset.view}`).classList.add("active");
  });
});

document.querySelector("#refresh-btn").addEventListener("click", refreshAll);
document.querySelector("#reload-incidents").addEventListener("click", refreshIncidents);
document.querySelector("#event-form").addEventListener("submit", submitAttendanceEvent);
document.querySelector("#exit-form").addEventListener("submit", submitExitAttempt);
document.querySelector("#face-register-form").addEventListener("submit", submitFaceRegister);
document.querySelector("#face-identify-form").addEventListener("submit", submitFaceIdentify);

refreshAll();
setInterval(refreshAll, 15000);

function apiBase() {
  return apiBaseInput.value.replace(/\/$/, "");
}

async function refreshAll() {
  await Promise.allSettled([
    refreshHealth(),
    refreshEvents(),
    refreshIncidents(),
    refreshFaces(),
  ]);
  renderDashboard();
}

async function refreshHealth() {
  try {
    await requestJson("/api/v1/health");
    setApiStatus(true);
  } catch (error) {
    setApiStatus(false);
  }
}

async function refreshEvents() {
  const data = await requestJson("/api/v1/attendance/events");
  state.events = data.events || [];
  renderEvents();
}

async function refreshIncidents() {
  const data = await requestJson("/api/v1/attendance/incidents");
  state.incidents = data.incidents || [];
  renderIncidents();
  renderDashboard();
}

async function refreshFaces() {
  const data = await requestJson("/api/v1/faces/registered");
  state.faces = data.faces || [];
  renderDashboard();
}

function renderDashboard() {
  document.querySelector("#metric-events").textContent = state.events.length;
  document.querySelector("#metric-incidents").textContent = state.incidents.length;
  document.querySelector("#metric-faces").textContent = state.faces.length;
  document.querySelector("#last-sync").textContent = `Actualizado ${new Date().toLocaleTimeString()}`;
}

function renderEvents() {
  const container = document.querySelector("#recent-events");
  if (!state.events.length) {
    container.className = "event-list empty";
    container.textContent = "Sin eventos";
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
      return `
        <article class="event-item">
          <div>
            <strong>${escapeHtml(event.employee_name || event.person_id)}</strong>
            <small>${escapeHtml(event.event_type)} · ${escapeHtml(event.device_id)} · ${formatDate(event.captured_at)}</small>
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
    container.textContent = "Sin incidencias";
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
  const data = await requestJson("/api/v1/attendance/events", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  showToast(data.message || "Evento registrado");
  await refreshEvents();
}

async function submitExitAttempt(event) {
  event.preventDefault();
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
  const data = await requestJson("/api/v1/attendance/exit-attempts", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  document.querySelector("#exit-result").textContent = JSON.stringify(data, null, 2);
  showToast(data.message || "Salida validada");
  await refreshIncidents();
}

async function submitFaceRegister(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const data = await requestForm("/api/v1/faces/register", form);
  showToast(`Rostro guardado: ${data.name}`);
  await refreshFaces();
}

async function submitFaceIdentify(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const data = await requestForm("/api/v1/faces/identify", form);
  document.querySelector("#face-result").textContent = JSON.stringify(data, null, 2);
  showToast(data.matched ? "Rostro identificado" : "Sin coincidencia");
}

async function requestJson(path, options = {}) {
  const response = await fetch(`${apiBase()}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

async function requestForm(path, form) {
  const response = await fetch(`${apiBase()}${path}`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    const message = await response.text();
    showToast("Error al procesar imagen");
    throw new Error(message);
  }
  return response.json();
}

function setApiStatus(ok) {
  const dot = document.querySelector("#api-status-dot");
  const label = document.querySelector("#api-status-label");
  dot.classList.toggle("ok", ok);
  dot.classList.toggle("bad", !ok);
  label.textContent = ok ? "Conectado" : "Sin conexion";
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), 2600);
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

