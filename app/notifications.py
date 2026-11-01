"""
Centralized Notification Service for AzamAI Business Bot.
Sends real-time admin alerts for new users, new service orders, status updates,
and delivers customer decision messages.
"""
from datetime import datetime
from html import escape
import logging
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.config import settings
from app.models import Customer, ServiceOrder

log = logging.getLogger(__name__)


def _now_tashkent() -> datetime:
    try:
        return datetime.now(ZoneInfo(settings.timezone))
    except Exception:
        return datetime.now()


def _format_date(dt: datetime | None) -> str:
    if not dt:
        dt = _now_tashkent()
    elif dt.tzinfo is None:
        try:
            dt = dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(settings.timezone))
        except Exception:
            pass
    return dt.strftime("%d.%m.%Y, %H:%M")


def order_notification_keyboard(order_id: int, telegram_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"ord_acc_{order_id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"ord_rej_{order_id}"),
            ],
            [
                InlineKeyboardButton(
                    text="💬 Mijoz bilan bog'lanish",
                    url=f"tg://user?id={telegram_id}",
                )
            ],
        ]
    )


async def notify_admins(
    bot: Bot,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    photo_file_id: str | None = None,
) -> int:
    """
    Sends notification to all configured ADMIN_IDS.
    Returns the count of successfully notified admins.
    """
    success = 0
    for admin_id in settings.admins:
        try:
            if photo_file_id:
                await bot.send_photo(
                    chat_id=admin_id,
                    photo=photo_file_id,
                    caption=text,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                )
            else:
                await bot.send_message(
                    chat_id=admin_id,
                    text=text,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                )
            success += 1
        except Exception as exc:
            log.warning("Failed to notify admin %s: %s", admin_id, exc)
    return success


async def notify_new_customer(bot: Bot, customer: Customer, total_customers: int) -> None:
    """
    Triggered ONLY when a genuinely new user is inserted into the database for the first time.
    """
    tashkent_now = _now_tashkent()
    date_str = tashkent_now.strftime("%d.%m.%Y")
    username_str = f"@{customer.username}" if customer.username else "Mavjud emas"

    text = (
        "🆕 <b>Yangi foydalanuvchi!</b>\n\n"
        f"👤 <b>Ism:</b> {escape(customer.full_name or '—')}\n"
        f"🔗 <b>Username:</b> {escape(username_str)}\n"
        f"🆔 <b>Telegram ID:</b> <code>{customer.telegram_id}</code>\n"
        f"🕒 <b>Sana:</b> {date_str}\n"
        f"📊 <b>Jami foydalanuvchilar:</b> {total_customers}"
    )
    await notify_admins(bot, text)


async def notify_new_order(bot: Bot, order: ServiceOrder) -> None:
    """
    Notifies admins immediately when a service booking request is submitted.
    Includes interactive Accept and Reject buttons.
    """
    date_str = _format_date(order.created_at)
    note_str = escape(order.note) if order.note else "Mavjud emas"

    text = (
        "🔔 <b>YANGI XIZMAT BUYURTMASI!</b>\n\n"
        f"👤 <b>Mijoz:</b> {escape(order.customer_name)}\n"
        f"📞 <b>Telefon:</b> {escape(order.phone)}\n"
        f"💇 <b>Xizmat:</b> {escape(order.service_name)}\n"
        f"💰 <b>Narxi:</b> {escape(order.service_price)}\n"
        f"📝 <b>Izoh:</b> {note_str}\n"
        f"🕒 <b>Sana:</b> {date_str}\n"
        f"🆔 <b>Buyurtma ID:</b> #{order.id}"
    )
    kb = order_notification_keyboard(order.id, order.telegram_id)
    await notify_admins(bot, text, reply_markup=kb)


async def notify_customer_order_status(
    bot: Bot,
    customer_tg_id: int,
    order: ServiceOrder,
    accepted: bool,
) -> bool:
    """
    Sends direct feedback to the customer when their order is accepted or rejected.
    """
    if accepted:
        text = (
            "✅ <b>Buyurtmangiz qabul qilindi!</b>\n\n"
            f"🆔 <b>Buyurtma:</b> #{order.id} — <b>{escape(order.service_name)}</b>\n"
            f"💰 <b>Narxi:</b> {escape(order.service_price)}\n\n"
            "Mutaxassisimiz tez orada siz bilan bog'lanib, vaqtni aniqlashtiradi. Rahmat!"
        )
    else:
        text = (
            "❌ <b>Buyurtma holati</b>\n\n"
            f"Hurmatli mijoz, afsuski <b>#{order.id} — {escape(order.service_name)}</b> bo'yicha buyurtmangiz "
            "hozirda qabul qilinmadi.\n\n"
            "Boshqa vaqtni tanlash yoki qo'shimcha ma'lumot olish uchun operatorimiz bilan bog'lanishingiz mumkin."
        )

    try:
        await bot.send_message(chat_id=customer_tg_id, text=text, parse_mode="HTML")
        return True
    except Exception as exc:
        log.warning("Could not send order status to customer %s: %s", customer_tg_id, exc)
        return False
