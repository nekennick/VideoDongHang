from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse


END_SHIFT_COMMAND = "CMD:END_SHIFT"
ORDER_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{4,80}")
ORDER_KEY_RE = re.compile(r"(?:order|order_code|orderid|tracking|tracking_no|code)\s*[:=]\s*([A-Za-z0-9_-]{5,80})", re.IGNORECASE)
IGNORED_TOKENS = {
    "http",
    "https",
    "www",
    "com",
    "shop",
    "shopee",
    "tiktok",
    "order",
    "orders",
    "tracking",
}


def extract_order_code(content: str) -> str | None:
    normalized = content.strip()
    if normalized.startswith("ORDER:"):
        normalized = normalized.split(":", 1)[1].strip()
        matches = ORDER_TOKEN_RE.findall(normalized)
        return matches[0] if matches else None

    key_match = ORDER_KEY_RE.search(normalized)
    if key_match:
        return key_match.group(1)

    parsed = urlparse(normalized)
    if parsed.query:
        query = parse_qs(parsed.query)
        for key in ("order_code", "orderId", "orderid", "order", "tracking_no", "tracking", "code"):
            values = query.get(key)
            if values:
                matches = ORDER_TOKEN_RE.findall(values[0])
                if matches:
                    return matches[0]

    matches = [token for token in ORDER_TOKEN_RE.findall(normalized) if token.lower() not in IGNORED_TOKENS]
    if not matches:
        return None
    return max(matches, key=len)


def detect_platform(order_code: str, raw_content: str) -> str:
    text = f"{order_code} {raw_content}".lower()
    if "shopee" in text or text.startswith("spx") or text.startswith("shp"):
        return "shopee"
    if "tiktok" in text or "tik tok" in text:
        return "tiktok"
    return "unknown"


def classify_qr(content: str) -> dict:
    normalized = content.strip()
    if normalized == END_SHIFT_COMMAND:
        return {"type": "end_shift", "raw_content": content}
    order_code = extract_order_code(normalized)
    if order_code:
        return {
            "type": "order",
            "order_code": order_code,
            "platform": detect_platform(order_code, normalized),
            "raw_content": content,
        }
    return {"type": "invalid", "raw_content": content}
