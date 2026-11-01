"""
Analytics and Reporting Engine for AzamAI Business Bot.
Computes real-time business statistics based on Asia/Tashkent timezone,
provides period-based reports, and executes the automatic daily 21:00 scheduler.
"""
import asyncio
from datetime import datetime, time, timedelta
from html import escape
import logging
from zoneinfo import ZoneInfo

from aiogram import Bot
from sqlalchemy import func, select

from app import services_manager
from app.config import settings
from app.db import SessionLocal
from app.models import Announcement, Customer, DailyReportLog, ServiceOrder
from app.notifications import notify_admins

log = logging.getLogger(__name__)


def get_tz() -> ZoneInfo:
    try:
        return ZoneInfo(settings.timezone)
    except Exception:
        return ZoneInfo("Asia/Tashkent")


def now_in_tz() -> datetime:
    return datetime.now(get_tz())


def get_time_boundaries():
    """
    Returns (today_start, week_start, month_start) in UTC-compatible or timezone-aware datetime.
    """
    tz = get_tz()
    now = datetime.now(tz)

    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    # Week start: Monday
    week_start = (today_start - timedelta(days=today_start.weekday()))
    # Month start: 1st of current month
    month_start = today_start.replace(day=1)

    return now, today_start, week_start, month_start


async def get_dashboard_stats() -> dict:
    """
    Computes real-time comprehensive statistics.
    """
    now, today_start, week_start, month_start = get_time_boundaries()

    async with SessionLocal() as db:
        # Customers
        total_customers = await db.scalar(select(func.count()).select_from(Customer)) or 0
        new_today = await db.scalar(
            select(func.count()).select_from(Customer).where(Customer.created_at >= today_start)
        ) or 0
        new_week = await db.scalar(
            select(func.count()).select_from(Customer).where(Customer.created_at >= week_start)
        ) or 0
        new_month = await db.scalar(
            select(func.count()).select_from(Customer).where(Customer.created_at >= month_start)
        ) or 0

        # Orders
        total_orders = await db.scalar(select(func.count()).select_from(ServiceOrder)) or 0
        pending_orders = await db.scalar(
            select(func.count()).select_from(ServiceOrder).where(
                ServiceOrder.status.in_(["yangi", "pending"])
            )
        ) or 0
        accepted_orders = await db.scalar(
            select(func.count()).select_from(ServiceOrder).where(
                ServiceOrder.status.in_(["qabul_qilindi", "accepted"])
            )
        ) or 0
        rejected_orders = await db.scalar(
            select(func.count()).select_from(ServiceOrder).where(
                ServiceOrder.status.in_(["rad_etildi", "rejected"])
            )
        ) or 0

        # Announcements
        published_news = await db.scalar(
            select(func.count()).select_from(Announcement).where(Announcement.is_published == True)
        ) or 0

    all_services = services_manager.get_all_services()
    active_services = sum(1 for s in all_services if s.get("is_active", True))

    return {
        "now": now,
        "total_customers": total_customers,
        "new_today": new_today,
        "new_week": new_week,
        "new_month": new_month,
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "accepted_orders": accepted_orders,
        "rejected_orders": rejected_orders,
        "total_services": len(all_services),
        "active_services": active_services,
        "published_news": published_news,
    }


def format_dashboard_text(stats: dict) -> str:
    now_str = stats["now"].strftime("%d.%m.%Y, %H:%M")
    return (
        "📊 <b>AZAMAI BUSINESS — ASOSIY HISOBOT</b>\n"
        f"🕒 <i>Holat: {now_str} (Asia/Tashkent)</i>\n\n"
        "👥 <b>Mijozlar statistikasi:</b>\n"
        f"• Jami mijozlar: <b>{stats['total_customers']:,}</b>\n"
        f"• Bugun qo‘shilganlar: <b>+{stats['new_today']}</b>\n"
        f"• Bu hafta: <b>+{stats['new_week']}</b>\n"
        f"• Bu oy: <b>+{stats['new_month']}</b>\n\n"
        "📥 <b>Buyurtmalar statistikasi:</b>\n"
        f"• Jami buyurtmalar: <b>{stats['total_orders']:,}</b>\n"
        f"• ⏳ Kutilayotgan: <b>{stats['pending_orders']}</b>\n"
        f"• ✅ Qabul qilingan: <b>{stats['accepted_orders']}</b>\n"
        f"• ❌ Rad etilgan: <b>{stats['rejected_orders']}</b>\n\n"
        "📋 <b>Biznes kontenti:</b>\n"
        f"• Xizmatlar: <b>{stats['total_services']} ta</b> (🟢 {stats['active_services']} faol)\n"
        f"• E'lonlar: <b>{stats['published_news']} ta</b> chop etilgan"
    )


