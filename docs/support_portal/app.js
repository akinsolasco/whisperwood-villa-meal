const articles = [
  {
    title: "Install or update the desktop app",
    section: "Downloads",
    keywords: "install update desktop installer download app setup windows smart screen defender latest version",
    summary: "Use the Raspberry Pi download page while connected to the facility network. Download the Windows installer, run it, then reopen Enhanced Living Whisperwood.",
    steps: [
      "Connect to the same network or VPN as the Raspberry Pi.",
      "Open the installer download link in this portal.",
      "Download WhisperwoodVillaSetup.exe and run it.",
      "If Windows SmartScreen appears, confirm the app came from the trusted Whisperwood network page before continuing.",
      "Open the app and confirm the displayed version."
    ],
    link: "#downloads"
  },
  {
    title: "Login fails or app says server unreachable",
    section: "Access",
    keywords: "login unauthorized network database control service server unreachable vpn facility network password",
    summary: "The app requires the Control Service when using the live system. Most login failures are caused by wrong network/VPN, server down, or credentials.",
    steps: [
      "Connect to the dedicated facility network or approved VPN.",
      "Ask IT Admin to confirm Control Service status.",
      "Confirm username is active and password is correct.",
      "If temporary password was issued, change it after login."
    ],
    link: "#troubleshooting"
  },
  {
    title: "Create or update a resident",
    section: "Admin / Nurse Admin",
    keywords: "resident create update edit diet texture fluids source document photo safety review approval nurse admin",
    summary: "Admin owns resident accuracy. Every resident change should have source information and should be saved before pairing or display updates.",
    steps: [
      "Search first to avoid duplicate records.",
      "Fill name, room, diet, texture, fluids, note, drinks, active status.",
      "Attach source document and resident photo.",
      "Mark safety review if information must be checked later.",
      "Save the record. If paired, text update is sent through the display pipeline."
    ],
    link: "#playbooks"
  },
  {
    title: "Staff change request",
    section: "Staff / Nurse",
    keywords: "staff nurse comment change request approval admin verify resident information cannot edit",
    summary: "Staff can view resident information and submit comments for Admin approval instead of directly editing live resident data.",
    steps: [
      "Open the resident record.",
      "Write a clear comment with what changed and where the information came from.",
      "Submit the change request.",
      "Admin reviews, verifies, edits if needed, then saves the approved resident record."
    ],
    link: "#roles"
  },
  {
    title: "Device offline",
    section: "Hardware",
    keywords: "esp32 offline online wifi disconnected gateway raspberry pi last seen device not connected provisioning",
    summary: "Check power, WiFi, Pi gateway, and last seen time before assuming the display unit failed.",
    steps: [
      "Confirm the display unit has power.",
      "Check whether the ESP32 is connected to the expected WiFi.",
      "Open IT Admin device list and review last seen time.",
      "Use USB provisioning if WiFi credentials changed.",
      "Collect device ID and serial logs before replacing hardware."
    ],
    link: "#troubleshooting"
  },
  {
    title: "LCD photo turns white or does not update",
    section: "LCD",
    keywords: "lcd photo image white blank reboot picture orientation landscape portrait screen shared bus",
    summary: "This usually points to LCD refresh, image send timing, or shared bus reclaim. Send photo separately and wait for acknowledgement.",
    steps: [
      "Attach the photo in Resident Records.",
      "Use Send Resident Photo and wait for the result.",
      "Do not repeatedly send text and image together.",
      "If photo appears only after reboot, capture firmware version and device ID for IT Admin.",
      "Check image orientation and firmware LCD bus reclaim notes."
    ],
    link: "#troubleshooting"
  },
  {
    title: "E-paper looks dirty or partial",
    section: "E-paper",
    keywords: "epaper e-paper dirty partial not wiping old text busy pin refresh text wrapping resident display",
    summary: "Wait for e-paper refresh to finish, confirm firmware clears before drawing, and check power stability.",
    steps: [
      "Wait for the update to finish before sending another command.",
      "Confirm the latest firmware is installed.",
      "Check battery and USB power stability.",
      "Take a clear photo of the display and collect serial logs."
    ],
    link: "#troubleshooting"
  },
  {
    title: "Google Drive backup and restore",
    section: "Recovery",
    keywords: "google drive backup restore rclone oauth token service account recovery bundle pi sd card failure data loss",
    summary: "The Pi creates a local recovery bundle first. Google Drive upload is optional but recommended for disaster recovery.",
    steps: [
      "IT Admin opens Settings > Integrations and configures Google Drive.",
      "Use Test Drive to confirm the remote works.",
      "Enable automatic recovery backup from IT Admin > Backups.",
      "If restoring, prepare the replacement Pi first, then restore the selected backup bundle."
    ],
    link: "#recovery"
  },
  {
    title: "LCD schedule does not run",
    section: "Schedule",
    keywords: "lcd schedule turn off turn on multiple schedule global manual control selected device time timezone",
    summary: "Confirm the Pi time zone, schedule entries, and whether you are using global schedule or manual control for one selected device.",
    steps: [
      "Check Pi time and Atlantic Time display in the app.",
      "Open LCD Schedule and confirm the schedule entry is enabled.",
      "Use multiple entries when different off/on times are required.",
      "Test manual LCD on/off for a selected device.",
      "Delete old schedule entries that conflict with the current plan."
    ],
    link: "#playbooks"
  },
  {
    title: "OTA firmware update",
    section: "IT Admin",
    keywords: "firmware ota esp32 bin upload release update arduino device all selected",
    summary: "IT Admin uploads a compiled ESP32 .bin and releases it to selected devices or all devices when the OTA backend is ready.",
    steps: [
      "Confirm the firmware was built from the approved source.",
      "Upload the .bin in IT Admin device/firmware tools.",
      "Release to one test device first.",
      "Confirm the device comes back online and reports the expected firmware version.",
      "Release to remaining devices only after the test is stable."
    ],
    link: "#technical"
  }
];

