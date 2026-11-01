import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from app.config import settings

log = logging.getLogger(__name__)


def _business_path() -> Path:
    return Path(settings.business_config_path)


def _normalize_service(s: dict, index: int) -> dict:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    srv_id = str(s.get("id") or f"srv_{index + 1}_{uuid.uuid4().hex[:6]}")
    return {
        "id": srv_id,
        "name": str(s.get("name") or "Nomsiz xizmat").strip(),
        "price": str(s.get("price") or "Kelishilgan narx").strip(),
        "duration": str(s.get("duration") or "Aniqlanmagan").strip(),
        "description": str(s.get("description") or "").strip(),
        "additional_info": str(s.get("additional_info") or "").strip(),
        "is_active": bool(s.get("is_active", True)),
        "created_at": str(s.get("created_at") or now_str),
        "updated_at": str(s.get("updated_at") or now_str),
    }


def load_business() -> dict:
    path = _business_path()
    if not path.exists():
        data = {
            "name": "Biznes",
            "description": "",
            "services": [],
            "faq": [],
            "handoff_text": "Operator bilan bog'laning.",
            "system_rules": "",
        }
        save_business(data)
        return data

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        log.error("Failed to parse %s: %s", path, exc)
        data = {}

    services = data.get("services", [])
    normalized = []
    has_changes = False

    for idx, s in enumerate(services):
        norm = _normalize_service(s, idx)
        if norm != s:
            has_changes = True
        normalized.append(norm)

    data["services"] = normalized
    if has_changes:
        save_business(data)
    return data


def save_business(data: dict) -> None:
    path = _business_path()
    temp_path = path.with_suffix(".tmp")
    text = json.dumps(data, ensure_ascii=False, indent=2)
    temp_path.write_text(text, encoding="utf-8")
    temp_path.replace(path)


def get_all_services() -> list[dict]:
    biz = load_business()
    return biz.get("services", [])


def get_active_services() -> list[dict]:
    all_s = get_all_services()
    return [s for s in all_s if s.get("is_active", True)]


def get_service_by_id(service_id: str) -> dict | None:
    for s in get_all_services():
        if s.get("id") == service_id:
            return s
    return None


def get_active_service_by_number(num: int) -> tuple[dict | None, int]:
    """
    Returns (service, total_active_count) for 1-based index `num`.
    """
    active = get_active_services()
    total = len(active)
    if 1 <= num <= total:
        return active[num - 1], total
    return None, total


def add_service(
    name: str,
    price: str,
    duration: str,
    description: str = "",
    additional_info: str = "",
    is_active: bool = True,
) -> dict:
    biz = load_business()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    srv = {
        "id": f"srv_{uuid.uuid4().hex[:8]}",
        "name": name.strip(),
        "price": price.strip(),
        "duration": duration.strip(),
        "description": description.strip(),
        "additional_info": additional_info.strip(),
        "is_active": is_active,
        "created_at": now_str,
        "updated_at": now_str,
    }
    biz.setdefault("services", []).append(srv)
    save_business(biz)
    return srv


def update_service(service_id: str, updates: dict) -> dict | None:
    biz = load_business()
    services = biz.get("services", [])
    target = None
    for s in services:
        if s.get("id") == service_id:
            target = s
            break
    if not target:
        return None

    for k, v in updates.items():
        if k in ("name", "price", "duration", "description", "additional_info"):
            target[k] = str(v).strip()
        elif k == "is_active":
            target[k] = bool(v)

    target["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_business(biz)
    return target


def delete_service(service_id: str) -> dict | None:
    biz = load_business()
    services = biz.get("services", [])
    removed = None
    new_services = []
    for s in services:
        if s.get("id") == service_id and removed is None:
            removed = s
        else:
            new_services.append(s)
    if removed:
        biz["services"] = new_services
        save_business(biz)
    return removed


def toggle_service_active(service_id: str) -> tuple[bool, dict | None]:
    """
    Toggles is_active for service_id.
    Returns (new_status, service_dict).
    """
    biz = load_business()
    for s in biz.get("services", []):
        if s.get("id") == service_id:
            s["is_active"] = not s.get("is_active", True)
            s["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            save_business(biz)
            return s["is_active"], s
    return False, None