async def get_period_report(period: str) -> str:
    """
    period: 'today' | 'week' | 'month'
    """
    now, today_start, week_start, month_start = get_time_boundaries()

    if period == "today":
        start_dt = today_start
        title = f"📅 <b>BUGUNGI HISOBOT ({now.strftime('%d.%m.%Y')})</b>"
    elif period == "week":
        start_dt = week_start
        title = f"📅 <b>HAFTALIK HISOBOT ({week_start.strftime('%d.%m')} — {now.strftime('%d.%m.%Y')})</b>"
    else:  # month
        start_dt = month_start
        title = f"📅 <b>OYLIK HISOBOT ({now.strftime('%B %Y')})</b>"

    async with SessionLocal() as db:
        new_customers = await db.scalar(
            select(func.count()).select_from(Customer).where(Customer.created_at >= start_dt)
        ) or 0
        new_orders = await db.scalar(
            select(func.count()).select_from(ServiceOrder).where(ServiceOrder.created_at >= start_dt)
        ) or 0
        accepted_orders = await db.scalar(
            select(func.count()).select_from(ServiceOrder).where(
                ServiceOrder.created_at >= start_dt,
                ServiceOrder.status.in_(["qabul_qilindi", "accepted"]),
            )
        ) or 0
        pending_orders = await db.scalar(
            select(func.count()).select_from(ServiceOrder).where(
                ServiceOrder.created_at >= start_dt,
                ServiceOrder.status.in_(["yangi", "pending"]),
            )
        ) or 0
        rejected_orders = await db.scalar(
            select(func.count()).select_from(ServiceOrder).where(
                ServiceOrder.created_at >= start_dt,
                ServiceOrder.status.in_(["rad_etildi", "rejected"]),
            )
        ) or 0

    return (
        f"{title}\n\n"
        f"🆕 <b>Yangi mijozlar:</b> {new_customers}\n"
        f"📥 <b>Yangi buyurtmalar:</b> {new_orders}\n"
        f"• ✅ Qabul qilingan: {accepted_orders}\n"
        f"• ⏳ Kutilayotgan: {pending_orders}\n"
        f"• ❌ Rad etilgan: {rejected_orders}\n\n"
        f"🕒 <i>Hisobot vaqti: {now.strftime('%H:%M')}</i>"
    )


async def send_daily_report_job(bot: Bot) -> bool:
    """
    Computes today's report, verifies idempotency in DailyReportLog,
    and sends report to all admins.
    """
    now = now_in_tz()
    today_str = now.strftime("%Y-%m-%d")

    async with SessionLocal() as db:
        existing_log = await db.scalar(
            select(DailyReportLog).where(DailyReportLog.report_date == today_str)
        )
        if existing_log:
            log.info("Daily report for %s already sent. Skipping.", today_str)
            return False

        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        new_customers = await db.scalar(
            select(func.count()).select_from(Customer).where(Customer.created_at >= today_start)
        ) or 0
        orders_today = await db.scalar(
            select(func.count()).select_from(ServiceOrder).where(ServiceOrder.created_at >= today_start)
        ) or 0
        accepted_today = await db.scalar(
            select(func.count()).select_from(ServiceOrder).where(
                ServiceOrder.created_at >= today_start,
                ServiceOrder.status.in_(["qabul_qilindi", "accepted"]),
            )
        ) or 0
        pending_today = await db.scalar(
            select(func.count()).select_from(ServiceOrder).where(
                ServiceOrder.created_at >= today_start,
                ServiceOrder.status.in_(["yangi", "pending"]),
            )
        ) or 0
        rejected_today = await db.scalar(
            select(func.count()).select_from(ServiceOrder).where(
                ServiceOrder.created_at >= today_start,
                ServiceOrder.status.in_(["rad_etildi", "rejected"]),
            )
        ) or 0

        report_text = (
            "📊 <b>KUNLIK HISOBOT</b>\n\n"
            f"📅 <b>Sana:</b> {now.strftime('%d.%m.%Y')}\n\n"
            f"🆕 <b>Yangi mijozlar:</b> {new_customers}\n"
            f"📥 <b>Yangi buyurtmalar:</b> {orders_today}\n"
            f"✅ <b>Qabul qilingan:</b> {accepted_today}\n"
            f"⏳ <b>Kutilayotgan:</b> {pending_today}\n"
            f"❌ <b>Rad etilgan:</b> {rejected_today}"
        )

        sent_count = await notify_admins(bot, report_text)

        # Log completion to DB for idempotency
        log_entry = DailyReportLog(
            report_date=today_str,
            sent_at=now,
            recipients_count=sent_count,
            summary_text=report_text,
        )
        db.add(log_entry)
        await db.commit()

        log.info("Daily report for %s sent to %d admins.", today_str, sent_count)
        return True


async def daily_report_scheduler(bot: Bot) -> None:
    """
    Background asynchronous loop that checks every 30 seconds
    if current Asia/Tashkent time has reached settings.daily_report_time (e.g. 21:00).
    """
    log.info("Daily report scheduler started for timezone %s (time: %s).", settings.timezone, settings.daily_report_time)

    # Parse target hour and minute
    target_hour = 21
    target_minute = 0
    try:
        parts = settings.daily_report_time.split(":")
        target_hour = int(parts[0])
        target_minute = int(parts[1]) if len(parts) > 1 else 0
    except Exception:
        pass

    while True:
        try:
            now = now_in_tz()
            # If current time is >= target_hour:target_minute, try to send
            if (now.hour == target_hour and now.minute >= target_minute) or (now.hour > target_hour):
                await send_daily_report_job(bot)
        except Exception as exc:
            log.error("Error in daily_report_scheduler loop: %s", exc)

        # Sleep 30 seconds before next check
        await asyncio.sleep(30)
