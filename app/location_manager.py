"""
Business Location Manager for AzamAI Business Bot.
Handles database persistence, validation of coordinates and URLs,
and formatting for customer and admin location views.
"""
from datetime import datetime
from html import escape
import logging
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.models import BusinessLocation

log = logging.getLogger(__name__)


def validate_coordinates(lat_val: float | str, lon_val: float | str) -> tuple[bool, float | None, float | None, str]:
    """
    Validates latitude and longitude ranges:
    -90 <= lat <= 90, -180 <= lon <= 180.
    """
    try:
        lat = float(lat_val)
        lon = float(lon_val)
    except (ValueError, TypeError):
        return False, None, None, "Koordinatalar raqam bo'lishi kerak (masalan: 41.2995, 69.2401)."

    if not (-90.0 <= lat <= 90.0):
        return False, None, None, "Kenglik (latitude) -90 dan +90 oralig'ida bo'lishi kerak."

    if not (-180.0 <= lon <= 180.0):
        return False, None, None, "Uzunlik (longitude) -180 dan +180 oralig'ida bo'lishi kerak."

    return True, lat, lon, "OK"


def validate_maps_url(url: str) -> tuple[bool, str]:
    """
    Validates Google Maps URL.
    """
    url = url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        return False, "Havola http:// yoki https:// bilan boshlanishi kerak."
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            return False, "Yaroqsiz URL formati."
    except Exception:
        return False, "Yaroqsiz URL."
    return True, "OK"


async def get_location() -> BusinessLocation | None:
    """
    Retrieves the active business location record.
    """
    async with SessionLocal() as db:
        loc = await db.scalar(select(BusinessLocation).where(BusinessLocation.is_active == True).limit(1))
        return loc


async def save_location(
    address: str | None = None,
    landmark: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    google_maps_url: str | None = None,
) -> BusinessLocation:
    """
    Creates or updates the business location record.
    """
    async with SessionLocal() as db:
        loc = await db.scalar(select(BusinessLocation).limit(1))
        if loc is None:
            loc = BusinessLocation(is_active=True)
            db.add(loc)

        if address is not None:
            loc.address = address.strip()
        if landmark is not None:
            loc.landmark = landmark.strip()
        if latitude is not None and longitude is not None:
            loc.latitude = latitude
            loc.longitude = longitude
        if google_maps_url is not None:
            loc.google_maps_url = google_maps_url.strip()

        loc.is_active = True
        loc.updated_at = datetime.now(ZoneInfo(settings.timezone))
        await db.commit()
        await db.refresh(loc)
        return loc


async def clear_location() -> bool:
    """
    Resets location fields.
    """
    async with SessionLocal() as db:
        loc = await db.scalar(select(BusinessLocation).limit(1))
        if loc:
            loc.address = ""
            loc.landmark = ""
            loc.latitude = None
            loc.longitude = None
            loc.google_maps_url = ""
            loc.updated_at = datetime.now(ZoneInfo(settings.timezone))
            await db.commit()
            return True
        return False


def format_customer_location_text(loc: BusinessLocation | None) -> str:
    if not loc or (not loc.address and not loc.google_maps_url and loc.latitude is None):
        return (
            "📍 <b>Bizning manzilimiz:</b>\n\n"
            "Hozircha manzil ma'lumotlari kiritilmagan.\n"
            "Aniq manzilni bilish uchun operatorimiz bilan bog'laning."
        )

    text = "📍 <b>Bizning manzilimiz</b>\n\n"
    if loc.address:
        text += f"🏢 <b>Manzil:</b> {escape(loc.address)}\n\n"
    if loc.landmark:
        text += f"ℹ️ <b>Mo'ljal:</b> {escape(loc.landmark)}\n\n"

    if loc.latitude is not None and loc.longitude is not None:
        text += "🗺 <i>Xarita lokatsiyasi ham mavjud. Pastdagi tugma orqali lokatsiyani xaritada ochishingiz mumkin.</i>"

    return text.strip()


def format_admin_location_text(loc: BusinessLocation | None) -> str:
    if not loc:
        return (
            "📍 <b>Manzil va xarita sozlamalari</b>\n\n"
            "<i>Hozircha manzil kiritilmagan.</i>\n\n"
            "Quyidagi tugmalar orqali manzil, koordinata yoki Google Maps havolasini kiriting:"
        )

    coords_str = f"{loc.latitude}, {loc.longitude}" if (loc.latitude is not None and loc.longitude is not None) else "Kiritilmagan"
    maps_str = escape(loc.google_maps_url) if loc.google_maps_url else "Kiritilmagan"
    address_str = escape(loc.address) if loc.address else "Kiritilmagan"
    landmark_str = escape(loc.landmark) if loc.landmark else "Kiritilmagan"

    return (
        "📍 <b>Manzil va xarita sozlamalari</b>\n\n"
        f"🏢 <b>Manzil:</b> {address_str}\n"
        f"ℹ️ <b>Mo'ljal:</b> {landmark_str}\n"
        f"🌐 <b>Koordinatalar:</b> <code>{coords_str}</code>\n"
        f"🗺 <b>Google Maps:</b> {maps_str}\n\n"
        "O'zgartirmoqchi bo'lgan ma'lumotni tanlang:"
    )
