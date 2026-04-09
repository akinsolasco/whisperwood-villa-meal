const state = {
  baseUrl: "http://192.168.4.1:8080",
  summary: {},
  residents: [],
  devices: [],
  logs: [],
  selectedResidentId: null,
  selectedPairResidentId: null,
  selectedDeviceId: null,
};

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.ok === false) throw new Error(data.error || data.message || "Request failed");
  return data;
}

function setLoginError(msg = "") {
  $("loginError").textContent = msg;
}

function showApp() {
  $("loginView").classList.add("hidden");
  $("appView").classList.remove("hidden");
}

function showLogin() {
  $("appView").classList.add("hidden");
  $("loginView").classList.remove("hidden");
}

function renderSummary() {
  const cards = [
    ["Saved residents", state.summary.active_residents ?? 0],
    ["Known devices", state.summary.known_devices ?? 0],
    ["Paired devices", state.summary.paired_devices ?? 0],
    ["Recent activity (today)", state.summary.recent_activity_today ?? state.summary.recent_activity ?? 0],
    ["Connected now", state.summary.online_devices ?? 0],
  ];
  $("summaryCards").innerHTML = cards
    .map(([title, value]) => `<div class="card"><h4>${title}</h4><p>${value}</p></div>`)
    .join("");
}

function residentLine(r) {
  const paired = r.paired_device_id ? ` | ${r.paired_device_online ? "online" : "offline"}: ${r.paired_device_id}` : "";
  return `${r.full_name || "Unnamed"} | ${r.room || "No room"} | ${r.resident_uid}${paired}`;
}

function renderResidents() {
  const wrap = $("residentList");
  wrap.innerHTML = state.residents
    .map((r) => `<div class="list-item ${state.selectedResidentId === r.id ? "active" : ""}" data-id="${r.id}">${residentLine(r)}</div>`)
    .join("");
  wrap.querySelectorAll(".list-item").forEach((el) => {
    el.onclick = () => {
      const id = Number(el.dataset.id);
      state.selectedResidentId = id;
      const row = state.residents.find((r) => r.id === id);
      fillResidentForm(row);
      renderResidents();
    };
  });
}

function renderPairResidents() {
  const wrap = $("pairResidentList");
  wrap.innerHTML = state.residents
    .map((r) => `<div class="list-item ${state.selectedPairResidentId === r.id ? "active" : ""}" data-id="${r.id}">${residentLine(r)}</div>`)
    .join("");
  wrap.querySelectorAll(".list-item").forEach((el) => {
    el.onclick = () => {
      state.selectedPairResidentId = Number(el.dataset.id);
      renderPairResidents();
    };
  });
}

function renderDevices() {
  const wrap = $("deviceList");
  wrap.innerHTML = state.devices
    .map((d) => {
      const label = `${d.device_id} | ${d.is_online ? "online" : "offline"} | ${d.resident_name || "unpaired"}`;
      return `<div class="list-item ${state.selectedDeviceId === d.device_id ? "active" : ""}" data-id="${d.device_id}">${label}</div>`;
    })
    .join("");
  wrap.querySelectorAll(".list-item").forEach((el) => {
    el.onclick = () => {
      state.selectedDeviceId = el.dataset.id;
      renderDevices();
    };
  });
}

function renderLogs() {
  const wrap = $("logsList");
  wrap.innerHTML = state.logs
    .map((l) => {
      const when = l.created_at || "";
      const ok = l.success ? "Yes" : "No";
      const action = l.action_type || "";
      const msg = l.message || "";
      return `<div class="list-item"><strong>${when}</strong><br>${action} | Success: ${ok}<br>${msg}</div>`;
    })
    .join("");
}

function fillResidentForm(r) {
  $("residentId").value = r?.id ?? "";
  $("residentUid").value = r?.resident_uid ?? "";
  $("residentName").value = r?.full_name ?? "";
  $("residentRoom").value = r?.room ?? "";
  $("residentDiet").value = r?.diet ?? "";
  $("residentAllergies").value = r?.allergies ?? "";
  $("residentNote").value = r?.note ?? "";
  $("residentDrinks").value = r?.drinks ?? "";
  $("residentSchedule").value = r?.schedule ?? "";
}

function clearResidentForm() {
  fillResidentForm(null);
  state.selectedResidentId = null;
  renderResidents();
}

async function loadBootstrap() {
  const data = await api(`/api/bootstrap?base_url=${encodeURIComponent(state.baseUrl)}`);
  state.summary = data.summary || {};
  state.residents = data.residents || [];
  state.devices = data.devices || [];
  state.logs = data.logs || [];
  renderSummary();
  renderResidents();
  renderPairResidents();
  renderDevices();
  renderLogs();
}

