const $ = (id) => document.getElementById(id);
let lastVideoItems = new Map();

const VIDEO_STATUS_LABELS = {
  recording: "Đang quay",
  queued: "Chờ nén",
  compressing: "Đang nén",
  done: "Hoàn tất",
  failed: "Lỗi",
};

function videoStatusLabel(value) {
  return VIDEO_STATUS_LABELS[value] || value || "-";
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

function queryFromForm() {
  const params = new URLSearchParams();
  const data = new FormData($("filters"));
  for (const [key, value] of data.entries()) {
    if (value) params.set(key, value);
  }
  params.set("limit", "200");
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
        <td>${escapeHtml(videoStatusLabel(item.status))}</td>
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

refreshVideos();
setInterval(refreshVideos, 5000);
