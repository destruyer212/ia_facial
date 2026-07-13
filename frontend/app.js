const state = {
  events: [],
  incidents: [],
  faces: [],
  facesFingerprint: "",
  camera: {
    stream: null,
    meshOverlay: null,
    scanTimer: null,
    scanning: false,
    speakingEnabled: true,
    speechReady: false,
    preferredVoice: null,
    speechQueue: [],
    speechBusy: false,
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
    late: 0,
    early_exits: 0,
  },
  registerProgressTimer: null,
  registerElapsedTimer: null,
  toastTimer: null,
  registerInProgress: false,
  registerScanner: null,
  registerScanComplete: false,
  registerScanStarting: false,
  registerExpectedCode: "",
  registerCaptureBlobs: null,
  lastRegisteredPersonId: null,
  employeeCatalog: null,
  schedule: null,
  scheduleFingerprint: "",
  preRegistrations: [],
  preRegistrationsFingerprint: "",
  admin: null,
  adminFingerprint: "",
  backgroundRefreshPaused: false,
  refreshTimer: null,
  lastSyncAt: null,
};

const DEFAULT_API_BASE = "http://104.238.215.26";
const API_BASE_STORAGE_KEY = "ia_facial_api_base";
const apiBaseInput = document.querySelector("#api-base");
const apiSettingsForm = document.querySelector("#api-settings-form");

function loadStoredApiBase() {
  try {
    return localStorage.getItem(API_BASE_STORAGE_KEY);
  } catch {
    return null;
  }
}

function saveStoredApiBase(url) {
  try {
    localStorage.setItem(API_BASE_STORAGE_KEY, url);
  } catch {
    // ignore storage errors
  }
}

function initApiBaseDefault() {
  if (!apiBaseInput) return;
  const stored = loadStoredApiBase();
  if (stored) {
    apiBaseInput.value = stored;
    return;
  }
  const current = apiBaseInput.value.trim();
  if (
    !current ||
    current === "http://127.0.0.1:8000" ||
    current === "http://localhost:8000" ||
    current.includes("onrender.com")
  ) {
    apiBaseInput.value = DEFAULT_API_BASE;
  }
}

function syncSettingsApiStatus() {
  const sidebarDot = document.querySelector("#api-status-dot");
  const sidebarLabel = document.querySelector("#api-status-label");
  const settingsDot = document.querySelector("#settings-api-status-dot");
  const settingsLabel = document.querySelector("#settings-api-status-label");
  if (!sidebarDot || !settingsDot) return;

  settingsDot.className = sidebarDot.className;
  if (settingsLabel && sidebarLabel) {
    settingsLabel.textContent = sidebarLabel.textContent;
  }
}
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
const registerStartScanBtn = document.querySelector("#register-start-scan-btn");
const registerCameraPreview = document.querySelector("#register-camera-preview");
const registerCameraMesh = document.querySelector("#register-camera-mesh");
const registerFaceCircle = document.querySelector("#register-face-circle");
const registerScanStep = document.querySelector("#register-scan-step");
const registerScanHint = document.querySelector("#register-scan-hint");
const registerScanProgress = document.querySelector("#register-scan-progress");
const registerAreaSelect = document.querySelector("#register-area-code");
const registerPositionSelect = document.querySelector("#register-position-code");
const registerEmployeeCodeInput = document.querySelector("#register-employee-code");
const cameraPreview = document.querySelector("#face-camera-preview");
const scanCameraMesh = document.querySelector("#scan-camera-mesh");
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
const voiceAssistantInput = document.querySelector("#voice-assistant-enabled");
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
const userEditShiftSelect = document.querySelector("#user-edit-shift-code");
const showInactiveUsersInput = document.querySelector("#show-inactive-users");
const userPhotoInput = document.querySelector("#user-photo-input");
const eventEditDialog = document.querySelector("#event-edit-dialog");
const eventEditForm = document.querySelector("#event-edit-form");
const organizationForm = document.querySelector("#organization-form");
const areaForm = document.querySelector("#area-form");
const positionForm = document.querySelector("#position-form");
const deviceForm = document.querySelector("#device-form");
const settingsForm = document.querySelector("#system-settings-form");
const adminAreaSelect = document.querySelector("#admin-position-area");
const registerShiftSelect = document.querySelector("#register-shift-code");
const shiftAssignmentForm = document.querySelector("#shift-assignment-form");
const shiftEmployeeSelect = document.querySelector("#shift-employee-select");
const shiftCodeSelect = document.querySelector("#shift-code-select");
const preRegisterForm = document.querySelector("#pre-register-form");
const preRegisterAreaSelect = document.querySelector("#pre-register-area-code");
const preRegisterPositionSelect = document.querySelector("#pre-register-position-code");
const preRegisterShiftSelect = document.querySelector("#pre-register-shift-code");
const shiftRosterSearch = document.querySelector("#shift-roster-search");
const mobileMenuToggle = document.querySelector("#mobile-menu-toggle");
const mobileMenuBackdrop = document.querySelector("#mobile-menu-backdrop");

document.querySelector("#today-label").textContent = new Intl.DateTimeFormat("es-PE", {
  weekday: "long",
  year: "numeric",
  month: "long",
  day: "numeric",
}).format(new Date());

const viewTitles = {
  overview: "Panel ejecutivo",
  attendance: "Centro de marcacion facial",
  register: "Registrar rostro",
  scan: "Escanear y marcar asistencia",
  users: "Colaboradores registrados",
  reports: "Reporte de entradas y salidas",
  incidents: "Incidencias de salida",
  organization: "Datos de empresa",
  areas: "Areas y cargos",
  schedules: "Horarios y turnos",
  preregistration: "Tokens de registro",
  devices: "Dispositivos",
  settings: "Configuracion del sistema",
};

const viewSubtitles = {
  overview: "Resumen operativo de asistencia, personas y dispositivos",
  attendance: "Marcacion biometrica por camara, movil y dispositivos edge",
  register: "Escaneo facial en vivo con malla 3D y validacion automatica",
  scan: "Reconocimiento facial en vivo con anti-spoofing",
  users: "Colaboradores con perfil facial activo",
  reports: "Consulta, filtra y corrige marcas de asistencia",
  incidents: "Salidas anticipadas y violaciones de politica",
  organization: "Perfil corporativo, sedes y datos legales",
  areas: "Mapa organizacional usado para codigos de empleados",
  schedules: "Turnos TM/TT, asignacion y reglas de tardanza",
  preregistration: "Pre-registro masivo para app movil con token seguro",
  devices: "Camaras, kioskos y PCs autorizadas para marcar asistencia",
  settings: "Parametros operativos del reconocimiento facial",
};

function setViewHeader(viewKey) {
  const title = document.querySelector(".topbar h1");
  const subtitle = document.querySelector("#view-subtitle");
  if (title) title.textContent = viewTitles[viewKey] || "IA Facial";
  if (subtitle) subtitle.textContent = viewSubtitles[viewKey] || "";
}

function openDashboardView(viewKey) {
  const button = document.querySelector(`.nav-item[data-view="${viewKey}"]`);
  if (button) {
    button.click();
    return;
  }
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
  document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
  document.querySelector(`#view-${viewKey}`)?.classList.add("active");
  setViewHeader(viewKey);
}

function setMobileMenuOpen(isOpen) {
  document.body.classList.toggle("mobile-menu-open", isOpen);
  mobileMenuToggle?.setAttribute("aria-expanded", String(isOpen));
  if (mobileMenuBackdrop) mobileMenuBackdrop.hidden = !isOpen;
}

function closeMobileMenu() {
  setMobileMenuOpen(false);
}

mobileMenuToggle?.addEventListener("click", () => {
  setMobileMenuOpen(!document.body.classList.contains("mobile-menu-open"));
});
mobileMenuBackdrop?.addEventListener("click", closeMobileMenu);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeMobileMenu();
});
window.addEventListener("resize", () => {
  if (window.innerWidth > 860) closeMobileMenu();
});

document.querySelectorAll(".nav-item").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
    button.classList.add("active");
    document.querySelector(`#view-${button.dataset.view}`).classList.add("active");
    setViewHeader(button.dataset.view);
    closeMobileMenu();
    if (button.dataset.view !== "scan") {
      stopCamera();
    }
    if (button.dataset.view !== "register") {
      stopRegisterScanner();
    }
    if (button.dataset.view === "register") {
      initEmployeeCatalog().catch(() => {});
      refreshScheduleOverview().catch(() => {});
    }
    if (button.dataset.view === "attendance") {
      refreshEvents().catch(() => {});
      renderAttendanceOps();
    }
    if (button.dataset.view === "reports") {
      refreshReport().catch(() => showToast("No se pudo cargar el reporte", 5000, "error"));
    }
    if (["organization", "areas", "devices", "settings"].includes(button.dataset.view)) {
      refreshAdminOverview().catch(() => showToast("No se pudo cargar administracion", 5000, "error"));
    }
    if (button.dataset.view === "settings") {
      syncSettingsApiStatus();
    }
    if (button.dataset.view === "schedules") {
      refreshScheduleOverview(true).catch(() => showToast("No se pudo cargar horarios", 5000, "error"));
    }
    if (button.dataset.view === "preregistration") {
      Promise.all([initEmployeeCatalog(), refreshScheduleOverview(), refreshPreRegistrations(true)])
        .catch(() => showToast("No se pudo cargar pre-registros", 5000, "error"));
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
document.querySelector("#event-form")?.addEventListener("submit", submitAttendanceEvent);
document.querySelector("#exit-form")?.addEventListener("submit", submitExitAttempt);
document.querySelector("#attendance-open-scan")?.addEventListener("click", () => openDashboardView("scan"));
document.querySelector("#attendance-open-reports")?.addEventListener("click", () => openDashboardView("reports"));
document.querySelector("#attendance-refresh-events")?.addEventListener("click", () => {
  refreshEvents().catch(() => showToast("No se pudo actualizar actividad", 5000, "error"));
});
document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-open-view]");
  if (!button) return;
  openDashboardView(button.dataset.openView);
});
document.querySelector("#face-register-form").addEventListener("submit", submitFaceRegister);
registerStartScanBtn?.addEventListener("click", (event) => {
  event.preventDefault();
  startRegisterFaceScan();
});
faceRegisterForm?.addEventListener("change", handleRegisterFormChange);
registerAreaSelect?.addEventListener("change", handleRegisterAreaChange);
registerPositionSelect?.addEventListener("change", () => refreshRegisterEmployeeCode());
startCameraBtn?.addEventListener("click", startCamera);
stopCameraBtn?.addEventListener("click", stopCamera);
scanCameraBtn?.addEventListener("click", () => scanFromCamera());
scanCheckInBtn?.addEventListener("click", () => scanWithEventType("check_in"));
scanCheckOutBtn?.addEventListener("click", () => scanWithEventType("check_out"));
scanModeCheckInBtn?.addEventListener("click", () => setScanEventType("check_in"));
scanModeCheckOutBtn?.addEventListener("click", () => setScanEventType("check_out"));
autoScanInput?.addEventListener("change", toggleAutoScan);
voiceAssistantInput?.addEventListener("change", () => {
  state.camera.speakingEnabled = voiceAssistantInput.checked;
  if (!voiceAssistantInput.checked) {
    stopSpeech();
  }
});
setScanEventType("check_in");
if (voiceAssistantInput) {
  state.camera.speakingEnabled = voiceAssistantInput.checked;
}
initSpeechSynthesis();
document.querySelector("#registered-users")?.addEventListener("click", handleUserCardAction);
userEditForm?.addEventListener("submit", submitUserEdit);
document.querySelector("#user-edit-cancel")?.addEventListener("click", closeUserEditDialog);
showInactiveUsersInput?.addEventListener("change", renderRegisteredUsers);
userPhotoInput?.addEventListener("change", handleQuickPhotoSelected);
organizationForm?.addEventListener("submit", submitOrganizationForm);
organizationForm?.addEventListener("input", handleOrganizationThemePreview);
organizationForm?.addEventListener("change", handleOrganizationThemePreview);
areaForm?.addEventListener("submit", submitAreaForm);
positionForm?.addEventListener("submit", submitPositionForm);
deviceForm?.addEventListener("submit", submitDeviceForm);
settingsForm?.addEventListener("submit", submitSettingsForm);
apiSettingsForm?.addEventListener("submit", submitApiSettingsForm);
document.querySelector("#reload-admin")?.addEventListener("click", () => {
  refreshAdminOverview(true).catch(() => showToast("No se pudo recargar administracion", 5000, "error"));
});
document.querySelector("#admin-areas-list")?.addEventListener("click", handleAdminAreaAction);
document.querySelector("#admin-positions-list")?.addEventListener("click", handleAdminPositionAction);
document.querySelector("#admin-devices-list")?.addEventListener("click", handleAdminDeviceAction);
shiftAssignmentForm?.addEventListener("submit", submitShiftAssignmentForm);
preRegisterForm?.addEventListener("submit", submitPreRegisterForm);
preRegisterAreaSelect?.addEventListener("change", handlePreRegisterAreaChange);
shiftRosterSearch?.addEventListener("input", renderEmployeesByShift);
document.querySelector("#pre-registrations-list")?.addEventListener("click", handlePreRegistrationAction);
document.querySelector("#reload-pre-registrations")?.addEventListener("click", () => {
  refreshPreRegistrations(true).catch(() => showToast("No se pudo recargar tokens", 5000, "error"));
});
document.querySelector("#reload-schedules")?.addEventListener("click", () => {
  refreshScheduleOverview(true).catch(() => showToast("No se pudo recargar horarios", 5000, "error"));
});