async function doLogin() {
  const username = $("usernameInput").value.trim();
  const password = $("passwordInput").value.trim();
  state.baseUrl = $("baseUrlInput").value.trim() || state.baseUrl;
  setLoginError("");
  try {
    await api("/api/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    showApp();
    await loadBootstrap();
  } catch (err) {
    setLoginError(err.message);
  }
}

function activeTab(tab) {
  document.querySelectorAll(".nav").forEach((btn) => btn.classList.toggle("active", btn.dataset.tab === tab));
  document.querySelectorAll(".tab").forEach((s) => s.classList.toggle("active", s.id === `tab-${tab}`));
}

async function saveResident() {
  const payload = {
    id: $("residentId").value ? Number($("residentId").value) : null,
    resident_uid: $("residentUid").value.trim(),
    full_name: $("residentName").value.trim(),
    room: $("residentRoom").value.trim(),
    diet: $("residentDiet").value.trim(),
    allergies: $("residentAllergies").value.trim(),
    note: $("residentNote").value.trim(),
    drinks: $("residentDrinks").value.trim(),
    schedule: $("residentSchedule").value.trim(),
    active: true,
    needs_safety_review: false,
    base_url: state.baseUrl,
  };
  await api("/api/residents", { method: "POST", body: JSON.stringify(payload) });
  await loadBootstrap();
}

async function deleteResident() {
  const id = $("residentId").value ? Number($("residentId").value) : null;
  if (!id) return;
  if (!confirm("Delete this resident?")) return;
  await api(`/api/residents/${id}`, { method: "DELETE" });
  clearResidentForm();
  await loadBootstrap();
}

async function refreshDevices() {
  await api("/api/devices/refresh", {
    method: "POST",
    body: JSON.stringify({ base_url: state.baseUrl }),
  });
  await loadBootstrap();
}

async function pairResidentDevice() {
  if (!state.selectedPairResidentId || !state.selectedDeviceId) {
    $("pairStatus").textContent = "Select resident and device first.";
    return;
  }
  await api("/api/pair", {
    method: "POST",
    body: JSON.stringify({
      resident_id: state.selectedPairResidentId,
      device_id: state.selectedDeviceId,
      base_url: state.baseUrl,
    }),
  });
  $("pairStatus").textContent = "Paired and auto-sent.";
  await loadBootstrap();
}

async function unpairDevice() {
  if (!state.selectedDeviceId) {
    $("pairStatus").textContent = "Select a device first.";
    return;
  }
  await api("/api/unpair", {
    method: "POST",
    body: JSON.stringify({ device_id: state.selectedDeviceId }),
  });
  $("pairStatus").textContent = "Unpaired.";
  await loadBootstrap();
}

async function sendTextNow() {
  if (!state.selectedPairResidentId || !state.selectedDeviceId) {
    $("pairStatus").textContent = "Select resident and device first.";
    return;
  }
  await api("/api/send_text", {
    method: "POST",
    body: JSON.stringify({
      resident_id: state.selectedPairResidentId,
      device_id: state.selectedDeviceId,
      base_url: state.baseUrl,
    }),
  });
  $("pairStatus").textContent = "Text sent.";
  await loadBootstrap();
}

async function saveGlobalSchedule() {
  await api("/api/schedule/global", {
    method: "POST",
    body: JSON.stringify({
      enabled: $("schedEnabled").checked,
      lcd_on_time: $("schedOn").value,
      lcd_off_time: $("schedOff").value,
      sleep_if_no_image: $("schedSleepNoImg").checked,
      base_url: state.baseUrl,
    }),
  });
  alert("Global schedule applied.");
  await loadBootstrap();
}

async function logout() {
  await api("/api/logout", { method: "POST" });
  showLogin();
}

function wire() {
  $("baseUrlInput").value = state.baseUrl;
  $("loginBtn").onclick = doLogin;
  $("newResidentBtn").onclick = clearResidentForm;
  $("saveResidentBtn").onclick = () => saveResident().catch((e) => alert(e.message));
  $("deleteResidentBtn").onclick = () => deleteResident().catch((e) => alert(e.message));
  $("refreshBtn").onclick = () => refreshDevices().catch((e) => alert(e.message));
  $("pairBtn").onclick = () => pairResidentDevice().catch((e) => alert(e.message));
  $("unpairBtn").onclick = () => unpairDevice().catch((e) => alert(e.message));
  $("sendTextBtn").onclick = () => sendTextNow().catch((e) => alert(e.message));
  $("saveScheduleBtn").onclick = () => saveGlobalSchedule().catch((e) => alert(e.message));
  $("logoutBtn").onclick = () => logout().catch((e) => alert(e.message));
  document.querySelectorAll(".nav").forEach((btn) => {
    btn.onclick = () => activeTab(btn.dataset.tab);
  });
}

wire();

