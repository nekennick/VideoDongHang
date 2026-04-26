const $ = (id) => document.getElementById(id);
const RECENT_CLEAR_KEY = "packingVideo.recentHiddenBefore";

const SYSTEM_STATE_LABELS = {
  IDLE: "Sẵn sàng",
  RECORDING: "Đang quay",
  SHIFT_ENDED: "Đã dừng quay",
  ERROR: "Lỗi",
};

const VIDEO_STATUS_LABELS = {
  recording: "Đang quay",
  queued: "Chờ nén",
  compressing: "Đang nén",
  done: "Hoàn tất",
  failed: "Lỗi",
};

function systemStateLabel(value) {
  return SYSTEM_STATE_LABELS[value] || value || "-";
}

function videoStatusLabel(value) {
  return VIDEO_STATUS_LABELS[value] || value || "-";
}

function fmtDuration(value) {
  return `${Number(value || 0).toFixed(1)}s`;
}

function fmtTime(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
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

function imageContentRect() {
  const wrap = document.querySelector(".preview-wrap");
  const image = $("preview");
  const wrapRect = wrap.getBoundingClientRect();
  const naturalWidth = image.naturalWidth || 16;
  const naturalHeight = image.naturalHeight || 9;
  const imageRatio = naturalWidth / naturalHeight;
  const wrapRatio = wrapRect.width / wrapRect.height;
  if (wrapRatio > imageRatio) {
    const height = wrapRect.height;
    const width = height * imageRatio;
    return { left: (wrapRect.width - width) / 2, top: 0, width, height };
  }
  const width = wrapRect.width;
  const height = width / imageRatio;
  return { left: 0, top: (wrapRect.height - height) / 2, width, height };
}

function renderQrDetections(detections) {
  const layer = $("qrDetections");
  const rect = imageContentRect();
  layer.style.left = `${rect.left}px`;
  layer.style.top = `${rect.top}px`;
  layer.style.width = `${rect.width}px`;
  layer.style.height = `${rect.height}px`;
  layer.innerHTML = (detections || [])
    .map((box) => {
      const label = escapeHtml(box.label || "QR");
      return `<div class="qr-detection-box" style="left:${box.x * 100}%;top:${box.y * 100}%;width:${box.w * 100}%;height:${box.h * 100}%;">
        <span>${label}</span>
      </div>`;
    })
    .join("");
}

async function refreshStatus() {
  const res = await fetch("/api/status");
  const status = await res.json();
  $("state").textContent = systemStateLabel(status.state);
  $("state").className = `state state-${String(status.state).toLowerCase()}`;
  $("order").textContent = status.current_order_code || "-";
  $("platform").textContent = status.current_platform || "unknown";
  $("duration").textContent = fmtDuration(status.current_duration_seconds);
  $("queue").textContent = status.compression_queue_size;
  $("done").textContent = status.done_today;
  $("failed").textContent = status.failed_today;
  $("disk").textContent = `${status.disk_free_gb} GB`;
  $("lastQr").textContent = status.last_qr_content || "-";
  $("camera").textContent = status.camera_connected ? "Đã kết nối" : "Mất kết nối";
  const warnings = [];
  if (status.camera_error) warnings.push(status.camera_error);
  if (!status.ffmpeg_available) warnings.push(`FFmpeg chưa sẵn sàng: ${status.ffmpeg_path}`);
  if (status.disk_space_low) {
    warnings.push(`Ổ đĩa sắp đầy: còn ${status.disk_free_gb} GB, ngưỡng tối thiểu ${status.min_free_disk_gb} GB`);
  }
  if (status.last_ignored_reason === "duplicate_order" && status.last_ignored_order_code) {
    warnings.push(`Mã ${status.last_ignored_order_code} đã có video, hệ thống bỏ qua`);
  }
  $("warning").textContent = warnings.join(" | ");
  $("clearRecentList").hidden = status.state !== "SHIFT_ENDED";
  renderQrDetections(status.qr_detections);
}

async function refreshRecentVideos() {
  const res = await fetch("/api/videos?limit=50");
  const data = await res.json();
  const hiddenBefore = localStorage.getItem(RECENT_CLEAR_KEY);
  const visibleItems = hiddenBefore
    ? data.items.filter((item) => {
        if (!item.start_time) return true;
        return new Date(item.start_time).getTime() > new Date(hiddenBefore).getTime();
      })
    : data.items;
  $("recentVideos").innerHTML = visibleItems
    .map((item) => {
      return `<tr>
        <td>${escapeHtml(fmtTime(item.start_time))}</td>
        <td>${escapeHtml(item.order_code)}</td>
        <td>${escapeHtml(videoStatusLabel(item.status))}</td>
        <td>${item.duration_seconds ? Number(item.duration_seconds).toFixed(1) : ""}</td>
      </tr>`;
    })
    .join("");
}

async function loadConfig() {
  const res = await fetch("/api/config");
  const config = await res.json();
  fillConfigForm(config);
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

$("emergency").addEventListener("click", async () => {
  if (!confirm("Xác nhận dừng quay?")) return;
  await fetch("/api/admin/emergency-stop", { method: "POST" });
  await refreshStatus();
  await refreshRecentVideos();
});

$("openVideosFolder").addEventListener("click", async () => {
  await fetch("/api/admin/open-videos-folder", { method: "POST" });
});

$("clearRecentList").addEventListener("click", () => {
  localStorage.setItem(RECENT_CLEAR_KEY, new Date().toISOString());
  refreshRecentVideos();
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
  fillConfigForm(data.config);
  await loadConfig();
  message.textContent = data.restart_required ? "Đã lưu. Khởi động lại app để áp dụng camera/storage." : "Đã lưu";
});

loadConfig();
refreshStatus();
refreshRecentVideos();
setInterval(refreshStatus, 500);
setInterval(refreshRecentVideos, 5000);
window.addEventListener("resize", refreshStatus);
