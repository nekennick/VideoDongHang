const $ = (id) => document.getElementById(id);
let lastVideoItems = new Map();
let currentConfig = null;

function fmtDuration(value) {
  return `${Number(value || 0).toFixed(1)}s`;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => {
    const entities = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return entities[char];
  });
}

async function refreshStatus() {
  const res = await fetch("/api/status");
  const status = await res.json();
  $("state").textContent = status.state;
  $("state").className = `state state-${String(status.state).toLowerCase()}`;
  $("order").textContent = status.current_order_code || "-";
  $("platform").textContent = status.current_platform || "unknown";
  $("duration").textContent = fmtDuration(status.current_duration_seconds);
  $("queue").textContent = status.compression_queue_size;
  $("done").textContent = status.done_today;
  $("failed").textContent = status.failed_today;
  $("disk").textContent = `${status.disk_free_gb} GB`;
  $("lastQr").textContent = status.last_qr_content || "-";
  $("camera").textContent = status.camera_connected ? "connected" : "disconnected";
  const warnings = [];
  if (status.camera_error) warnings.push(status.camera_error);
  if (!status.ffmpeg_available) {
    warnings.push(`FFmpeg chưa sẵn sàng: ${status.ffmpeg_path}`);
  }
  if (status.disk_space_low) {
    warnings.push(`Ổ đĩa sắp đầy: còn ${status.disk_free_gb} GB, ngưỡng tối thiểu ${status.min_free_disk_gb} GB`);
  }
  $("warning").textContent = warnings.join(" | ");
}

async function loadConfig() {
  const res = await fetch("/api/config");
  const config = await res.json();
  currentConfig = config;
  fillConfigForm(config);
  const roiBox = document.querySelector(".roi-box");
  const roi = config.qr?.roi;
  if (!config.qr?.roi_enabled || !roi) {
    roiBox.hidden = true;
    return;
  }
  roiBox.hidden = false;
  roiBox.style.left = `${Number(roi.x || 0) * 100}%`;
  roiBox.style.top = `${Number(roi.y || 0) * 100}%`;
  roiBox.style.width = `${Number(roi.w || 0) * 100}%`;
  roiBox.style.height = `${Number(roi.h || 0) * 100}%`;
}

function setField(name, value) {
  const field = document.querySelector(`[name="${name}"]`);
  if (!field) return;
  if (field.type === "checkbox") {
    field.checked = Boolean(value);
  } else {
    field.value = value ?? "";
  }
}

function fillConfigForm(config) {
  setField("camera.index", config.camera?.index);
  setField("camera.width", config.camera?.width);
  setField("camera.height", config.camera?.height);
  setField("camera.fps", config.camera?.fps);
  setField("ffmpeg.crf", config.ffmpeg?.crf);
  setField("ffmpeg.preset", config.ffmpeg?.preset);
  setField("storage.min_free_disk_gb", config.storage?.min_free_disk_gb);
  setField("qr.roi_enabled", config.qr?.roi_enabled);
  setField("qr.roi.x", config.qr?.roi?.x);
  setField("qr.roi.y", config.qr?.roi?.y);
  setField("qr.roi.w", config.qr?.roi?.w);
  setField("qr.roi.h", config.qr?.roi?.h);
}

function readNumber(name) {
  const field = document.querySelector(`[name="${name}"]`);
  return field.value === "" ? undefined : Number(field.value);
}

function readText(name) {
  const field = document.querySelector(`[name="${name}"]`);
  return field.value.trim();
}

function buildConfigPayload() {
  return {
    camera: {
      index: readNumber("camera.index"),
      width: readNumber("camera.width"),
      height: readNumber("camera.height"),
      fps: readNumber("camera.fps"),
    },
    ffmpeg: {
      crf: readNumber("ffmpeg.crf"),
      preset: readText("ffmpeg.preset"),
    },
    storage: {
      min_free_disk_gb: readNumber("storage.min_free_disk_gb"),
    },
    qr: {
      roi_enabled: document.querySelector('[name="qr.roi_enabled"]').checked,
      roi: {
        x: readNumber("qr.roi.x"),
        y: readNumber("qr.roi.y"),
        w: readNumber("qr.roi.w"),
        h: readNumber("qr.roi.h"),
      },
    },
  };
}