initApiBaseDefault();
const persistedBrandTheme = loadPersistedBrandTheme();
if (persistedBrandTheme) {
  applyBrandTheme(persistedBrandTheme);
}
renderCameraSecurityBanners();
refreshAll();
refreshAdminOverview().catch(() => {});
refreshScheduleOverview().catch(() => {});
refreshPreRegistrations().catch(() => {});
setViewHeader("overview");
state.refreshTimer = window.setInterval(() => {
  refreshAll().catch(() => {});
}, 30_000);
if (faceRegisterForm) {
  updateRegisterFilesSummary(faceRegisterForm);
  setRegisterStatus("idle", "Listo para escanear", "Selecciona area y cargo, completa el nombre y pulsa Iniciar escaneo facial.");
  initEmployeeCatalog().catch(() => {});
  refreshScheduleOverview().catch(() => {});
  renderPreRegisterOptions();
}

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
  const viewsNeedingFaces = ["overview", "users", "register", "scan"];
  if (viewsNeedingFaces.includes(activeView)) {
    tasks.push(refreshFaces());
  }
  if (activeView === "reports") {
    tasks.push(refreshReport());
  }
  if (activeView === "scan" || state.camera.stream) {
    tasks.push(refreshAttendancePolicy());
  }
  if (["organization", "areas", "devices", "settings"].includes(activeView)) {
    tasks.push(refreshAdminOverview());
  }
  if (["schedules", "register", "users", "reports"].includes(activeView)) {
    tasks.push(refreshScheduleOverview());
  }
  if (activeView === "preregistration") {
    tasks.push(refreshPreRegistrations());
  }
  if (activeView === "attendance") {
    tasks.push(refreshEvents());
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

async function refreshAdminOverview(force = false) {
  const data = await requestJson("/api/v1/admin/overview");
  const fingerprint = JSON.stringify({
    organization: data.organization,
    areas: data.areas,
    positions: data.positions,
    devices: data.devices,
    settings: data.settings,
  });
  if (!force && fingerprint === state.adminFingerprint) return data;
  state.admin = data;
  state.adminFingerprint = fingerprint;
  applyAdminSettings(data.settings);
  renderAdminViews();
  return data;
}

function applyAdminSettings(settings) {
  if (!settings) return;
  state.camera.attendanceCooldownMs = Number(settings.attendance_cooldown_ms || 12_000);
  if (livenessEnabledInput) {
    livenessEnabledInput.checked = Boolean(settings.liveness_enabled);
  }
  if (voiceAssistantInput) {
    voiceAssistantInput.checked = Boolean(settings.voice_enabled);
    state.camera.speakingEnabled = voiceAssistantInput.checked;
  }
}

function renderAdminViews() {
  renderOrganizationForm();
  renderAreasAndPositions();
  renderDevicesAdmin();
  renderSettingsForm();
  applyBrandTheme(state.admin?.organization);
  renderDashboard();
}

function renderOrganizationForm() {
  if (!organizationForm || !state.admin?.organization) return;
  const org = state.admin.organization;
  formField(organizationForm, "code").value = org.code || "";
  formField(organizationForm, "name").value = org.name || "";
  formField(organizationForm, "ruc").value = org.ruc || "";
  formField(organizationForm, "logo_url").value = org.logo_url || "";
  formField(organizationForm, "address").value = org.address || "";
  formField(organizationForm, "timezone").value = org.timezone || "America/Lima";
  formField(organizationForm, "brand_primary_color").value = normalizeHexColor(org.brand_primary_color, "#0d9488");
  formField(organizationForm, "brand_accent_color").value = normalizeHexColor(org.brand_accent_color, "#2563eb");
  formField(organizationForm, "brand_sidebar_color").value = normalizeHexColor(org.brand_sidebar_color, "#101827");
  formField(organizationForm, "sites").value = (org.sites || [])
    .map((site) => [site.code, site.name, site.address || "", site.is_active === false ? "inactive" : "active"].join(" | "))
    .join("\n");
  applyBrandTheme(org);
  const summary = document.querySelector("#organization-summary");
  if (summary) {
    const sites = org.sites || [];
    const activeSites = sites.filter((site) => site.is_active !== false);
    const initials = getInitials(org.name || org.code || "IA");
    summary.innerHTML = `
      <article class="company-card">
        <div class="company-avatar">${escapeHtml(initials)}</div>
        <div>
          <span class="section-kicker">Empresa activa</span>
          <strong>${escapeHtml(org.name || "Empresa sin nombre")}</strong>
          <small>${escapeHtml(org.address || "Direccion principal pendiente")}</small>
        </div>
      </article>
      <div class="company-kpis">
        <article class="admin-summary-item">
          <span>RUC</span>
          <strong>${escapeHtml(org.ruc || "Pendiente")}</strong>
        </article>
        <article class="admin-summary-item">
          <span>Codigo</span>
          <strong>${escapeHtml(org.code || "-")}</strong>
        </article>
        <article class="admin-summary-item">
          <span>Sedes activas</span>
          <strong>${activeSites.length}/${sites.length}</strong>
        </article>
        <article class="admin-summary-item">
          <span>Zona horaria</span>
          <strong>${escapeHtml(org.timezone || "America/Lima")}</strong>
        </article>
      </div>
      <div class="site-list">
        <h3>Sedes registradas</h3>
        ${
          sites.length
            ? sites
                .map((site) => {
                  const siteAddress = effectiveSiteAddress(site, org);
                  return `
                  <article class="site-row">
                    <div>
                      <strong>${escapeHtml(site.name || site.code)}</strong>
                      <small>${escapeHtml(siteAddress || "Sin direccion")}</small>
                    </div>
                    <span class="badge ${site.is_active === false ? "bad" : "ok"}">${site.is_active === false ? "Inactiva" : "Activa"}</span>
                  </article>
                `;
                })
                .join("")
            : emptyAdminState("Sin sedes", "Agrega sedes para separar operaciones y dispositivos")
        }
      </div>
    `;
  }
  renderAdminWarnings();
}

function effectiveSiteAddress(site, org) {
  const ownAddress = String(site?.address || "").trim();
  if (ownAddress) return ownAddress;
  const code = String(site?.code || "").trim().toUpperCase();
  const name = String(site?.name || "").trim().toLowerCase();
  if (code === "HQ" || name.includes("principal")) {
    return org?.address || "";
  }
  return "";
}

function applyBrandTheme(org) {
  const primary = normalizeHexColor(org?.brand_primary_color, "#0d9488");
  const accent = normalizeHexColor(org?.brand_accent_color, "#2563eb");
  const sidebar = normalizeHexColor(org?.brand_sidebar_color, "#101827");
  const primaryLight = tintHex(primary, 42);
  const primaryDark = shadeHex(primary, -22);
  const root = document.documentElement;

  root.style.setProperty("--accent", primary);
  root.style.setProperty("--accent-hover", primaryDark);
  root.style.setProperty("--accent-soft", rgbaHex(primary, 0.14));
  root.style.setProperty("--accent-glow", rgbaHex(primary, 0.28));
  root.style.setProperty("--blue", accent);
  root.style.setProperty("--blue-soft", rgbaHex(accent, 0.14));
  root.style.setProperty("--sidebar-bg", sidebar);
  root.style.setProperty("--sidebar-active", rgbaHex(primary, 0.14));
  root.style.setProperty("--sidebar-active-border", rgbaHex(primary, 0.24));
  root.style.setProperty("--sidebar-active-icon", rgbaHex(primary, 0.22));
  root.style.setProperty("--nav-active-color", tintHex(primary, 58));
  root.style.setProperty("--brand-logo-gradient", `linear-gradient(145deg, ${primaryLight} 0%, ${primary} 100%)`);
  root.style.setProperty("--brand-logo-shadow", rgbaHex(primary, 0.35));
  root.style.setProperty(
    "--brand-btn-gradient",
    `linear-gradient(135deg, ${tintHex(primary, 18)} 0%, ${primary} 52%, ${primaryDark} 100%)`,
  );
  root.style.setProperty("--ring-accent", rgbaHex(primary, 0.82));
  root.style.setProperty("--ring-accent-soft", rgbaHex(primary, 0.38));
  root.style.setProperty("--scan-ring", rgbaHex(primary, 0.85));

  persistBrandTheme({
    brand_primary_color: primary,
    brand_accent_color: accent,
    brand_sidebar_color: sidebar,
  });
}

const BRAND_THEME_STORAGE_KEY = "ia_facial_brand_theme";

function persistBrandTheme(org) {
  if (!org) return;
  try {
    localStorage.setItem(
      BRAND_THEME_STORAGE_KEY,
      JSON.stringify({
        brand_primary_color: org.brand_primary_color,
        brand_accent_color: org.brand_accent_color,
        brand_sidebar_color: org.brand_sidebar_color,
      }),
    );
  } catch {
    // ignore storage errors
  }
}

function loadPersistedBrandTheme() {
  try {
    const raw = localStorage.getItem(BRAND_THEME_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return null;
    return parsed;
  } catch {
    return null;
  }
}

function normalizeHexColor(value, fallback) {
  const text = String(value || "").trim();
  return /^#[0-9a-f]{6}$/i.test(text) ? text : fallback;
}

function hexToRgb(hex) {
  const normalized = normalizeHexColor(hex, "#0d9488").slice(1);
  return {
    r: parseInt(normalized.slice(0, 2), 16),
    g: parseInt(normalized.slice(2, 4), 16),
    b: parseInt(normalized.slice(4, 6), 16),
  };
}

function rgbaHex(hex, alpha) {
  const { r, g, b } = hexToRgb(hex);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function shadeHex(hex, percent) {
  const { r, g, b } = hexToRgb(hex);
  const shift = (channel) => {
    const target = percent < 0 ? 0 : 255;
    const amount = Math.abs(percent) / 100;
    return Math.round(channel + (target - channel) * amount);
  };
  return `#${[shift(r), shift(g), shift(b)]
    .map((channel) => channel.toString(16).padStart(2, "0"))
    .join("")}`;
}

function tintHex(hex, percent) {
  return shadeHex(hex, Math.abs(percent));
}

function renderAreasAndPositions() {
  if (!state.admin) return;
  const areas = state.admin.areas || [];
  const positions = state.admin.positions || [];
  if (adminAreaSelect) {
    const current = adminAreaSelect.value;
    adminAreaSelect.innerHTML = [
      '<option value="">Selecciona area...</option>',
      ...areas.map(
        (area) =>
          `<option value="${escapeHtml(area.code)}">${escapeHtml(area.name)} (${escapeHtml(area.code)})</option>`,
      ),
    ].join("");
    adminAreaSelect.value = current;
  }
  const areaList = document.querySelector("#admin-areas-list");
  if (areaList) {
    areaList.innerHTML = areas.length
      ? areas
          .map((area) => {
            const count = positions.filter((position) => position.area_code === area.code).length;
            const badge = area.is_active ? "ok" : "bad";
            const label = area.is_active ? "Activo" : "Inactivo";
            return `
              <article class="admin-row">
                <div>
                  <strong>${escapeHtml(area.name)}</strong>
                  <small><code>${escapeHtml(area.code)}</code> - ${count} cargo(s) - Orden ${area.sort_order}</small>
                </div>
                <div class="admin-row-actions">
                  <span class="badge ${badge}">${label}</span>
                  <button class="ghost-btn" type="button" data-admin-action="edit-area" data-area-code="${escapeHtml(area.code)}">Editar</button>
                  <button class="${area.is_active ? "danger-btn" : "ghost-btn"}" type="button" data-admin-action="toggle-area" data-area-code="${escapeHtml(area.code)}" data-next-active="${area.is_active ? "false" : "true"}">${area.is_active ? "Desactivar" : "Activar"}</button>
                </div>
              </article>`;
          })
          .join("")
      : emptyAdminState("Sin areas", "Crea la primera area para organizar empleados");
  }
  const positionList = document.querySelector("#admin-positions-list");
  if (positionList) {
    positionList.innerHTML = positions.length
      ? positions
          .map((position) => {
            const area = areas.find((item) => item.code === position.area_code);
            const badge = position.is_active ? "ok" : "bad";
            const label = position.is_active ? "Activo" : "Inactivo";
            return `
              <article class="admin-row">
                <div>
                  <strong>${escapeHtml(position.name)}</strong>
                  <small><code>${escapeHtml(position.area_code)}-${escapeHtml(position.code)}</code> - ${escapeHtml(area?.name || "Area no encontrada")} - Orden ${position.sort_order}</small>
                </div>
                <div class="admin-row-actions">
                  <span class="badge ${badge}">${label}</span>
                  <button class="ghost-btn" type="button" data-admin-action="edit-position" data-area-code="${escapeHtml(position.area_code)}" data-position-code="${escapeHtml(position.code)}">Editar</button>
                  <button class="${position.is_active ? "danger-btn" : "ghost-btn"}" type="button" data-admin-action="toggle-position" data-area-code="${escapeHtml(position.area_code)}" data-position-code="${escapeHtml(position.code)}" data-next-active="${position.is_active ? "false" : "true"}">${position.is_active ? "Desactivar" : "Activar"}</button>
                </div>
              </article>`;
          })
          .join("")
      : emptyAdminState("Sin cargos", "Crea cargos dentro de cada area");
  }
  renderOrganizationHierarchy(areas, positions);
  renderAdminWarnings();
}

function renderOrganizationHierarchy(areas, positions) {
  const hierarchy = document.querySelector("#admin-hierarchy-list");
  if (!hierarchy) return;
  if (!areas.length) {
    hierarchy.innerHTML = emptyAdminState("Sin estructura", "Crea areas y cargos para ver el mapa organizacional");
    return;
  }
  hierarchy.innerHTML = areas
    .slice()
    .sort((a, b) => Number(a.sort_order || 0) - Number(b.sort_order || 0))
    .map((area) => {
      const areaPositions = positions
        .filter((position) => position.area_code === area.code)
        .sort((a, b) => Number(a.sort_order || 0) - Number(b.sort_order || 0));
      return `
        <article class="org-node ${area.is_active ? "" : "inactive"}">
          <div class="org-node-header">
            <div>
              <span class="section-kicker">${escapeHtml(area.code)}</span>
              <strong>${escapeHtml(area.name)}</strong>
              <small>${areaPositions.length} cargo(s) asociados</small>
            </div>
            <span class="badge ${area.is_active ? "ok" : "bad"}">${area.is_active ? "Activa" : "Inactiva"}</span>
          </div>
          <div class="position-chip-list">
            ${
              areaPositions.length
                ? areaPositions
                    .map((position) => `
                      <span class="position-chip ${position.is_active ? "" : "inactive"}">
                        <b>${escapeHtml(position.code)}</b>
                        ${escapeHtml(position.name)}
                      </span>
                    `)
                    .join("")
                : '<span class="position-chip muted">Sin cargos asignados</span>'
            }
          </div>
        </article>
      `;
    })
    .join("");
}

function renderDevicesAdmin() {
  if (!state.admin) return;
  const devices = state.admin.devices || [];
  const list = document.querySelector("#admin-devices-list");
  if (list) {
    list.innerHTML = devices.length
      ? devices
          .map((device) => {
            const statusBadge = device.online ? "ok" : (device.is_active ? "warn" : "bad");
            const status = device.online ? "Online" : (device.is_active ? "Sin actividad" : "Inactivo");
            return `
              <article class="admin-row">
                <div>
                  <strong>${escapeHtml(device.label || device.device_id)}</strong>
                  <small><code>${escapeHtml(device.device_id)}</code> - ${escapeHtml(device.kind || "edge")} - ${escapeHtml(device.location || "Sin ubicacion")} - Ultima actividad: ${formatDate(device.last_seen_at)}</small>
                </div>
                <div class="admin-row-actions">
                  <span class="badge ${statusBadge}">${status}</span>
                  <button class="ghost-btn" type="button" data-admin-action="edit-device" data-device-id="${escapeHtml(device.device_id)}">Editar</button>
                  <button class="${device.is_active ? "danger-btn" : "ghost-btn"}" type="button" data-admin-action="toggle-device" data-device-id="${escapeHtml(device.device_id)}" data-next-active="${device.is_active ? "false" : "true"}">${device.is_active ? "Desactivar" : "Activar"}</button>
                </div>
              </article>`;
          })
          .join("")
      : emptyAdminState("Sin dispositivos", "Registra una camara, PC o kiosko");
  }
  renderAdminWarnings();
}

function renderSettingsForm() {
  if (!settingsForm || !state.admin?.settings) return;
  const settings = state.admin.settings;
  formField(settingsForm, "camera_device_id").value = settings.camera_device_id || "dashboard-camera-001";
  formField(settingsForm, "attendance_cooldown_ms").value = settings.attendance_cooldown_ms ?? 12000;
  formField(settingsForm, "face_match_threshold").value = settings.face_match_threshold ?? 0.35;
  formField(settingsForm, "face_scan_match_threshold").value = settings.face_scan_match_threshold ?? 0.48;
  formField(settingsForm, "default_scheduled_exit_time").value = settings.default_scheduled_exit_time || "22:00";
  formField(settingsForm, "default_exit_tolerance_minutes").value = settings.default_exit_tolerance_minutes ?? 10;
  formField(settingsForm, "liveness_enabled").checked = Boolean(settings.liveness_enabled);
  formField(settingsForm, "voice_enabled").checked = Boolean(settings.voice_enabled);
  const runtime = document.querySelector("#settings-runtime");
  if (runtime) {
    runtime.innerHTML = `
      <article class="admin-summary-item">
        <span>Storage</span>
        <strong>${escapeHtml(settings.storage_backend)}</strong>
      </article>
      <article class="admin-summary-item">
        <span>Modo JSON</span>
        <strong>${settings.json_mode ? "Activo" : "No"}</strong>
      </article>
      <article class="admin-summary-item">
        <span>R2</span>
        <strong>${settings.r2_enabled ? "Configurado" : "Pendiente"}</strong>
      </article>
    `;
  }
  renderAdminWarnings();
}

function renderAdminWarnings() {
  const warningBox = document.querySelector("#admin-warnings");
  if (!warningBox) return;
  const warnings = state.admin?.warnings || [];
  if (!warnings.length) {
    warningBox.classList.add("hidden");
    warningBox.innerHTML = "";
    return;
  }
  warningBox.classList.remove("hidden");
  warningBox.innerHTML = warnings.map((item) => `<p>${escapeHtml(item)}</p>`).join("");
}

function emptyAdminState(title, detail) {
  return `
    <div class="empty-state compact-empty">
      <span class="empty-icon">o</span>
      <p>${escapeHtml(title)}</p>
      <small>${escapeHtml(detail)}</small>
    </div>`;
}

function formField(form, name) {
  return form.elements[name];
}

function handleOrganizationThemePreview(event) {
  if (!event.target?.matches?.('input[type="color"]')) return;
  applyBrandTheme({
    ...(state.admin?.organization || {}),
    brand_primary_color: formField(organizationForm, "brand_primary_color")?.value,
    brand_accent_color: formField(organizationForm, "brand_accent_color")?.value,
    brand_sidebar_color: formField(organizationForm, "brand_sidebar_color")?.value,
  });
}

async function submitOrganizationForm(event) {
  event.preventDefault();
  const submitBtn = organizationForm?.querySelector('[type="submit"]');
  const defaultLabel = submitBtn?.dataset.defaultLabel || submitBtn?.textContent || "Guardar";
  setButtonLoading(submitBtn, true, "Guardando...", defaultLabel);
  const form = new FormData(organizationForm);
  const payload = {
    name: String(form.get("name") || "").trim(),
    timezone: String(form.get("timezone") || "").trim() || "America/Lima",
    ruc: String(form.get("ruc") || "").trim() || null,
    logo_url: String(form.get("logo_url") || "").trim() || null,
    address: String(form.get("address") || "").trim() || null,
    brand_primary_color: normalizeHexColor(form.get("brand_primary_color"), "#0d9488"),
    brand_accent_color: normalizeHexColor(form.get("brand_accent_color"), "#2563eb"),
    brand_sidebar_color: normalizeHexColor(form.get("brand_sidebar_color"), "#101827"),
    sites: parseSites(String(form.get("sites") || "")),
  };
  try {
    const data = await requestJson("/api/v1/admin/organization", {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    state.admin.organization = data.organization;
    state.adminFingerprint = "";
    renderOrganizationForm();
    applyBrandTheme(data.organization);
    showToast(data.message || "Organizacion guardada", 4000, "success");
  } catch (error) {
    showToast(parseApiError(error), 6000, "error");
  } finally {
    setButtonLoading(submitBtn, false, "", defaultLabel);
  }
}

async function submitAreaForm(event) {
  event.preventDefault();
  const form = new FormData(areaForm);
  const payload = {
    code: String(form.get("code") || "").trim().toUpperCase(),
    name: String(form.get("name") || "").trim(),
    sort_order: Number(form.get("sort_order") || 0),
    is_active: form.get("is_active") === "on",
  };
  try {
    const data = await requestJson("/api/v1/admin/areas", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    showToast(data.message || "Area guardada", 4000, "success");
    areaForm.reset();
    formField(areaForm, "is_active").checked = true;
    state.employeeCatalog = null;
    await refreshAdminOverview(true);
  } catch (error) {
    showToast(parseApiError(error), 6000, "error");
  }
}

async function submitPositionForm(event) {
  event.preventDefault();
  const form = new FormData(positionForm);
  const payload = {
    area_code: String(form.get("area_code") || "").trim().toUpperCase(),
    code: String(form.get("code") || "").trim().toUpperCase(),
    name: String(form.get("name") || "").trim(),
    sort_order: Number(form.get("sort_order") || 0),
    is_active: form.get("is_active") === "on",
  };
  try {
    const data = await requestJson("/api/v1/admin/positions", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    showToast(data.message || "Cargo guardado", 4000, "success");
    const currentArea = formField(positionForm, "area_code").value;
    positionForm.reset();
    formField(positionForm, "area_code").value = currentArea;
    formField(positionForm, "is_active").checked = true;
    state.employeeCatalog = null;
    await refreshAdminOverview(true);
  } catch (error) {
    showToast(parseApiError(error), 6000, "error");
  }
}

async function submitDeviceForm(event) {
  event.preventDefault();
  const form = new FormData(deviceForm);
  const payload = {
    device_id: String(form.get("device_id") || "").trim(),
    label: String(form.get("label") || "").trim(),
    kind: String(form.get("kind") || "edge").trim() || "edge",
    location: String(form.get("location") || "").trim() || null,
    is_active: form.get("is_active") === "on",
  };
  try {
    const data = await requestJson("/api/v1/admin/devices", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    showToast(data.message || "Dispositivo guardado", 4000, "success");
    deviceForm.reset();
    formField(deviceForm, "kind").value = "edge";
    formField(deviceForm, "is_active").checked = true;
    await refreshAdminOverview(true);
  } catch (error) {
    showToast(parseApiError(error), 6000, "error");
  }
}

async function submitApiSettingsForm(event) {
  event.preventDefault();
  if (!apiBaseInput) return;

  const url = apiBaseInput.value.trim().replace(/\/$/, "");
  if (!url) {
    showToast("Ingresa la URL del servidor API.", 4000, "error");
    return;
  }

  apiBaseInput.value = url;
  saveStoredApiBase(url);
  setApiStatus(false);
  document.querySelector("#api-status-label").textContent = "Verificando...";
  syncSettingsApiStatus();

  try {
    const ok = await probeApiConnection();
    if (ok) {
      showToast("Conexion guardada y verificada.", 4000, "success");
      await refreshAll();
    } else {
      showToast("URL guardada, pero el servidor no responde.", 6000, "error");
    }
  } catch (error) {
    showToast(parseApiError(error), 6000, "error");
  } finally {
    syncSettingsApiStatus();
  }
}

async function submitSettingsForm(event) {
  event.preventDefault();
  const form = new FormData(settingsForm);
  const payload = {
    camera_device_id: String(form.get("camera_device_id") || "").trim() || "dashboard-camera-001",
    liveness_enabled: form.get("liveness_enabled") === "on",
    voice_enabled: form.get("voice_enabled") === "on",
    attendance_cooldown_ms: Number(form.get("attendance_cooldown_ms") || 12000),
    face_match_threshold: Number(form.get("face_match_threshold") || 0.35),
    face_scan_match_threshold: Number(form.get("face_scan_match_threshold") || 0.48),
    default_scheduled_exit_time: String(form.get("default_scheduled_exit_time") || "22:00"),
    default_exit_tolerance_minutes: Number(form.get("default_exit_tolerance_minutes") || 10),
  };
  try {
    const data = await requestJson("/api/v1/admin/settings", {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    state.admin.settings = data.settings;
    applyAdminSettings(data.settings);
    renderSettingsForm();
    showToast(data.message || "Configuracion guardada", 4000, "success");
  } catch (error) {
    showToast(parseApiError(error), 6000, "error");
  }
}

async function handleAdminAreaAction(event) {
  const button = event.target.closest("[data-admin-action]");
  if (!button) return;
  const areaCode = button.dataset.areaCode;
  const area = state.admin?.areas?.find((item) => item.code === areaCode);
  if (!area) return;
  if (button.dataset.adminAction === "edit-area") {
    formField(areaForm, "code").value = area.code;
    formField(areaForm, "name").value = area.name;
    formField(areaForm, "sort_order").value = area.sort_order;
    formField(areaForm, "is_active").checked = area.is_active;
    formField(areaForm, "code").focus();
    return;
  }
  if (button.dataset.adminAction === "toggle-area") {
    await updateAdminArea(areaCode, { is_active: button.dataset.nextActive === "true" });
  }
}

async function handleAdminPositionAction(event) {
  const button = event.target.closest("[data-admin-action]");
  if (!button) return;
  const areaCode = button.dataset.areaCode;
  const positionCode = button.dataset.positionCode;
  const position = state.admin?.positions?.find(
    (item) => item.area_code === areaCode && item.code === positionCode,
  );
  if (!position) return;
  if (button.dataset.adminAction === "edit-position") {
    formField(positionForm, "area_code").value = position.area_code;
    formField(positionForm, "code").value = position.code;
    formField(positionForm, "name").value = position.name;
    formField(positionForm, "sort_order").value = position.sort_order;
    formField(positionForm, "is_active").checked = position.is_active;
    formField(positionForm, "code").focus();
    return;
  }
  if (button.dataset.adminAction === "toggle-position") {
    await updateAdminPosition(areaCode, positionCode, { is_active: button.dataset.nextActive === "true" });
  }
}

async function handleAdminDeviceAction(event) {
  const button = event.target.closest("[data-admin-action]");
  if (!button) return;
  const deviceId = button.dataset.deviceId;
  const device = state.admin?.devices?.find((item) => item.device_id === deviceId);
  if (!device) return;
  if (button.dataset.adminAction === "edit-device") {
    formField(deviceForm, "device_id").value = device.device_id;
    formField(deviceForm, "label").value = device.label;
    formField(deviceForm, "kind").value = device.kind || "edge";
    formField(deviceForm, "location").value = device.location || "";
    formField(deviceForm, "is_active").checked = device.is_active;
    formField(deviceForm, "device_id").focus();
    return;
  }
  if (button.dataset.adminAction === "toggle-device") {
    await updateAdminDevice(deviceId, { is_active: button.dataset.nextActive === "true" });
  }
}

async function updateAdminArea(areaCode, payload) {
  try {
    const data = await requestJson(`/api/v1/admin/areas/${encodeURIComponent(areaCode)}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    showToast(data.message || "Area actualizada", 4000, "success");
    state.employeeCatalog = null;
    await refreshAdminOverview(true);
  } catch (error) {
    showToast(parseApiError(error), 6000, "error");
  }
}

async function updateAdminPosition(areaCode, positionCode, payload) {
  try {
    const data = await requestJson(
      `/api/v1/admin/positions/${encodeURIComponent(areaCode)}/${encodeURIComponent(positionCode)}`,
      { method: "PATCH", body: JSON.stringify(payload) },
    );
    showToast(data.message || "Cargo actualizado", 4000, "success");
    state.employeeCatalog = null;
    await refreshAdminOverview(true);
  } catch (error) {
    showToast(parseApiError(error), 6000, "error");
  }
}

async function updateAdminDevice(deviceId, payload) {
  try {
    const data = await requestJson(`/api/v1/admin/devices/${encodeURIComponent(deviceId)}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    showToast(data.message || "Dispositivo actualizado", 4000, "success");
    await refreshAdminOverview(true);
  } catch (error) {
    showToast(parseApiError(error), 6000, "error");
  }
}

function parseSites(value) {
  return String(value || "")
    .split(/\r?\n/)
    .map((line, index) => {
      const parts = line.split("|").map((part) => part.trim());
      const name = parts[1] || parts[0];
      if (!name) return null;
      const code = (parts[1] ? parts[0] : buildSiteCode(name, index)).toUpperCase();
      return {
        code,
        name,
        address: parts[2] || null,
        is_active: (parts[3] || "active").toLowerCase() !== "inactive",
      };
    })
    .filter(Boolean);
}

function buildSiteCode(name, index) {
  const code = String(name || "")
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, "")
    .slice(0, 8);
  return code || `S${index + 1}`;
}

async function refreshScheduleOverview(force = false) {
  const data = await requestJson("/api/v1/schedules/overview");
  const fingerprint = JSON.stringify({
    shifts: data.shifts,
    assignments: data.assignments,
    employees: data.employees?.map((item) => `${item.person_id}:${item.shift_code}:${item.is_active}`),
  });
  if (!force && fingerprint === state.scheduleFingerprint) return data;
  state.schedule = data;
  state.scheduleFingerprint = fingerprint;
  renderShiftOptions();
  renderSchedulesView();
  return data;
}

function renderShiftOptions() {
  const shifts = activeShifts();
  const options = [
    '<option value="">Sin turno asignado...</option>',
    ...shifts.map(
      (shift) =>
        `<option value="${escapeHtml(shift.code)}">${escapeHtml(shift.code)} - ${escapeHtml(shift.name)} (${formatTimeShort(shift.start_time)} - ${formatTimeShort(shift.end_time)})</option>`,
    ),
  ].join("");
  if (registerShiftSelect) {
    const current = registerShiftSelect.value;
    registerShiftSelect.innerHTML = options;
    registerShiftSelect.value = current;
  }
  if (shiftCodeSelect) {
    const current = shiftCodeSelect.value;
    shiftCodeSelect.innerHTML = [
      '<option value="">Selecciona turno...</option>',
      ...shifts.map(
        (shift) =>
          `<option value="${escapeHtml(shift.code)}">${escapeHtml(shift.code)} - ${escapeHtml(shift.name)}</option>`,
      ),
    ].join("");
    shiftCodeSelect.value = current;
  }
  if (shiftEmployeeSelect) {
    const current = shiftEmployeeSelect.value;
    const employees = state.schedule?.employees || [];
    shiftEmployeeSelect.innerHTML = [
      '<option value="">Selecciona empleado...</option>',
      ...employees.map(
        (employee) =>
          `<option value="${escapeHtml(employee.person_id)}">${escapeHtml(employee.employee_code || employee.person_id)} - ${escapeHtml(employee.name)}</option>`,
      ),
    ].join("");
    shiftEmployeeSelect.value = current;
  }
  if (userEditShiftSelect) {
    const current = userEditShiftSelect.value;
    userEditShiftSelect.innerHTML = options;
    userEditShiftSelect.value = current;
  }
}

function renderSchedulesView() {
  renderScheduleSummary();
  renderShiftCards();
  renderShiftRules();
  renderEmployeesByShift();
}

function renderScheduleSummary() {
  const container = document.querySelector("#shift-summary");
  if (!container) return;
  const schedule = state.schedule;
  if (!schedule) {
    container.innerHTML = `
      <article><span>Total empleados</span><strong>--</strong></article>
      <article><span>Asignados</span><strong>--</strong></article>
      <article><span>Sin turno</span><strong>--</strong></article>
      <article><span>Cobertura</span><strong>--</strong></article>
    `;
    return;
  }
  const shifts = schedule.shifts || [];
  const assigned = shifts.reduce((total, shift) => total + employeesForShift(shift.code).length, 0);
  const unassigned = employeesForShift("SIN_TURNO").length;
  const totalEmployees = Math.max(getScheduleEmployees().length, assigned + unassigned);
  const coverage = totalEmployees ? Math.round((assigned / totalEmployees) * 100) : 0;
  container.innerHTML = `
    <article>
      <span>Total empleados</span>
      <strong>${totalEmployees}</strong>
    </article>
    <article>
      <span>Asignados</span>
      <strong>${assigned}</strong>
    </article>
    <article class="${unassigned ? "summary-warn" : "summary-ok"}">
      <span>Sin turno</span>
      <strong>${unassigned}</strong>
    </article>
    <article class="${coverage >= 90 ? "summary-ok" : "summary-warn"}">
      <span>Cobertura</span>
      <strong>${coverage}%</strong>
    </article>
  `;
}

function renderShiftCards() {
  const container = document.querySelector("#shift-cards");
  if (!container) return;
  const shifts = state.schedule?.shifts || [];
  container.innerHTML = shifts.length
    ? shifts.map((shift) => {
        const tardyFrom = addMinutesToTimeLabel(shift.start_time, (shift.tolerance_minutes || 0) + 1);
        const assignedCount = employeesForShift(shift.code).length;
        return `
          <article class="shift-card">
            <div class="shift-card-header">
              <span class="shift-code">${escapeHtml(shift.code)}</span>
              <span class="badge ${shift.is_active ? "ok" : "bad"}">${shift.is_active ? "Activo" : "Inactivo"}</span>
            </div>
            <div class="shift-card-title">
              <strong>${escapeHtml(shift.name)}</strong>
              <small>${assignedCount} empleado(s) asignados</small>
            </div>
            <div class="shift-window">
              <span><b>${formatTimeShort(shift.start_time)}</b><small>Entrada</small></span>
              <span><b>${formatTimeShort(shift.end_time)}</b><small>Salida</small></span>
              <span><b>${shift.work_hours}</b><small>Horas</small></span>
            </div>
            <div class="shift-rule-line">
              <span>Tolerancia ${shift.tolerance_minutes} min</span>
              <span>Tardanza desde ${tardyFrom}</span>
            </div>
          </article>
        `;
      }).join("")
    : emptyAdminState("Sin turnos", "Crea o restaura TM/TT");
}

function renderShiftRules() {
  const container = document.querySelector("#shift-rules");
  if (!container) return;
  const shifts = state.schedule?.shifts || [];
  container.innerHTML = shifts.map((shift) => {
    const start = formatTimeShort(shift.start_time);
    const toleranceEnd = addMinutesToTimeLabel(shift.start_time, shift.tolerance_minutes || 0);
    const tardyFrom = addMinutesToTimeLabel(shift.start_time, (shift.tolerance_minutes || 0) + 1);
    return `
      <article class="admin-row">
        <div>
          <strong>${escapeHtml(shift.code)} - ${escapeHtml(shift.name)}</strong>
          <small>${start} correcto - ${toleranceEnd} correcto - ${tardyFrom} tardanza. Salida antes de ${formatTimeShort(shift.end_time)} = salida anticipada.</small>
        </div>
      </article>
    `;
  }).join("");
}

function renderEmployeesByShift() {
  const container = document.querySelector("#employees-by-shift");
  if (!container) return;
  const schedule = state.schedule;
  if (!schedule) {
    container.innerHTML = emptyAdminState("Cargando turnos", "Consultando asignaciones");
    return;
  }
  const query = String(shiftRosterSearch?.value || "").trim().toLowerCase();
  const shifts = [...(schedule.shifts || []), { code: "SIN_TURNO", name: "Sin turno", isUnassigned: true }];
  container.innerHTML = shifts.map((shift) => {
    const employees = employeesForShift(shift.code);
    const filteredEmployees = query
      ? employees.filter((employee) => employeeMatchesRosterQuery(employee, query))
      : employees;
    const hiddenCount = employees.length - filteredEmployees.length;
    const groupClass = shift.isUnassigned ? "shift-group unassigned" : "shift-group";
    return `
      <section class="${groupClass}">
        <div class="shift-group-header">
          <div>
            <span class="shift-code small">${escapeHtml(shift.code === "SIN_TURNO" ? "ST" : shift.code)}</span>
            <strong>${escapeHtml(shift.name)}</strong>
          </div>
          <span class="count-pill">${employees.length} empleado(s)</span>
        </div>
        <div class="shift-roster-list">
          ${filteredEmployees.length
            ? filteredEmployees.map((employee) => `
                <article class="shift-worker">
                  <span class="worker-avatar">${escapeHtml(getInitials(employee.name || employee.person_id))}</span>
                  <div>
                    <strong>${escapeHtml(employee.name || "Sin nombre")}</strong>
                    <small><code>${escapeHtml(employee.employee_code || employee.person_id)}</code> ${escapeHtml(employee.area_name || "Sin area")} / ${escapeHtml(employee.position_name || "Sin cargo")}</small>
                  </div>
                </article>
              `).join("")
            : emptyAdminState(
                query ? "Sin coincidencias" : "Sin empleados",
                query ? "Prueba con otro nombre, codigo o area" : "No hay empleados en este grupo",
              )}
        </div>
        ${hiddenCount > 0 ? `<p class="shift-filter-note">${hiddenCount} oculto(s) por el filtro</p>` : ""}
      </section>
    `;
  }).join("");
}

function getScheduleEmployees() {
  const schedule = state.schedule;
  if (!schedule) return [];
  if (Array.isArray(schedule.employees)) return schedule.employees;
  const grouped = schedule.employees_by_shift || {};
  const seen = new Set();
  return Object.values(grouped)
    .flat()
    .filter((employee) => {
      const key = employee.person_id || employee.employee_code || employee.name;
      if (!key || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
}

function employeesForShift(shiftCode) {
  const schedule = state.schedule;
  if (!schedule) return [];
  const grouped = schedule.employees_by_shift || {};
  if (Array.isArray(grouped[shiftCode])) return grouped[shiftCode];
  const employees = getScheduleEmployees();
  if (shiftCode === "SIN_TURNO") {
    return employees.filter((employee) => !employee.shift_code);
  }
  return employees.filter((employee) => employee.shift_code === shiftCode);
}

function employeeMatchesRosterQuery(employee, query) {
  const haystack = [
    employee.name,
    employee.employee_code,
    employee.person_id,
    employee.area_name,
    employee.position_name,
    employee.schedule_label,
  ].join(" ").toLowerCase();
  return haystack.includes(query);
}

async function submitShiftAssignmentForm(event) {
  event.preventDefault();
  const form = new FormData(shiftAssignmentForm);
  const personId = String(form.get("person_id") || "").trim();
  const shiftCode = String(form.get("shift_code") || "").trim().toUpperCase();
  if (!personId || !shiftCode) {
    showToast("Selecciona empleado y turno", 4000, "error");
    return;
  }
  try {
    const data = await requestJson(`/api/v1/schedules/assignments/${encodeURIComponent(personId)}`, {
      method: "PUT",
      body: JSON.stringify({ shift_code: shiftCode }),
    });
    showToast(data.message || "Turno asignado", 4000, "success");
    state.facesFingerprint = "";
    await Promise.all([refreshScheduleOverview(true), refreshFaces()]);
  } catch (error) {
    showToast(parseApiError(error), 6000, "error");
  }
}

function activeShifts() {
  return (state.schedule?.shifts || []).filter((shift) => shift.is_active !== false);
}

function formatTimeShort(value) {
  return String(value || "").slice(0, 5);
}

function addMinutesToTimeLabel(value, minutes) {
  const [hour, minute] = formatTimeShort(value).split(":").map(Number);
  if (Number.isNaN(hour) || Number.isNaN(minute)) return "--:--";
  const total = hour * 60 + minute + Number(minutes || 0);
  const normalized = ((total % 1440) + 1440) % 1440;
  return `${String(Math.floor(normalized / 60)).padStart(2, "0")}:${String(normalized % 60).padStart(2, "0")}`;
}

async function refreshPreRegistrations(force = false) {
  const data = await requestJson("/api/v1/employees/pre-registrations");
  const workers = data.workers || [];
  const fingerprint = workers
    .map((worker) => `${worker.employee_id}:${worker.registration_status}:${worker.token_status}:${worker.updated_at}`)
    .join("|");
  if (!force && fingerprint === state.preRegistrationsFingerprint) return data;
  state.preRegistrations = workers;
  state.preRegistrationsFingerprint = fingerprint;
  renderPreRegisterOptions();
  renderPreRegistrations();
  return data;
}

function renderPreRegisterOptions() {
  if (preRegisterAreaSelect && state.employeeCatalog?.areas) {
    const current = preRegisterAreaSelect.value;
    preRegisterAreaSelect.innerHTML = [
      '<option value="">Selecciona area...</option>',
      ...state.employeeCatalog.areas.map(
        (area) => `<option value="${escapeHtml(area.code)}">${escapeHtml(area.name)} (${escapeHtml(area.code)})</option>`,
      ),
    ].join("");
    preRegisterAreaSelect.value = current;
    handlePreRegisterAreaChange();
  }
  if (preRegisterShiftSelect) {
    const current = preRegisterShiftSelect.value;
    preRegisterShiftSelect.innerHTML = [
      '<option value="">Selecciona turno...</option>',
      ...activeShifts().map(
        (shift) =>
          `<option value="${escapeHtml(shift.code)}">${escapeHtml(shift.code)} - ${escapeHtml(shift.name)} (${formatTimeShort(shift.start_time)} - ${formatTimeShort(shift.end_time)})</option>`,
      ),
    ].join("");
    preRegisterShiftSelect.value = current;
  }
}

function handlePreRegisterAreaChange() {
  if (!preRegisterPositionSelect || !state.employeeCatalog?.positions) return;
  const areaCode = preRegisterAreaSelect?.value || "";
  const positions = state.employeeCatalog.positions.filter((item) => item.area_code === areaCode);
  if (!areaCode || !positions.length) {
    preRegisterPositionSelect.innerHTML = '<option value="">Primero elige un area...</option>';
    preRegisterPositionSelect.disabled = true;
    return;
  }
  const current = preRegisterPositionSelect.value;
  preRegisterPositionSelect.disabled = false;
  preRegisterPositionSelect.innerHTML = [
    '<option value="">Selecciona cargo...</option>',
    ...positions.map(
      (position) =>
        `<option value="${escapeHtml(position.code)}">${escapeHtml(position.name)} (${escapeHtml(position.code)})</option>`,
    ),
  ].join("");
  preRegisterPositionSelect.value = current;
}

function renderPreRegistrations() {
  const list = document.querySelector("#pre-registrations-list");
  const count = document.querySelector("#pre-registrations-count");
  if (count) count.textContent = `${state.preRegistrations.length} trabajador(es)`;
  if (!list) return;
  if (!state.preRegistrations.length) {
    list.innerHTML = emptyAdminState("Sin pre-registros", "Crea trabajadores para enviar tokens por Gmail");
    return;
  }
  list.innerHTML = state.preRegistrations
    .map((worker) => {
      const status = registrationStatusLabel(worker);
      return `
        <article class="admin-row token-worker-row">
          <div>
            <strong>${escapeHtml(worker.name)}</strong>
            <small>
              <code>${escapeHtml(worker.employee_code)}</code> -
              DNI ${escapeHtml(worker.dni)} -
              ${escapeHtml(worker.area_name)} / ${escapeHtml(worker.position_name)} -
              ${escapeHtml(worker.shift_code)} ${escapeHtml(worker.schedule_label || "")}
            </small>
            <small>Correo: ${escapeHtml(worker.email)} - Token vence: ${formatDate(worker.token_expires_at)}</small>
          </div>
          <div class="admin-row-actions">
            <span class="badge ${status.badge}">${status.label}</span>
            <button class="ghost-btn" type="button" data-token-action="resend" data-employee-id="${escapeHtml(worker.employee_id)}">Reenviar</button>
            <button class="ghost-btn" type="button" data-token-action="regenerate" data-employee-id="${escapeHtml(worker.employee_id)}">Regenerar</button>
            <button class="danger-btn" type="button" data-token-action="cancel" data-employee-id="${escapeHtml(worker.employee_id)}">Cancelar</button>
          </div>
        </article>
      `;
    })
    .join("");
}

function registrationStatusLabel(worker) {
  const status = worker.registration_status;
  if (status === "FACE_REGISTERED") return { label: "Rostro registrado", badge: "ok" };
  if (status === "TOKEN_EXPIRED" || worker.token_status === "TOKEN_EXPIRED") return { label: "Token vencido", badge: "bad" };
  if (status === "TOKEN_CANCELLED" || worker.token_status === "TOKEN_CANCELLED") return { label: "Token cancelado", badge: "bad" };
  if (worker.token_status === "TOKEN_USED") return { label: "Token usado", badge: "ok" };
  if (status === "TOKEN_SENT") return { label: "Token enviado", badge: "warn" };
  return { label: "Pendiente", badge: "warn" };
}

async function submitPreRegisterForm(event) {
  event.preventDefault();
  const form = new FormData(preRegisterForm);
  const payload = {
    name: String(form.get("name") || "").trim(),
    dni: String(form.get("dni") || "").trim(),
    email: String(form.get("email") || "").trim(),
    area_code: String(form.get("area_code") || "").trim().toUpperCase(),
    position_code: String(form.get("position_code") || "").trim().toUpperCase(),
    shift_code: String(form.get("shift_code") || "").trim().toUpperCase(),
    token_expires_hours: Number(form.get("token_expires_hours") || 48),
  };
  try {
    const data = await requestJson("/api/v1/employees/pre-register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    showTokenResult(data);
    preRegisterForm.reset();
    handlePreRegisterAreaChange();
    await refreshPreRegistrations(true);
  } catch (error) {
    showToast(parseApiError(error), 7000, "error");
  }
}

async function handlePreRegistrationAction(event) {
  const button = event.target.closest("[data-token-action]");
  if (!button) return;
  const employeeId = button.dataset.employeeId;
  const action = button.dataset.tokenAction;
  const paths = {
    resend: `/api/v1/employees/${encodeURIComponent(employeeId)}/send-registration-token`,
    regenerate: `/api/v1/employees/${encodeURIComponent(employeeId)}/regenerate-registration-token`,
    cancel: `/api/v1/employees/${encodeURIComponent(employeeId)}/cancel-registration-token`,
  };
  try {
    const data = await requestJson(paths[action], { method: "POST" });
    showTokenResult(data);
    await refreshPreRegistrations(true);
  } catch (error) {
    showToast(parseApiError(error), 7000, "error");
  }
}

function showTokenResult(data) {
  const message = data?.message || "Operacion completada";
  const devToken = data?.dev_token ? ` Token dev: ${data.dev_token}` : "";
  showToast(`${message}${devToken}`, data?.dev_token ? 12000 : 5000, data?.email_sent ? "success" : "info");
  const box = document.querySelector("#pre-register-result");
  if (box) {
    box.textContent = JSON.stringify(data, null, 2);
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
  state.lastSyncAt = new Date();
  renderEvents();
}

async function refreshReport() {
  setReportLoading(true);
  const form = document.querySelector("#report-filters");
  const params = new URLSearchParams({ limit: "150" });
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
  try {
    const data = await requestJson(`/api/v1/attendance/events?${params.toString()}`, {
      timeoutMs: 20_000,
    });
    state.reportEvents = data.events || [];
    state.reportSummary = data.summary || state.reportSummary;
    renderReport();
  } finally {
    setReportLoading(false);
  }
}

function setReportLoading(loading) {
  const wrap = document.querySelector("#report-table-wrap");
  const reloadBtn = document.querySelector("#reload-reports");
  const filterBtn = document.querySelector("#report-filters .filter-submit");
  if (reloadBtn) reloadBtn.disabled = loading;
  if (filterBtn) filterBtn.disabled = loading;
  if (!wrap || !loading) return;
  wrap.className = "report-table-wrap loading";
  wrap.innerHTML = `
    <div class="empty-state">
      <span class="empty-icon">⏳</span>
      <p>Cargando entradas y salidas...</p>
      <small>Consultando marcas de asistencia</small>
    </div>`;
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
  document.querySelector("#report-late").textContent = state.reportSummary.late ?? 0;
  document.querySelector("#report-early-exits").textContent = state.reportSummary.early_exits ?? 0;

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
          <th>Turno</th>
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
            const rowClass = !event.accepted || event.duplicate || event.work_status === "early_exit"
              ? "row-bad"
              : (event.work_status === "late" ? "row-warn" : "");
            return `
              <tr class="${rowClass}">
                <td>${formatDate(event.captured_at)}</td>
                <td>${escapeHtml(event.employee_name || "-")}</td>
                <td><code>${escapeHtml(event.person_id)}</code></td>
                <td><span class="event-type ${typeClass}">${typeLabel}</span></td>
                <td>${escapeHtml(event.shift_code ? `${event.shift_code} ${formatShiftSchedule(event)}` : "Sin turno")}</td>
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
  if (event.work_status === "late") return '<span class="badge warn">Tardanza</span>';
  if (event.work_status === "early_exit") return '<span class="badge bad">Salida anticipada</span>';
  if (event.work_status === "on_time") return '<span class="badge ok">Correcto</span>';
  return '<span class="badge ok">Aceptado</span>';
}

function formatShiftSchedule(event) {
  if (!event.scheduled_start_time || !event.scheduled_exit_time) return "";
  return `(${formatTimeShort(event.scheduled_start_time)}-${formatTimeShort(event.scheduled_exit_time)})`;
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
    if (event.work_status === "late") state.reportSummary.late -= 1;
    if (event.work_status === "early_exit") state.reportSummary.early_exits -= 1;
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
    .map((face) => `${face.person_id}:${face.is_active}:${face.embedding_count}:${face.shift_code}:${face.created_at}`)
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
        <article class="user-card${isInactive ? " inactive" : ""}" data-person-id="${escapeHtml(face.person_id)}">
          <div class="user-card-photo-wrap">${photoMarkup}</div>
          <div class="user-card-body">
            <strong>${escapeHtml(face.name)}</strong>
            <div class="user-card-meta">
              <span><b>Codigo:</b> ${escapeHtml(face.employee_code || face.person_id)}</span>
              <span><b>Area:</b> ${escapeHtml(face.area_name ? `${face.area_name} (${face.area_code})` : "Sin area")}</span>
              <span><b>Cargo:</b> ${escapeHtml(face.position_name ? `${face.position_name} (${face.position_code})` : "Sin cargo")}</span>
              <span><b>Turno:</b> ${escapeHtml(face.shift_code ? `${face.shift_code} - ${face.shift_name || "Turno"}` : "Sin turno")}</span>
              <span><b>Horario:</b> ${escapeHtml(face.schedule_label || "Sin horario")}</span>
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
              <button class="danger-btn solid full-row" type="button" data-user-action="delete" data-person-id="${escapeHtml(face.person_id)}">Eliminar definitivamente</button>
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
    return;
  }
  if (action === "delete") {
    deleteEmployeePermanently(face);
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
  if (userEditShiftSelect) {
    renderShiftOptions();
    userEditShiftSelect.value = face.shift_code || "";
  }
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
    shift_code: String(form.get("shift_code") || "").trim() || null,
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

async function deleteEmployeePermanently(face) {
  const confirmed = window.confirm(
    `¿Eliminar definitivamente a ${face.name} (${face.person_id})?\n\n` +
      "Se borrara TODO: rostro, embeddings, fotos, marcas de asistencia e incidencias.\n" +
      "Esta accion no se puede deshacer.",
  );
  if (!confirmed) return;

  const typed = window.prompt(
    `Escribe ELIMINAR para confirmar la eliminacion de ${face.name}:`,
    "",
  );
  if (typed?.trim().toUpperCase() !== "ELIMINAR") {
    showToast("Eliminacion cancelada.", 4000, "info");
    return;
  }

  try {
    showToast("Eliminando usuario...", 5000, "info");
    const data = await requestJson(
      `/api/v1/faces/employees/${encodeURIComponent(face.person_id)}`,
      { method: "DELETE" },
    );
    state.faces = state.faces.filter((item) => item.person_id !== face.person_id);
    delete state.facePhotoVersions[face.person_id];
    state.facesFingerprint = "";
    renderRegisteredUsers();
    updateFacesCountLabel();
    await Promise.all([refreshEvents(), refreshIncidents()]);
    showToast(data.message || "Usuario eliminado definitivamente", 6000, "success");
  } catch (error) {
    showToast(parseApiError(error), 7000, "error");
    await refreshFaces();
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
  const sortedEvents = getSortedEvents(state.events);
  const todayEvents = sortedEvents.filter(isTodayEvent);
  const todayCheckIns = todayEvents.filter((event) => event.event_type === "check_in").length;
  const todayCheckOuts = todayEvents.filter((event) => event.event_type === "check_out").length;
  const activeFaces = (state.faces || []).filter((face) => face.is_active !== false).length;
  const recentTotal = state.events.length;
  const devices = state.admin?.devices || [];
  const activeDevices = devices.filter((device) => device.is_active !== false);
  const onlineDevices = activeDevices.filter((device) => device.online);
  const cameraDeviceId = state.admin?.settings?.camera_device_id || "dashboard-camera-001";

  setText("#metric-events", todayEvents.length);
  setText("#metric-events-sub", `Total reciente: ${recentTotal}`);
  setText("#metric-incidents", state.incidents.length);
  setText("#metric-incidents-sub", state.incidents.length === 1 ? "Caso abierto" : "Casos abiertos");
  setText("#metric-faces", activeFaces);
  setText("#metric-faces-sub", `Total perfiles: ${state.faces.length}`);
  setText("#metric-device", devices.length ? `${onlineDevices.length}/${activeDevices.length}` : "--");
  setText("#metric-device-sub", devices.length ? "Online / activos" : cameraDeviceId);

  const lastSyncLabel = state.lastSyncAt
    ? `Actualizado ${state.lastSyncAt.toLocaleTimeString()}`
    : "Sin sincronizar";
  setText("#last-sync", lastSyncLabel);

  const latestEvent = sortedEvents[0];
  const mainStatus = document.querySelector("#overview-main-status");
  const mainDetail = document.querySelector("#overview-main-detail");
  if (mainStatus) {
    mainStatus.textContent = todayEvents.length
      ? `${todayEvents.length} marca(s) registradas hoy`
      : "Sin marcas registradas hoy";
  }
  if (mainDetail) {
    mainDetail.textContent = latestEvent
      ? `Ultima marca recibida: ${eventTypeLabel(latestEvent.event_type)} de ${latestEvent.employee_name || latestEvent.person_id} el ${formatDate(latestEvent.captured_at)}.`
      : "El panel se actualiza automaticamente cada 30 segundos.";
  }

  renderOverviewInsights({
    todayEvents,
    todayCheckIns,
    todayCheckOuts,
    activeFaces,
    latestEvent,
    onlineDevices,
    activeDevices,
  });
}

function setText(selector, value) {
  const node = document.querySelector(selector);
  if (node) node.textContent = String(value);
}

function getSortedEvents(events) {
  return (events || [])
    .slice()
    .sort((a, b) => eventTimestamp(b) - eventTimestamp(a));
}

function eventTimestamp(event) {
  const date = event?.captured_at ? new Date(event.captured_at) : null;
  return date && !Number.isNaN(date.getTime()) ? date.getTime() : 0;
}

function isTodayEvent(event) {
  return dateKeyLocal(event?.captured_at) === dateKeyLocal(new Date());
}

function dateKeyLocal(value) {
  const date = value instanceof Date ? value : new Date(value);
  if (!date || Number.isNaN(date.getTime())) return "";
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

function renderOverviewInsights(summary) {
  const container = document.querySelector("#overview-insights");
  if (!container) return;
  const latestDetail = summary.latestEvent
    ? `${summary.latestEvent.employee_name || summary.latestEvent.person_id} - ${formatDate(summary.latestEvent.captured_at)}`
    : "Aun no hay marcas cargadas";
  const deviceDetail = summary.activeDevices.length
    ? `${summary.onlineDevices.length} online de ${summary.activeDevices.length} activo(s)`
    : "Registra dispositivos para medir actividad";
  const insights = [
    {
      tone: summary.todayEvents.length ? "ok" : "warn",
      title: summary.todayEvents.length ? "Operacion activa hoy" : "Sin actividad de hoy",
      detail: summary.todayEvents.length
        ? `${summary.todayCheckIns} entrada(s) y ${summary.todayCheckOuts} salida(s).`
        : "Los registros visibles pertenecen a dias anteriores.",
    },
    {
      tone: summary.activeFaces ? "ok" : "bad",
      title: "Base facial",
      detail: `${summary.activeFaces} rostro(s) activo(s) para reconocimiento.`,
    },
    {
      tone: summary.onlineDevices.length ? "ok" : "warn",
      title: "Dispositivos",
      detail: deviceDetail,
    },
    {
      tone: summary.latestEvent && isTodayEvent(summary.latestEvent) ? "ok" : "info",
      title: "Ultima marca",
      detail: latestDetail,
    },
  ];
  container.innerHTML = insights
    .map((item) => `
      <article class="insight ${item.tone}">
        <span></span>
        <div>
          <strong>${escapeHtml(item.title)}</strong>
          <small>${escapeHtml(item.detail)}</small>
        </div>
      </article>
    `)
    .join("");
}

function eventTypeLabel(eventType) {
  return eventType === "check_out" ? "Salida" : "Entrada";
}

function buildEventListMarkup(events, emptyCopy) {
  if (!events.length) {
    return {
      className: "event-list empty",
      html: `
        <div class="empty-state">
          <span class="empty-icon">${emptyCopy.icon}</span>
          <p>${emptyCopy.title}</p>
          <small>${emptyCopy.subtitle}</small>
        </div>`,
    };
  }
  return {
    className: "event-list",
    html: getSortedEvents(events)
      .slice(0, 12)
      .map((event) => {
        const status = event.duplicate ? "Duplicado" : (event.work_status_label || "Aceptado");
        const badge = event.duplicate || event.work_status === "late"
          ? "warn"
          : (event.work_status === "early_exit" ? "bad" : "ok");
        const typeClass = event.event_type === "check_out" ? "check-out" : "check-in";
        const source = event.source ? ` | ${escapeHtml(event.source)}` : "";
        const shift = event.shift_code ? ` | Turno ${escapeHtml(event.shift_code)}` : " | Sin turno";
        return `
          <article class="event-item">
            <div>
              <strong>${escapeHtml(event.employee_name || event.person_id)}</strong>
              <small>
                <span class="event-type ${typeClass}">${eventTypeLabel(event.event_type)}</span>
                | ${escapeHtml(event.device_id)}${source}${shift} | ${formatDate(event.captured_at)}
              </small>
            </div>
            <span class="badge ${badge}">${escapeHtml(status)}</span>
          </article>
        `;
      })
      .join(""),
  };
}

function renderEvents() {
  const overview = buildEventListMarkup(state.events, {
    icon: "&#9638;",
    title: "Sin eventos todavia",
    subtitle: "Las marcas apareceran aqui al escanear con reconocimiento facial",
  });
  const container = document.querySelector("#recent-events");
  if (container) {
    container.className = overview.className;
    container.innerHTML = overview.html;
  }

  const live = buildEventListMarkup(state.events, {
    icon: "&#9673;",
    title: "Sin marcas biometricas todavia",
    subtitle: "Inicia el escaner facial para registrar la primera entrada",
  });
  const liveContainer = document.querySelector("#attendance-live-events");
  if (liveContainer) {
    liveContainer.className = live.className;
    liveContainer.innerHTML = live.html;
  }
  renderAttendanceOps();
}

function renderAttendanceOps() {
  let checkIns = 0;
  let checkOuts = 0;
  for (const event of state.events) {
    if (!isTodayEvent(event)) continue;
    if (event.event_type === "check_in") checkIns += 1;
    if (event.event_type === "check_out") checkOuts += 1;
  }
  const checkinsNode = document.querySelector("#attendance-checkins-today");
  const checkoutsNode = document.querySelector("#attendance-checkouts-today");
  const facesNode = document.querySelector("#attendance-faces-active");
  if (checkinsNode) checkinsNode.textContent = String(checkIns);
  if (checkoutsNode) checkoutsNode.textContent = String(checkOuts);
  if (facesNode) {
    const activeFaces = (state.faces || []).filter((face) => face.is_active !== false).length;
    facesNode.textContent = String(activeFaces);
  }
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

async function startRegisterFaceScan() {
  if (state.registerInProgress || state.registerScanStarting || state.registerScanner?.running) {
    return;
  }
  state.registerScanStarting = true;

  setRegisterStatus("loading", "Iniciando escaneo...", "Preparando camara e inteligencia artificial");
  showToast("Iniciando escaneo facial...", 3000, "info");
  if (registerStartScanBtn) registerStartScanBtn.disabled = true;
  registerStatus?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  document.querySelector(".register-camera-wrap")?.scrollIntoView({ behavior: "smooth", block: "center" });

  if (!window.RegisterFaceScanner) {
    setRegisterStatus("error", "Escanner no listo", "Recarga con Ctrl+Shift+R (recarga forzada).");
    showToast("El escaner no cargo. Recarga forzada: Ctrl+Shift+R.", 7000, "error");
    if (registerStartScanBtn) registerStartScanBtn.disabled = false;
    state.registerScanStarting = false;
    return;
  }

  const cameraBlocked = getCameraBlockedReason();
  if (cameraBlocked) {
    setRegisterStatus("error", "Camara bloqueada", cameraBlocked);
    showToast(cameraBlocked, 9000, "error");
    renderCameraSecurityBanners();
    if (registerStartScanBtn) registerStartScanBtn.disabled = false;
    state.registerScanStarting = false;
    return;
  }

  const formEl = faceRegisterForm;
  if (!formEl) {
    showToast("Formulario de registro no encontrado.", 5000, "error");
    if (registerStartScanBtn) registerStartScanBtn.disabled = false;
    state.registerScanStarting = false;
    return;
  }

  const areaCode = String(new FormData(formEl).get("area_code") || "").trim();
  const positionCode = String(new FormData(formEl).get("position_code") || "").trim();
  const name = String(new FormData(formEl).get("name") || "").trim();
  if (!areaCode || !positionCode) {
    setRegisterStatus("error", "Faltan datos", "Selecciona area y cargo.");
    showToast("Selecciona area y cargo antes de escanear.", 4000, "error");
    if (registerStartScanBtn) registerStartScanBtn.disabled = false;
    state.registerScanStarting = false;
    return;
  }
  if (!registerEmployeeCodeInput?.value?.trim()) {
    await refreshRegisterEmployeeCode();
  }
  state.registerExpectedCode = registerEmployeeCodeInput?.value?.trim() || "";
  if (!name) {
    setRegisterStatus("error", "Faltan datos", "Ingresa el nombre del colaborador.");
    showToast("Ingresa el nombre del colaborador.", 4000, "error");
    if (registerStartScanBtn) registerStartScanBtn.disabled = false;
    state.registerScanStarting = false;
    return;
  }

  const backendOk = document.querySelector("#api-status-dot")?.classList.contains("ok");
  if (!backendOk) {
    await refreshHealth();
    if (!document.querySelector("#api-status-dot")?.classList.contains("ok")) {
      setRegisterStatus(
        "error",
        "Sin conexion al backend",
        "Inicia uvicorn en puerto 8000. API debe ser http://127.0.0.1:8000",
      );
      showToast("Backend sin conexion. Inicia uvicorn y pulsa Actualizar.", 7000, "error");
      if (registerStartScanBtn) registerStartScanBtn.disabled = false;
      state.registerScanStarting = false;
      return;
    }
  }

  state.registerScanComplete = false;
  state.registerCaptureBlobs = null;
  pauseBackgroundRefresh(true);
  stopRegisterScanner();
  state.registerScanner = new window.RegisterFaceScanner({
    video: registerCameraPreview,
    canvas: registerCameraMesh,
    circleEl: registerFaceCircle,
    stepLabelEl: registerScanStep,
    hintEl: registerScanHint,
    progressEl: registerScanProgress,
    apiBase: apiBase(),
    onSpeak: (message) => speak(message),
    onStatus: (mode, title, detail) => setRegisterStatus(mode, title, detail),
    onStepCaptured: () => {
      if (registerFilesSummary) {
        registerFilesSummary.className = "register-files-summary ok";
        registerFilesSummary.textContent = "Capturas en progreso. Mantente dentro del circulo.";
      }
    },
    onComplete: async (captures) => {
      state.registerScanComplete = true;
      state.registerCaptureBlobs = captures;
      if (faceRegisterForm) {
        state.registerScanner?.applyCapturesToForm(faceRegisterForm);
        updateRegisterFilesSummary(faceRegisterForm);
      }
      registerStartScanBtn?.classList.add("hidden");
      faceRegisterSubmit?.classList.remove("hidden");
      stopRegisterScanner();
      try {
        await submitFaceRegisterFromScan(faceRegisterForm);
      } catch (error) {
        const message = parseApiError(error);
        setRegisterStatus("error", "No se pudo guardar el perfil", message);
        showToast(message, 8000, "error");
      }
    },
  });

  try {
    await state.registerScanner.startCamera();
    setRegisterStatus(
      "loading",
      "Validando rostro vivo",
      "Parpadeo, giro de cabeza y anti-spoofing antes del perfil",
    );
    const liveness = await runRegisterLivenessChallenge();
    if (!liveness?.passed) {
      const msg =
        liveness?.message ||
        "No se valido que seas una persona real. No uses fotos ni pantallas.";
      setRegisterStatus("error", "Rostro no validado", msg);
      showToast(msg, 8000, "error");
      stopRegisterScanner();
      pauseBackgroundRefresh(false);
      return;
    }
    setRegisterStatus(
      "success",
      "Rostro vivo validado",
      "Ahora capturaremos frontal, izquierda y derecha para tu perfil.",
    );
    showToast("Prueba de vida superada. Continua con las 3 poses.", 4000, "success");
    speak("Rostro validado. Ahora las tres poses del registro.");
    await sleep(600);
    await state.registerScanner.beginPoseScan();
  } catch (error) {
    const message = error?.message || "Revisa permisos de camara.";
    setRegisterStatus("error", "No se pudo escanear", message);
    showToast(message, 7000, "error");
    stopRegisterScanner();
    pauseBackgroundRefresh(false);
  } finally {
    if (!state.registerScanner?.running) {
      if (registerStartScanBtn) registerStartScanBtn.disabled = false;
      state.registerScanStarting = false;
    }
  }
}

window.__startRegisterFaceScanReady = startRegisterFaceScan;
window.startRegisterFaceScan = startRegisterFaceScan;
console.info("[IA Facial] app.js listo — escaneo facial disponible");

function stopRegisterScanner() {
  state.registerScanner?.stop();
  state.registerScanner = null;
  registerFaceCircle?.classList.remove("aligned", "scanning");
}

async function submitFaceRegisterFromScan(formEl) {
  if (!formEl) return;
  const fakeEvent = { preventDefault() {}, currentTarget: formEl };
  await submitFaceRegister(fakeEvent, { fromScanner: true });
}

async function submitFaceRegister(event, options = {}) {
  event.preventDefault();
  if (state.registerInProgress) {
    showToast("Registro en curso. Espera a que termine la IA.", 4000, "info");
    return;
  }

  const formEl = event.currentTarget;
  const fromScanner = options.fromScanner === true;

  const validationError = validateRegisterForm(formEl, {
    fromScanner,
    captureBlobs: fromScanner ? state.registerCaptureBlobs : null,
  });
  if (validationError) {
    setRegisterStatus("error", "No se pudo guardar", validationError);
    showToast(validationError, 6000, "error");
    registerStatus?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    pauseBackgroundRefresh(false);
    return;
  }

  if (!document.querySelector("#api-status-dot")?.classList.contains("ok")) {
    const offlineMsg = "Backend sin conexion. Inicia uvicorn en el puerto 8000 y pulsa Actualizar.";
    setRegisterStatus("error", "Sin conexion", offlineMsg);
    showToast(offlineMsg, 6000, "error");
    return;
  }

  const form = buildRegisterFormPayload(
    formEl,
    fromScanner ? state.registerCaptureBlobs : null,
  );
  const expectedCode = state.registerExpectedCode || registerEmployeeCodeInput?.value?.trim() || "";
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
    const duplicateFace = isDuplicateFaceError(error);
    const spoofBlocked = isSpoofBlockedError(error);
    if (!duplicateFace && !spoofBlocked) {
      const recovered = await recoverRegisterIfSaved(expectedCode);
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
    }

    if (!duplicateFace && !spoofBlocked && isTransientNetworkError(error)) {
      setRegisterStatus(
        "loading",
        "Reintentando conexion...",
        "La red se interrumpio. Reintentando una vez (no pulses de nuevo).",
      );
      await sleep(2500);
      try {
        const retryForm = buildRegisterFormPayload(
          formEl,
          fromScanner ? state.registerCaptureBlobs : null,
        );
        const data = await requestForm("/api/v1/faces/register-profile", retryForm, {
          silent: true,
          timeoutMs: 300_000,
        });
        await handleRegisterSuccess(data, formEl);
        return;
      } catch (retryError) {
        const recoveredAfterRetry = await recoverRegisterIfSaved(expectedCode);
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
      duplicateFace
        ? "Rostro ya registrado"
        : spoofBlocked
          ? "Rostro no validado"
          : "Conexion interrumpida",
      duplicateFace
        ? `${message} Usa el perfil existente o eliminalo antes de volver a registrar.`
        : spoofBlocked
          ? `${message} Escanea en vivo con la camara de este equipo, sin fotos ni pantallas.`
          : `${message} Si ves el JSON de exito abajo, el perfil puede estar guardado. Revisa Usuarios.`,
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
  speak(`Perfil facial de ${data.name} guardado correctamente.`, { priority: true });
  state.registerScanComplete = false;
  state.registerCaptureBlobs = null;
  state.registerExpectedCode = "";
  state.lastRegisteredPersonId = data.person_id || null;
  registerStartScanBtn?.classList.remove("hidden");
  faceRegisterSubmit?.classList.add("hidden");
  formEl.reset();
  resetRegisterHierarchyFields();
  updateRegisterFilesSummary(formEl);
  await refreshFaces();
  await refreshScheduleOverview(true);
  await refreshRegisterEmployeeCode();
  pauseBackgroundRefresh(false);
  openDashboardView("users");
  if (state.lastRegisteredPersonId) {
    window.setTimeout(() => highlightRegisteredUser(state.lastRegisteredPersonId), 450);
  }
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

async function initEmployeeCatalog() {
  if (state.employeeCatalog?.areas?.length) {
    renderRegisterAreaOptions();
    return state.employeeCatalog;
  }
  const data = await requestJson("/api/v1/employees/catalog");
  state.employeeCatalog = data;
  renderRegisterAreaOptions();
  return data;
}

function renderRegisterAreaOptions() {
  if (!registerAreaSelect || !state.employeeCatalog?.areas) return;
  const current = registerAreaSelect.value;
  registerAreaSelect.innerHTML = [
    '<option value="">Selecciona un area...</option>',
    ...state.employeeCatalog.areas.map(
      (area) => `<option value="${escapeHtml(area.code)}">${escapeHtml(area.name)} (${escapeHtml(area.code)})</option>`,
    ),
  ].join("");
  if (current) {
    registerAreaSelect.value = current;
    handleRegisterAreaChange();
  }
}

function handleRegisterAreaChange() {
  if (!registerPositionSelect || !state.employeeCatalog?.positions) return;
  const areaCode = registerAreaSelect?.value || "";
  const positions = state.employeeCatalog.positions.filter((item) => item.area_code === areaCode);
  if (!areaCode || !positions.length) {
    registerPositionSelect.innerHTML = '<option value="">Primero elige un area...</option>';
    registerPositionSelect.disabled = true;
    registerPositionSelect.value = "";
    clearRegisterEmployeeCode();
    return;
  }
  registerPositionSelect.disabled = false;
  registerPositionSelect.innerHTML = [
    '<option value="">Selecciona un cargo...</option>',
    ...positions.map(
      (position) =>
        `<option value="${escapeHtml(position.code)}">${escapeHtml(position.name)} (${escapeHtml(position.code)})</option>`,
    ),
  ].join("");
  registerPositionSelect.value = "";
  clearRegisterEmployeeCode();
}

async function refreshRegisterEmployeeCode() {
  const areaCode = registerAreaSelect?.value || "";
  const positionCode = registerPositionSelect?.value || "";
  if (!areaCode || !positionCode) {
    clearRegisterEmployeeCode();
    return null;
  }
  try {
    const data = await requestJson(
      `/api/v1/employees/next-code?area_code=${encodeURIComponent(areaCode)}&position_code=${encodeURIComponent(positionCode)}`,
    );
    if (registerEmployeeCodeInput) {
      registerEmployeeCodeInput.value = data.employee_code;
      registerEmployeeCodeInput.classList.add("ready");
    }
    state.registerExpectedCode = data.employee_code;
    return data;
  } catch (error) {
    clearRegisterEmployeeCode();
    showToast(parseApiError(error), 5000, "error");
    return null;
  }
}

function clearRegisterEmployeeCode() {
  if (registerEmployeeCodeInput) {
    registerEmployeeCodeInput.value = "";
    registerEmployeeCodeInput.classList.remove("ready");
  }
  state.registerExpectedCode = "";
}

function resetRegisterHierarchyFields() {
  if (registerAreaSelect) registerAreaSelect.value = "";
  if (registerShiftSelect) registerShiftSelect.value = "";
  handleRegisterAreaChange();
  clearRegisterEmployeeCode();
}

function validateRegisterForm(formEl, options = {}) {
  const areaCode = getRegisterFieldValue(formEl, "area_code");
  const positionCode = getRegisterFieldValue(formEl, "position_code");
  const name = getRegisterFieldValue(formEl, "name");
  if (!areaCode || !positionCode) return "Selecciona area y cargo.";
  if (!name) return "Ingresa el nombre del colaborador.";

  const requiredFiles = [
    { name: "front", label: "frontal" },
    { name: "left", label: "giro izquierda" },
    { name: "right", label: "giro derecha" },
  ];
  const captureBlobs = options.captureBlobs;
  const missing = requiredFiles.filter(({ name: fieldName }) => {
    if (captureBlobs && captureBlobs[fieldName]) return false;
    const input = formEl.querySelector(`input[name="${fieldName}"]`);
    return !input?.files?.length;
  });
  if (missing.length) {
    if (options.fromScanner) {
      return "El escaneo no completo las 3 poses. Pulsa Iniciar escaneo facial otra vez.";
    }
    return `Faltan capturas obligatorias: ${missing.map((item) => item.label).join(", ")}. Usa Iniciar escaneo facial.`;
  }
  return null;
}

function getRegisterFieldValue(formEl, name) {
  const control = formEl.elements.namedItem(name);
  if (control && "value" in control) {
    return String(control.value || "").trim();
  }
  return String(new FormData(formEl).get(name) || "").trim();
}

function buildRegisterFormPayload(formEl, captureBlobs = null) {
  const form = new FormData();
  form.append("area_code", getRegisterFieldValue(formEl, "area_code"));
  form.append("position_code", getRegisterFieldValue(formEl, "position_code"));
  form.append("name", getRegisterFieldValue(formEl, "name"));

  const shiftCode = getRegisterFieldValue(formEl, "shift_code");
  if (shiftCode) form.append("shift_code", shiftCode);

  const email = getRegisterFieldValue(formEl, "email");
  if (email) form.append("email", email);

  const poseFields = ["front", "left", "right"];
  for (const field of poseFields) {
    const blob = captureBlobs?.[field];
    if (blob instanceof Blob) {
      form.append(field, blob, `${field}.jpg`);
      continue;
    }
    const input = formEl.querySelector(`input[name="${field}"]`);
    const file = input?.files?.[0];
    if (file) form.append(field, file, file.name || `${field}.jpg`);
  }

  return form;
}

function highlightRegisteredUser(personId) {
  const container = document.querySelector("#registered-users");
  if (!container) return;
  container.querySelectorAll(".user-card.highlight-new").forEach((card) => {
    card.classList.remove("highlight-new");
  });
  const card = container.querySelector(`.user-card[data-person-id="${personId}"]`);
  if (!card) return;
  card.classList.add("highlight-new");
  card.scrollIntoView({ behavior: "smooth", block: "center" });
  window.setTimeout(() => card.classList.remove("highlight-new"), 6000);
}

function handleRegisterFormChange(event) {
  const target = event.target;
  if (target instanceof HTMLSelectElement) {
    return;
  }
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
  const labels = {
    front: "frontal",
    left: "izquierda",
    right: "derecha",
  };

  const picked = required.filter((field) => {
    const input = formEl.querySelector(`input[name="${field}"]`);
    return input?.files?.length;
  });

  if (!picked.length) {
    registerFilesSummary.className = "register-files-summary";
    registerFilesSummary.textContent =
      "Pulsa Iniciar escaneo facial. El sistema capturara frontal, izquierda y derecha automaticamente.";
    return;
  }

  if (picked.length < required.length) {
    const missing = required.filter((field) => !picked.includes(field));
    registerFilesSummary.className = "register-files-summary warn";
    registerFilesSummary.textContent = `Faltan capturas: ${missing.map((f) => labels[f]).join(", ")}.`;
    return;
  }

  registerFilesSummary.className = "register-files-summary ok";
  registerFilesSummary.textContent = `Capturas listas: ${picked.map((f) => labels[f]).join(", ")}.`;
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
    if (el.id === "register-employee-code") return;
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

function isDuplicateFaceError(error) {
  const message = parseApiError(error).toLowerCase();
  return message.includes("ya esta registrado") || message.includes("ya está registrado");
}

function isSpoofBlockedError(error) {
  const message = parseApiError(error).toLowerCase();
  return (
    message.includes("rostro humano en vivo") ||
    message.includes("anti-spoof") ||
    message.includes("fotos, pantallas")
  );
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
  movement: { prepMs: 1500, countdownSec: 2, actionCue: "turnNow", burst: false },
  blink: { prepMs: 700, countdownSec: 0, actionCue: null, burst: false },
  smile: { prepMs: 1400, countdownSec: 2, actionCue: "smileNow", burst: true },
};
const SPEECH_PHRASES = {
  front: "Mira de frente a la camara, con buena luz.",
  movement: "Gira un poco la cabeza hacia un lado.",
  blink: "Mira a la camara. Parpadea de forma natural cuando estes listo.",
  smile: "Prepárate. En un momento debes sonreir.",
  turnNow: "Gira la cabeza ahora.",
  blinkNow: "Parpadea ahora.",
  smileNow: "Sonrie ahora.",
  validate: "Validando identidad. Espera un momento por favor.",
  welcome: "Camara lista. Elige entrada o salida y escanea cuando estes preparado.",
  noMatch: "No te reconoci. Acercate un poco, mira de frente y vuelve a intentar.",
  scanError: "Hubo un error al escanear. Revisa que el servidor este activo.",
  saveError: "Te reconoci, pero no pude guardar la asistencia. Intenta otra vez.",
};
const COUNTDOWN_WORDS = ["", "uno", "dos", "tres", "cuatro", "cinco"];
const LIVENESS_ACTION_HOLD_MS = 400;
const LIVENESS_BURST_INTERVAL_MS = 180;
const CAMERA_FRAME_QUALITY = 0.9;

function setLivenessOverlayText(text) {
  if (scanOverlay) scanOverlay.textContent = text;
  setCameraStatus(text);
}

async function countdownWithActionCue(seconds, actionCueKey) {
  for (let remaining = seconds; remaining >= 1; remaining -= 1) {
    const isActionSecond = actionCueKey && remaining === 1;
    const spokenAction = actionCueKey ? (SPEECH_PHRASES[actionCueKey] || actionCueKey) : null;
    const label = isActionSecond ? spokenAction : `Captura en ${remaining}...`;
    setLivenessOverlayText(label);
    if (isActionSecond) {
      speak(spokenAction, { priority: true });
    } else if (remaining <= 3) {
      speak(COUNTDOWN_WORDS[remaining] || String(remaining), { rate: 0.95 });
    }
    await sleep(1000);
  }
}

function speechForLivenessStep(stepType) {
  return SPEECH_PHRASES[stepType] || null;
}

async function captureLivenessStep(step) {
  if (step.type === "blink" && window.captureBlinkOnLiveClose && cameraPreview?.videoWidth) {
    const spokenIntro = speechForLivenessStep(step.type) || step.prompt;
    setScanResult("scanning", step.prompt, "Detectando parpadeo en vivo...");
    setLivenessOverlayText("Mira a la camara con ojos abiertos");
    speak(spokenIntro);
    await sleep(700);
    try {
      return await window.captureBlinkOnLiveClose({
        video: cameraPreview,
        captureFrame: captureCameraFrame,
        onStatus: setLivenessOverlayText,
      });
    } catch (error) {
      console.warn("Parpadeo en vivo fallo, usando captura de respaldo:", error);
      setLivenessOverlayText("Reintento: parpadea ahora...");
      speak(SPEECH_PHRASES.blinkNow, { priority: true });
      await sleep(400);
      return window.captureBlinkBurstPickClosed(
        cameraPreview,
        captureCameraFrame,
        8,
        110,
      );
    }
  }

  const timing = LIVENESS_STEP_TIMING[step.type] || LIVENESS_STEP_TIMING.front;
  const spokenIntro = speechForLivenessStep(step.type) || step.prompt;
  setScanResult("scanning", step.prompt, "Preparate, la captura es automatica...");
  setLivenessOverlayText(step.prompt);
  speak(spokenIntro);
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

async function captureRegisterCameraFrame() {
  const video = registerCameraPreview;
  if (!video?.videoWidth || !video?.videoHeight) {
    return null;
  }
  const maxWidth = 960;
  const scale = Math.min(1, maxWidth / video.videoWidth);
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(video.videoWidth * scale);
  canvas.height = Math.round(video.videoHeight * scale);
  const ctx = canvas.getContext("2d");
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = "high";
  ctx.translate(canvas.width, 0);
  ctx.scale(-1, 1);
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  return new Promise((resolve) => {
    canvas.toBlob((blob) => resolve(blob), "image/jpeg", CAMERA_FRAME_QUALITY);
  });
}

async function captureRegisterLivenessStep(step) {
  if (step.type === "blink" && window.captureBlinkOnLiveClose && registerCameraPreview?.videoWidth) {
    const spokenIntro = speechForLivenessStep(step.type) || step.prompt;
    setRegisterStatus("loading", step.prompt, "Detectando parpadeo en vivo...");
    if (registerScanHint) registerScanHint.textContent = "Mira a la camara con ojos abiertos";
    speak(spokenIntro);
    await sleep(700);
    try {
      return await window.captureBlinkOnLiveClose({
        video: registerCameraPreview,
        captureFrame: captureRegisterCameraFrame,
        onStatus: (text) => {
          if (registerScanHint) registerScanHint.textContent = text;
        },
      });
    } catch (error) {
      console.warn("Parpadeo en vivo (registro) fallo, respaldo:", error);
      if (registerScanHint) registerScanHint.textContent = "Reintento: parpadea ahora...";
      speak(SPEECH_PHRASES.blinkNow, { priority: true });
      await sleep(400);
      return window.captureBlinkBurstPickClosed?.(
        registerCameraPreview,
        captureRegisterCameraFrame,
        8,
        110,
      ) ?? captureRegisterCameraFrame();
    }
  }

  const timing = LIVENESS_STEP_TIMING[step.type] || LIVENESS_STEP_TIMING.front;
  const spokenIntro = speechForLivenessStep(step.type) || step.prompt;
  setRegisterStatus("loading", step.prompt, "Preparate, la captura es automatica...");
  if (registerScanHint) registerScanHint.textContent = step.prompt;
  speak(spokenIntro);
  await sleep(timing.prepMs);
  await countdownWithActionCue(timing.countdownSec, timing.actionCue);
  if (timing.actionCue) {
    await sleep(LIVENESS_ACTION_HOLD_MS);
  }
  if (registerScanHint) registerScanHint.textContent = "Capturando...";
  if (timing.burst) {
    return captureRegisterCameraBurst(2, LIVENESS_BURST_INTERVAL_MS);
  }
  await sleep(250);
  return captureRegisterCameraFrame();
}

async function captureRegisterCameraBurst(count = 2, intervalMs = 180) {
  let lastBlob = null;
  for (let index = 0; index < count; index += 1) {
    const blob = await captureRegisterCameraFrame();
    if (blob) lastBlob = blob;
    if (index < count - 1) await sleep(intervalMs);
  }
  return lastBlob;
}

async function runRegisterLivenessChallenge() {
  const challenge = await requestJson("/api/v1/faces/liveness/challenge");
  const form = new FormData();
  form.append("challenge_id", challenge.challenge_id || "");

  for (let index = 0; index < challenge.steps.length; index += 1) {
    const step = challenge.steps[index];
    setRegisterStatus(
      "loading",
      `Prueba de vida ${index + 1}/${challenge.steps.length}`,
      step.prompt,
    );
    const blob = await captureRegisterLivenessStep(step);
    if (!blob) {
      throw new Error("La camara no capturo imagen. Espera un momento e intenta de nuevo.");
    }
    form.append(step.form_field, blob, `${step.form_field}.jpg`);
    await sleep(250);
  }

  setRegisterStatus("loading", "Validando rostro real...", "Anti-spoofing en el servidor...");
  if (registerScanHint) registerScanHint.textContent = "Validando rostro real...";
  speak(SPEECH_PHRASES.validate);
  return requestForm("/api/v1/faces/liveness/verify", form, {
    silent: true,
    timeoutMs: 300_000,
  });
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
  speak(SPEECH_PHRASES.validate);
  return requestForm("/api/v1/faces/liveness/verify", form, {
    silent: true,
    timeoutMs: 300_000,
  });
}

async function startCamera() {
  if (state.camera.stream) return;

  const blockedReason = getCameraBlockedReason();
  if (blockedReason) {
    setCameraStatus(blockedReason);
    setScanResult("bad", "Camara bloqueada por el navegador", blockedReason);
    showToast(blockedReason, 9000, "error");
    renderCameraSecurityBanners();
    return;
  }

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
    const meshReady = await startScanFaceMesh();
    setScanResult("idle", "Camara lista", "Elige Entrada o Salida y pulsa el boton correspondiente.");
    setCameraStatus(
      meshReady
        ? "Camara activa con malla MediaPipe (puntos azules). Selecciona Entrada o Salida."
        : "Camara activa. MediaPipe no cargo; el escaneo sigue funcionando sin puntos azules.",
    );
    await refreshAttendancePolicy();
    warmUpSpeech();
    speak(`${getWelcomeSpeech()} ${SPEECH_PHRASES.welcome}`);
    if (autoScanInput?.checked) {
      startAutoScan();
    }
  } catch (error) {
    const message = describeCameraError(error);
    setCameraStatus(message);
    setScanResult("bad", "No se pudo abrir la camara", message);
    showToast(message, 9000, "error");
    renderCameraSecurityBanners();
  }
}

function isCameraSecureContext() {
  if (window.isSecureContext) return true;
  const host = window.location.hostname;
  return host === "localhost" || host === "127.0.0.1" || host === "[::1]";
}

function getCameraBlockedReason() {
  if (!navigator.mediaDevices?.getUserMedia) {
    return "Tu navegador no permite acceso a la camara web.";
  }
  if (!isCameraSecureContext()) {
    return `La camara exige HTTPS. Estas en ${window.location.origin} (HTTP). Abre el panel con https:// o usa localhost en tu PC.`;
  }
  return null;
}

function describeCameraError(error) {
  const name = String(error?.name || "");
  const msg = String(error?.message || error || "").toLowerCase();
  if (name === "NotAllowedError" || msg.includes("permission") || msg.includes("denied")) {
    return "Permiso de camara denegado. Pulsa el candado junto a la URL, permite Camara y recarga.";
  }
  if (name === "NotFoundError" || msg.includes("not found") || msg.includes("devices")) {
    return "No se detecto ninguna camara conectada.";
  }
  if (name === "NotReadableError" || msg.includes("not readable") || msg.includes("could not start")) {
    return "La camara esta en uso por otra app (Teams, Zoom, etc.). Cierrala e intenta de nuevo.";
  }
  if (name === "SecurityError" || msg.includes("secure") || msg.includes("insecure")) {
    return getCameraBlockedReason() || "Contexto no seguro: la camara requiere HTTPS.";
  }
  const insecure = getCameraBlockedReason();
  if (insecure) return insecure;
  return error?.message || "No se pudo abrir la camara.";
}

function renderCameraSecurityBanners() {
  const reason = getCameraBlockedReason();
  document.querySelectorAll("[data-camera-security-banner]").forEach((banner) => {
    if (!reason) {
      banner.classList.add("hidden");
      banner.textContent = "";
      return;
    }
    banner.classList.remove("hidden");
    banner.textContent = reason;
  });
}

async function startScanFaceMesh() {
  if (!window.FaceMeshOverlay || !scanCameraMesh || !cameraPreview) return false;
  if (!state.camera.meshOverlay) {
    state.camera.meshOverlay = new window.FaceMeshOverlay(cameraPreview, scanCameraMesh);
  }
  return state.camera.meshOverlay.start();
}

function stopScanFaceMesh() {
  state.camera.meshOverlay?.stop();
}

function stopCamera() {
  stopAutoScan();
  stopScanFaceMesh();
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
        speak(speechForLivenessFailure(liveness), { priority: true });
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
      speak(`Identidad confirmada. Hola ${personName}.`, { priority: true });
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
      speak(SPEECH_PHRASES.noMatch, { priority: true });
    }
  } catch (error) {
    setScanResult("bad", "Error al escanear", "Revisa que el backend este activo");
    setCameraStatus("Error al escanear");
    showToast("Error al escanear. Mira consola o backend.", 5000);
    speak(SPEECH_PHRASES.scanError, { priority: true });
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
    device_id: state.admin?.settings?.camera_device_id || "dashboard-camera-001",
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
      speak(speechForAttendanceMessage(duplicateMessage, personName, eventType), { priority: true });
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
    speak(speechForAttendanceSuccess(personName, eventType), { priority: true });
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
    speak(SPEECH_PHRASES.saveError, { priority: true });
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
  // Espejo horizontal: misma orientacion que el preview y el registro facial.
  ctx.translate(cameraCanvas.width, 0);
  ctx.scale(-1, 1);
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
  if (dot) {
    dot.classList.toggle("ok", ok);
    dot.classList.toggle("bad", !ok);
  }
  if (label) {
    label.textContent = ok ? "Conectado" : "Sin conexion";
  }
  syncSettingsApiStatus();
}

async function probeApiConnection() {
  try {
    await requestJson("/api/v1/health", { timeoutMs: 8000 });
    setApiStatus(true);
    return true;
  } catch {
    setApiStatus(false);
    return false;
  }
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

function initSpeechSynthesis() {
  if (!("speechSynthesis" in window)) return;
  const loadVoices = () => {
    state.camera.preferredVoice = pickBestSpanishVoice();
    state.camera.speechReady = true;
  };
  loadVoices();
  window.speechSynthesis.addEventListener("voiceschanged", loadVoices);
}

function warmUpSpeech() {
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.getVoices();
  if (!state.camera.preferredVoice) {
    state.camera.preferredVoice = pickBestSpanishVoice();
  }
}

function pickBestSpanishVoice() {
  const voices = window.speechSynthesis.getVoices();
  if (!voices.length) return null;

  const preferredNames = [
    "helena",
    "sabina",
    "paulina",
    "monica",
    "laura",
    "elvira",
    "google español",
    "google spanish",
    "microsoft sabina",
    "microsoft helena",
  ];

  const scoreVoice = (voice) => {
    const name = voice.name.toLowerCase();
    const lang = (voice.lang || "").toLowerCase();
    let score = 0;
    if (lang.startsWith("es")) score += 40;
    if (lang.includes("mx") || lang.includes("es-es") || lang.includes("pe")) score += 12;
    if (voice.localService) score += 18;
    if (preferredNames.some((hint) => name.includes(hint))) score += 35;
    if (name.includes("neural") || name.includes("natural")) score += 20;
    if (name.includes("online")) score -= 8;
    return score;
  };

  const spanishVoices = voices
    .filter((voice) => (voice.lang || "").toLowerCase().startsWith("es"))
    .sort((a, b) => scoreVoice(b) - scoreVoice(a));

  return spanishVoices[0] || voices.find((voice) => voice.lang?.startsWith("es")) || null;
}

function humanizeSpeechText(message) {
  return String(message || "")
    .replace(/\s+/g, " ")
    .replace(/%/g, " por ciento")
    .replace(/EMP-/gi, "empleado ")
    .replace(/check_in|check-in/gi, "entrada")
    .replace(/check_out|check-out/gi, "salida")
    .replace(/anti-spoof(?:ing)?/gi, "validacion de rostro real")
    .replace(/liveness/gi, "prueba de vida")
    .replace(/backend/gi, "servidor")
    .replace(/:\s*/g, ". ")
    .trim();
}

function speechForLivenessFailure(liveness) {
  const checks = liveness?.checks || {};
  if (checks.blink === false) {
    return "No detecté el parpadeo. Cierra los ojos un instante y vuelve a intentar.";
  }
  if (checks.smile === false) {
    return "No detecté la sonrisa. Sonríe un poco o abre la boca y vuelve a intentar.";
  }
  if (checks.movement === false) {
    return "No detecté el giro de cabeza. Gira un poco hacia un lado y vuelve a intentar.";
  }
  if (checks.face_detected === false) {
    return "No vi tu rostro con claridad. Acércate, mejora la luz y vuelve a intentar.";
  }
  const raw = liveness?.message || "No se validó el rostro. Repite el escaneo.";
  return humanizeSpeechText(raw);
}

function speechForAttendanceSuccess(personName, eventType) {
  const name = personName || "colaborador";
  if (eventType === "check_out") {
    return `Listo ${name}. Tu salida quedó registrada correctamente.`;
  }
  return `Perfecto ${name}. Tu entrada quedó registrada correctamente.`;
}

function speechForAttendanceMessage(message, personName, eventType) {
  const text = humanizeSpeechText(message);
  if (text) return text;
  if (eventType === "check_out") {
    return `${personName}, ya registraste tu salida hoy.`;
  }
  return `${personName}, ya registraste tu entrada hoy. Si ya saliste, cambia a modo salida.`;
}

function stopSpeech() {
  if (!("speechSynthesis" in window)) return;
  state.camera.speechQueue = [];
  state.camera.speechBusy = false;
  window.speechSynthesis.cancel();
}

function speak(message, options = {}) {
  const { priority = false, rate = 0.92, pitch = 1, volume = 1 } = options;
  if (!state.camera.speakingEnabled || !("speechSynthesis" in window)) return Promise.resolve();
  const text = humanizeSpeechText(message);
  if (!text) return Promise.resolve();

  if (priority) {
    stopSpeech();
  }

  return new Promise((resolve) => {
    state.camera.speechQueue.push({ text, rate, pitch, volume, resolve });
    drainSpeechQueue();
  });
}

function drainSpeechQueue() {
  if (state.camera.speechBusy || !state.camera.speechQueue.length) return;
  if (!state.camera.speechReady) {
    warmUpSpeech();
  }

  const item = state.camera.speechQueue.shift();
  state.camera.speechBusy = true;

  const utterance = new SpeechSynthesisUtterance(item.text);
  utterance.lang = state.camera.preferredVoice?.lang || "es-MX";
  utterance.rate = item.rate;
  utterance.pitch = item.pitch;
  utterance.volume = item.volume;
  if (state.camera.preferredVoice) {
    utterance.voice = state.camera.preferredVoice;
  }

  utterance.onend = () => {
    state.camera.speechBusy = false;
    item.resolve();
    drainSpeechQueue();
  };
  utterance.onerror = () => {
    state.camera.speechBusy = false;
    item.resolve();
    drainSpeechQueue();
  };

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
