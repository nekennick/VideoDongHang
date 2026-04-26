const $ = (id) => document.getElementById(id);
let lastVideoItems = new Map();
let selectedVideoIds = new Set();

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

function canDeleteVideo(item) {
  return !["recording", "queued", "compressing"].includes(item.status);
}

function updateBulkActions() {
  const count = selectedVideoIds.size;
  $("selectedCount").textContent = count ? `Đã chọn ${count} video` : "Chưa chọn video nào";
  $("bulkDelete").disabled = count === 0;

  const selectableIds = [...lastVideoItems.entries()]
    .filter(([, item]) => canDeleteVideo(item))
    .map(([id]) => id);
  const selectedVisibleCount = selectableIds.filter((id) => selectedVideoIds.has(id)).length;
  $("selectAllVideos").checked = selectableIds.length > 0 && selectedVisibleCount === selectableIds.length;
  $("selectAllVideos").indeterminate = selectedVisibleCount > 0 && selectedVisibleCount < selectableIds.length;
}

async function refreshVideos() {
  const res = await fetch(`/api/videos?${queryFromForm()}`);
  const data = await res.json();
  lastVideoItems = new Map(data.items.map((item) => [String(item.id), item]));
  selectedVideoIds = new Set([...selectedVideoIds].filter((id) => lastVideoItems.has(id)));
  $("videos").innerHTML = data.items
    .map((item) => {
      const itemId = String(item.id);
      const size = item.compressed_size_mb || item.raw_size_mb || "";
      const view = item.status === "done" ? `<a href="/video/${item.id}" target="_blank">Xem</a>` : "";
      const folder = item.video_path || item.raw_path ? `<button type="button" data-open-folder="${item.id}">Mở</button>` : "";
      const copy = item.video_path || item.raw_path ? `<button type="button" data-copy-path="${item.id}">Copy</button>` : "";
      const retry = item.status === "failed" && item.raw_path ? `<button type="button" data-retry="${item.id}">Nén lại</button>` : "";
      const deleteAllowed = canDeleteVideo(item);
      const checked = selectedVideoIds.has(itemId) ? "checked" : "";
      const checkbox = deleteAllowed
        ? `<input type="checkbox" data-select-video="${item.id}" ${checked} aria-label="Chọn video ${escapeHtml(item.order_code)}" />`
        : "";
      const remove = deleteAllowed ? `<button class="delete-video-button" type="button" data-delete="${item.id}">Xóa</button>` : "";
      const error = item.error_message ? String(item.error_message).slice(0, 140) : "";
      return `<tr>
        <td>${checkbox}</td>
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
        <td>${remove}</td>
      </tr>`;
    })
    .join("");
  updateBulkActions();
}

$("filters").addEventListener("submit", (event) => {
  event.preventDefault();
  $("bulkMessage").textContent = "";
  refreshVideos();
});

$("selectAllVideos").addEventListener("change", (event) => {
  for (const [id, item] of lastVideoItems.entries()) {
    if (!canDeleteVideo(item)) continue;
    if (event.target.checked) {
      selectedVideoIds.add(id);
    } else {
      selectedVideoIds.delete(id);
    }
  }
  $("bulkMessage").textContent = "";
  refreshVideos();
});

$("bulkDelete").addEventListener("click", async () => {
  const ids = [...selectedVideoIds];
  if (!ids.length) return;
  if (!confirm(`Xóa ${ids.length} video đã chọn? File video/raw và record database sẽ bị xóa.`)) return;
  $("bulkDelete").disabled = true;
  $("bulkMessage").textContent = "Đang xóa...";
  const res = await fetch("/api/videos/bulk-delete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    $("bulkMessage").textContent = data.detail || "Không xóa được";
    updateBulkActions();
    return;
  }
  selectedVideoIds.clear();
  $("bulkMessage").textContent = data.failed?.length ? `Đã xóa ${data.deleted.length}, lỗi ${data.failed.length}` : `Đã xóa ${data.deleted.length} video`;
  await refreshVideos();
});

$("videos").addEventListener("click", async (event) => {
  const openButton = event.target.closest("[data-open-folder]");
  if (openButton) {
    const res = await fetch(`/api/admin/open-video-folder/${openButton.dataset.openFolder}`, { method: "POST" });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      alert(data.detail || "Không mở được thư mục");
    }
    return;
  }

  const selectBox = event.target.closest("[data-select-video]");
  if (selectBox) {
    const id = selectBox.dataset.selectVideo;
    if (selectBox.checked) {
      selectedVideoIds.add(id);
    } else {
      selectedVideoIds.delete(id);
    }
    $("bulkMessage").textContent = "";
    updateBulkActions();
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

  const deleteButton = event.target.closest("[data-delete]");
  if (deleteButton) {
    const item = lastVideoItems.get(deleteButton.dataset.delete);
    const orderCode = item?.order_code || "";
    if (!confirm(`Xóa video mã ${orderCode}? File video/raw và record database sẽ bị xóa.`)) return;
    deleteButton.disabled = true;
    deleteButton.textContent = "Đang xóa";
    const res = await fetch(`/api/videos/${deleteButton.dataset.delete}`, { method: "DELETE" });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      deleteButton.textContent = data.detail || "Lỗi";
      deleteButton.disabled = false;
      return;
    }
    selectedVideoIds.delete(deleteButton.dataset.delete);
    await refreshVideos();
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