const results = document.getElementById("results");
const searchInput = document.getElementById("supportSearch");
const searchButton = document.getElementById("searchButton");

function scoreArticle(article, query) {
  const q = query.toLowerCase().trim();
  if (!q) return article.title === "Install or update the desktop app" ? 3 : 1;
  const haystack = `${article.title} ${article.section} ${article.keywords} ${article.summary}`.toLowerCase();
  const terms = q.split(/\s+/).filter(Boolean);
  return terms.reduce((score, term) => score + (haystack.includes(term) ? 3 : 0), 0);
}

function renderResults(query = "") {
  const ranked = articles
    .map((article) => ({ article, score: scoreArticle(article, query) }))
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 3);

  const visible = ranked.length ? ranked : articles.slice(0, 3).map((article) => ({ article, score: 1 }));

  results.innerHTML = visible.map(({ article }) => `
    <article class="result-card">
      <p class="eyebrow">${article.section}</p>
      <h3>${article.title}</h3>
      <p>${article.summary}</p>
      <ol>
        ${article.steps.slice(0, 4).map((step) => `<li>${step}</li>`).join("")}
      </ol>
      <a href="${article.link}"><strong>Open related section</strong></a>
    </article>
  `).join("");
}

function runSearch() {
  renderResults(searchInput.value);
}

searchButton.addEventListener("click", runSearch);
searchInput.addEventListener("input", () => renderResults(searchInput.value));
searchInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    runSearch();
  }
});

document.querySelectorAll("[data-query]").forEach((button) => {
  button.addEventListener("click", () => {
    searchInput.value = button.dataset.query || "";
    renderResults(searchInput.value);
    searchInput.focus();
  });
});

document.querySelectorAll("[data-accordion] > button").forEach((button) => {
  button.addEventListener("click", () => {
    const panel = button.nextElementSibling;
    const isOpen = button.getAttribute("aria-expanded") === "true";
    button.setAttribute("aria-expanded", String(!isOpen));
    if (panel) panel.hidden = isOpen;
  });
});

document.getElementById("printGuide").addEventListener("click", () => window.print());

document.getElementById("copyChecklist").addEventListener("click", async () => {
  const checklist = [
    "Enhanced Living Whisperwood support checklist",
    "1. Site/facility:",
    "2. User role and username:",
    "3. App version:",
    "4. Laptop network/VPN:",
    "5. Exact date and time:",
    "6. Resident UID or room:",
    "7. Device ID:",
    "8. What was clicked:",
    "9. Exact error message:",
    "10. Screenshot/photo attached:",
    "11. Pi logs or ESP32 serial logs attached:",
    "12. Does it affect one device or all devices:"
  ].join("\n");

  try {
    await navigator.clipboard.writeText(checklist);
    document.getElementById("copyChecklist").textContent = "Checklist copied";
  } catch (error) {
    document.getElementById("copyChecklist").textContent = "Copy failed";
  }
});

function updateLocalLinks() {
  const host = window.location.hostname || "192.168.2.37";
  const download = document.getElementById("desktopDownload");
  const manual = document.getElementById("manualHome");
  if (download) download.href = `http://${host}:8090/download/`;
  if (manual) manual.href = window.location.href;
}

updateLocalLinks();
renderResults();