function removeEmptyValues(value) {
  if (!value || typeof value !== "object") return value;
  for (const key of Object.keys(value)) {
    if (value[key] === undefined || value[key] === "") {
      delete value[key];
    } else {
      removeEmptyValues(value[key]);
      if (value[key] && typeof value[key] === "object" && Object.keys(value[key]).length === 0) {
        delete value[key];
      }
    }
  }
  return value;
}

function queryFromForm() {
  const params = new URLSearchParams();
  const data = new FormData($("filters"));
  for (const [key, value] of data.entries()) {
    if (value) params.set(key, value);
  }
  params.set("limit", "50");
  return params.toString();
}

async function refreshVideos() {
  const res = await fetch(`/api/videos?${queryFromForm()}`);
  const data = await res.json();
  lastVideoItems = new Map(data.items.map((item) => [String(item.id), item]));
  $("videos").innerHTML = data.items
    .map((item) => {
      const size = item.compressed_size_mb || item.raw_size_mb || "";
      const view = item.status === "done" ? `<a href="/video/${item.id}" target="_blank">Xem</a>` : "";
      const folder = item.video_path || item.raw_path ? `<button type="button" data-open-folder="${item.id}">Mở</button>` : "";
      const copy = item.video_path || item.raw_path ? `<button type="button" data-copy-path="${item.id}">Copy</button>` : "";
      const retry = item.status === "failed" && item.raw_path ? `<button type="button" data-retry="${item.id}">Nén lại</button>` : "";
      const error = item.error_message ? String(item.error_message).slice(0, 140) : "";
      return `<tr>
        <td>${escapeHtml(item.start_time)}</td>
        <td>${escapeHtml(item.order_code)}</td>
        <td>${escapeHtml(item.platform)}</td>
        <td>${escapeHtml(item.status)}</td>
        <td>${item.duration_seconds ? Number(item.duration_seconds).toFixed(1) : ""}</td>
        <td>${escapeHtml(size)}</td>
        <td class="error-cell" title="${escapeHtml(item.error_message)}">${escapeHtml(error)}</td>
        <td>${view}</td>
        <td>${retry}</td>
        <td>${folder}</td>
        <td>${copy}</td>
      </tr>`;
    })
    .join("");
}

$("filters").addEventListener("submit", (event) => {
  event.preventDefault();
  refreshVideos();
});

$("emergency").addEventListener("click", async () => {
  if (!confirm("Xác nhận dừng khẩn cấp / kết thúc ca?")) return;
  await fetch("/api/admin/emergency-stop", { method: "POST" });
  await refreshStatus();
  await refreshVideos();
});

$("openVideosFolder").addEventListener("click", async () => {
  await fetch("/api/admin/open-videos-folder", { method: "POST" });
});

$("videos").addEventListener("click", async (event) => {
  const openButton = event.target.closest("[data-open-folder]");
  if (openButton) {
    await fetch(`/api/admin/open-video-folder/${openButton.dataset.openFolder}`, { method: "POST" });
    return;
  }
  const copyButton = event.target.closest("[data-copy-path]");
  if (copyButton) {
    const item = lastVideoItems.get(copyButton.dataset.copyPath);
    const path = item?.video_path || item?.raw_path || "";
    if (!path) return;
    await navigator.clipboard.writeText(path);
    copyButton.textContent = "Đã copy";
    setTimeout(() => {
      copyButton.textContent = "Copy";
    }, 1200);
    return;
  }
  const retryButton = event.target.closest("[data-retry]");
  if (!retryButton) return;
  retryButton.disabled = true;
  retryButton.textContent = "Đã gửi";
  const res = await fetch(`/api/admin/retry-compression/${retryButton.dataset.retry}`, { method: "POST" });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    retryButton.textContent = data.detail || "Lỗi";
    retryButton.disabled = false;
    return;
  }
  await refreshVideos();
});

$("configForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = $("configMessage");
  message.textContent = "Đang lưu...";
  const payload = removeEmptyValues(buildConfigPayload());
  const res = await fetch("/api/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    message.textContent = data.detail || "Không lưu được cấu hình";
    return;
  }
  const data = await res.json();
  currentConfig = data.config;
  fillConfigForm(currentConfig);
  await loadConfig();
  message.textContent = data.restart_required ? "Đã lưu. Khởi động lại app để áp dụng camera/storage." : "Đã lưu";
});

loadConfig();
refreshStatus();
refreshVideos();
setInterval(refreshStatus, 1000);
setInterval(refreshVideos, 5000);
