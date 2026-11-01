"""
Admin panel handlers for AzamAI Business Bot.
Supports:
- Module 1: News & announcements management and broadcast to all customers.
- Module 2: Order request management (interactive accept/reject with customer feedback).
- Module 3: Live business reports & analytics (dashboard, today, week, month).
- Module 4: Business location and interactive map management.
- Existing service management and business configuration.
"""
import asyncio
from datetime import datetime
from html import escape
import logging
from math import ceil
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import BaseFilter, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select

from app.config import settings
from app.db import SessionLocal
from app.models import (
    Announcement, BroadcastCampaign, Customer, Lead, ServiceOrder
)
from app.keyboards import (
    admin_keyboard,
    admin_service_actions_inline,
    admin_services_list_inline,
    business_fields_inline,
    confirm_add_inline,
    confirm_delete_inline,
    edit_fields_inline,
    main_keyboard,
    pagination_inline,
    services_inline,
    reports_periods_inline,
    admin_location_menu_inline,
    confirm_clear_location_inline,
    admin_news_menu_inline,
    news_preview_inline,
    news_item_actions_inline,
    confirm_delete_news_inline,
    confirm_broadcast_inline,
    order_action_inline,
)
from app import services_manager
from app import location_manager
from app import reports
from app import broadcast
from app.notifications import notify_customer_order_status

log = logging.getLogger(__name__)

admin_router = Router()


# ─────────────────────────────────────────────
# Global admin filter: only admin users' messages are routed here.
# Non-admin messages pass through to the customer router.
# ─────────────────────────────────────────────
class IsAdminFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in settings.admins


admin_router.message.filter(IsAdminFilter())

PAGE_SIZE = 10


# ─────────────────────────────────────────────
# FSM States
# ─────────────────────────────────────────────
class AddServiceFSM(StatesGroup):
    name = State()
    price = State()
    duration = State()
    description = State()
    additional_info = State()
    confirm = State()


class EditServiceFSM(StatesGroup):
    new_value = State()


class EditBusinessFSM(StatesGroup):
    new_value = State()


class AdminLocationFSM(StatesGroup):
    entering_address = State()
    entering_landmark = State()
    entering_coords = State()
    entering_url = State()
    waiting_location_pin = State()


class AdminNewsFSM(StatesGroup):
    title = State()
    text = State()
    photo = State()
    expires_at = State()
    confirm = State()


class QuickBroadcastFSM(StatesGroup):
    text = State()
    confirm = State()


# ─────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────
def is_admin(user_id: int) -> bool:
    return user_id in settings.admins


async def _deny(message: Message) -> None:
    await message.answer("⛔ Sizda admin huquqi yo'q.")


async def _deny_cb(cb: CallbackQuery) -> None:
    await cb.answer("⛔ Ruxsat yo'q.", show_alert=True)


# ─────────────────────────────────────────────
# /admin — open admin panel
# ─────────────────────────────────────────────
@admin_router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await _deny(message)
        return
    await state.clear()
    await message.answer(
        "👨‍💼 <b>Admin paneli</b>\nQuyidagi bo'limlardan birini tanlang:",
        reply_markup=admin_keyboard(),
        parse_mode="HTML",
    )


# /cancel — cancel any ongoing admin operation
@admin_router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    current = await state.get_state()
    if current is None:
        await message.answer("Bekor qilish uchun aktiv jarayon yo'q.", reply_markup=admin_keyboard())
        return
    await state.clear()
    await message.answer("❌ Jarayon bekor qilindi.", reply_markup=admin_keyboard())


# ─────────────────────────────────────────────
# 📊 MODULE 3: Reports & Analytics
# ─────────────────────────────────────────────
@admin_router.message(F.text.in_(["📊 Hisobotlar", "📊 Statistika"]))
async def admin_reports_menu(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    stats = await reports.get_dashboard_stats()
    text = reports.format_dashboard_text(stats)
    await message.answer(text, parse_mode="HTML", reply_markup=reports_periods_inline())


@admin_router.callback_query(F.data == "rep_today")
async def rep_today_cb(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    text = await reports.get_period_report("today")
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reports_periods_inline())
    await cb.answer()


@admin_router.callback_query(F.data == "rep_week")
async def rep_week_cb(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    text = await reports.get_period_report("week")
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reports_periods_inline())
    await cb.answer()


@admin_router.callback_query(F.data == "rep_month")
async def rep_month_cb(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    text = await reports.get_period_report("month")
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reports_periods_inline())
    await cb.answer()


@admin_router.callback_query(F.data.in_(["rep_all", "rep_refresh"]))
async def rep_all_cb(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    stats = await reports.get_dashboard_stats()
    text = reports.format_dashboard_text(stats)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=reports_periods_inline())
    await cb.answer("Yangilandi!")


# ─────────────────────────────────────────────
# 📥 MODULE 2: Order Management & Interactive Accept/Reject
# ─────────────────────────────────────────────
@admin_router.message(F.text.in_(["📥 Buyurtmalar", "📥 Kontaktlar"]))
async def admin_orders_menu(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    await _send_orders_page(message, page=0)


async def _send_orders_page(message: Message, page: int) -> None:
    async with SessionLocal() as db:
        total = await db.scalar(select(func.count()).select_from(ServiceOrder)) or 0
        rows = (
            await db.scalars(
                select(ServiceOrder)
                .order_by(ServiceOrder.id.desc())
                .offset(page * PAGE_SIZE)
                .limit(PAGE_SIZE)
            )
        ).all()

    if not total:
        await message.answer("Hozircha xizmat buyurtmalari yo'q.", reply_markup=admin_keyboard())
        return

    total_pages = ceil(total / PAGE_SIZE)
    lines = []
    for o in rows:
        status_icon = "⏳" if o.status == "yangi" else ("✅" if o.status == "qabul_qilindi" else "❌")
        created_str = o.created_at.strftime("%d.%m %H:%M") if o.created_at else "—"
        note_str = f" | 📝 {escape(o.note)}" if o.note else ""
        lines.append(
            f"{status_icon} <b>#{o.id} — {escape(o.service_name)}</b> ({escape(o.service_price)})\n"
            f"   👤 {escape(o.customer_name)} | 📞 {escape(o.phone)} | 🕒 {created_str}{note_str}"
        )

    text = (
        f"📥 <b>Xizmat buyurtmalari</b> (sahifa {page + 1}/{total_pages}, jami: {total})\n\n"
        + "\n\n".join(lines)
    )
    markup = pagination_inline(page, total_pages, "orders")
    await message.answer(text, parse_mode="HTML", reply_markup=markup)


@admin_router.callback_query(F.data.startswith("orders_page_"))
async def orders_page_cb(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    page = int(cb.data.split("_")[-1])
    await cb.message.delete()
    await _send_orders_page(cb.message, page=page)
    await cb.answer()


@admin_router.callback_query(F.data.startswith("ord_acc_"))
async def order_accept_cb(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    order_id = int(cb.data.replace("ord_acc_", ""))

    async with SessionLocal() as db:
        order = await db.get(ServiceOrder, order_id)
        if not order:
            await cb.answer("Buyurtma topilmadi.", show_alert=True)
            return

        if order.status != "yangi":
            await cb.answer(f"Bu buyurtma allaqachon ko'rib chiqilgan ({order.status}).", show_alert=True)
            return

        order.status = "qabul_qilindi"
        order.handled_by_admin = cb.from_user.id
        order.updated_at = datetime.now(ZoneInfo(settings.timezone))
        await db.commit()
        await db.refresh(order)

    # Send feedback to customer
    await notify_customer_order_status(cb.bot, order.telegram_id, order, accepted=True)

    # Edit admin notification message
    admin_name = escape(cb.from_user.full_name or "Admin")
    updated_caption = (
        cb.message.html_text + f"\n\n✅ <b>Qabul qildi:</b> {admin_name} (ID: <code>{cb.from_user.id}</code>)"
    )
    try:
        await cb.message.edit_text(updated_caption, parse_mode="HTML", reply_markup=None)
    except Exception:
        pass

    await cb.answer("✅ Buyurtma qabul qilindi va mijozga xabar berildi!", show_alert=True)


@admin_router.callback_query(F.data.startswith("ord_rej_"))
async def order_reject_cb(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    order_id = int(cb.data.replace("ord_rej_", ""))

    async with SessionLocal() as db:
        order = await db.get(ServiceOrder, order_id)
        if not order:
            await cb.answer("Buyurtma topilmadi.", show_alert=True)
            return

        if order.status != "yangi":
            await cb.answer(f"Bu buyurtma allaqachon ko'rib chiqilgan ({order.status}).", show_alert=True)
            return

        order.status = "rad_etildi"
        order.handled_by_admin = cb.from_user.id
        order.updated_at = datetime.now(ZoneInfo(settings.timezone))
        await db.commit()
        await db.refresh(order)

    # Send feedback to customer
    await notify_customer_order_status(cb.bot, order.telegram_id, order, accepted=False)

    admin_name = escape(cb.from_user.full_name or "Admin")
    updated_caption = (
        cb.message.html_text + f"\n\n❌ <b>Rad etdi:</b> {admin_name} (ID: <code>{cb.from_user.id}</code>)"
    )
    try:
        await cb.message.edit_text(updated_caption, parse_mode="HTML", reply_markup=None)
    except Exception:
        pass

    await cb.answer("❌ Buyurtma rad etildi va mijozga xabar berildi.", show_alert=True)


# ─────────────────────────────────────────────
# 📰 MODULE 1: News & Announcements Management
# ─────────────────────────────────────────────
@admin_router.message(F.text.in_(["📰 Yangiliklar", "📰 Yangiliklarni boshqarish"]))
async def admin_news_menu(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "📰 <b>Yangiliklar va e'lonlar bo'limi</b>\n\n"
        "Bu yerda mijozlar uchun yangiliklar, chegirmalar va aksiyalarni yaratishingiz, "
        "tahrirlashingiz hamda barcha foydalanuvchilarga xabar yuborishingiz mumkin.",
        parse_mode="HTML",
        reply_markup=admin_news_menu_inline(),
    )


@admin_router.callback_query(F.data == "news_create_new")
async def news_create_new_cb(cb: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    await state.set_state(AdminNewsFSM.title)
    await cb.message.answer(
        "📰 <b>Yangi e'lon yaratish</b>\n\n"
        "1️⃣ E'lon sarlavhasini kiriting:\n"
        "<i>(Masalan: 🎉 Yangi aksiya!)</i>\n\n"
        "<i>Bekor qilish: /cancel</i>",
        parse_mode="HTML",
    )
    await cb.answer()


@admin_router.message(AdminNewsFSM.title)
async def news_step_title(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    title = message.text.strip() if message.text else ""
    if not title or len(title) > 200:
        await message.answer("❗ Sarlavha bo'sh bo'lmasligi va 200 belgidan oshmasligi kerak.")
        return
    await state.update_data(title=title)
    await state.set_state(AdminNewsFSM.text)
    await message.answer(
        "2️⃣ E'lon matnini kiriting:\n"
        "<i>(Masalan: Manikyur xizmatlariga 20% chegirma taqdim etiladi!)</i>",
        parse_mode="HTML",
    )


@admin_router.message(AdminNewsFSM.text)
async def news_step_text(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    body = message.text.strip() if message.text else ""
    if not body or len(body) > 3000:
        await message.answer("❗ Matn bo'sh bo'lmasligi va 3000 belgidan oshmasligi kerak.")
        return
    await state.update_data(body=body)
    await state.set_state(AdminNewsFSM.photo)
    await message.answer(
        "3️⃣ Rasm yuklang (ixtiyoriy):\n"
        "<i>E'lon uchun rasm yuboring yoki o'tkazib yuborish uchun «-» yozing.</i>",
        parse_mode="HTML",
    )


@admin_router.message(AdminNewsFSM.photo, F.photo)
async def news_step_photo_upload(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_file_id=photo_id)
    await state.set_state(AdminNewsFSM.expires_at)
    await message.answer(
        "4️⃣ Amal qilish muddatini kiriting (ixtiyoriy):\n"
        "<i>(Masalan: 15.11.2026 yoki «-» yozing)</i>",
        parse_mode="HTML",
    )


@admin_router.message(AdminNewsFSM.photo)
async def news_step_photo_skip(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await state.update_data(photo_file_id=None)
    await state.set_state(AdminNewsFSM.expires_at)
    await message.answer(
        "4️⃣ Amal qilish muddatini kiriting (ixtiyoriy):\n"
        "<i>(Masalan: 15.11.2026 yoki «-» yozing)</i>",
        parse_mode="HTML",
    )


@admin_router.message(AdminNewsFSM.expires_at)
async def news_step_expires(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    raw = message.text.strip() if message.text else ""
    expires_dt = None
    if raw != "-":
        try:
            expires_dt = datetime.strptime(raw, "%d.%m.%Y")
            expires_dt = expires_dt.replace(hour=23, minute=59, tzinfo=ZoneInfo(settings.timezone))
        except Exception:
            await message.answer("❗ Sana formati noto'g'ri (namuna: 15.11.2026). O'tkazib yuborish uchun «-» yozing.")
            return

    await state.update_data(expires_at=expires_dt.isoformat() if expires_dt else None)
    data = await state.get_data()

    preview_text = (
        "📰 <b>E'LON KO'RINIShI (PREVIEW):</b>\n\n"
        f"🎉 <b>{escape(data['title'])}</b>\n\n"
        f"{escape(data['body'])}\n"
    )
    if expires_dt:
        preview_text += f"\n📅 <i>Amal qilish muddati: {expires_dt.strftime('%d.%m.%Y')} gacha</i>"

    await state.set_state(AdminNewsFSM.confirm)
    if data.get("photo_file_id"):
        await message.answer_photo(
            photo=data["photo_file_id"],
            caption=preview_text,
            parse_mode="HTML",
            reply_markup=news_preview_inline(),
        )
    else:
        await message.answer(
            preview_text,
            parse_mode="HTML",
            reply_markup=news_preview_inline(),
        )


@admin_router.callback_query(AdminNewsFSM.confirm, F.data == "news_action_broadcast")
async def news_action_broadcast_cb(cb: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    data = await state.get_data()
    expires_dt = datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None

    # Save announcement to DB as published
    async with SessionLocal() as db:
        ann = Announcement(
            title=data["title"],
            text=data["body"],
            photo_file_id=data.get("photo_file_id"),
            is_published=True,
            expires_at=expires_dt,
        )
        db.add(ann)
        await db.commit()
        await db.refresh(ann)
        ann_id = ann.id

    await state.clear()
    await cb.message.answer(
        "🚀 E'lon saqlandi va barcha mijozlarga yuborilmoqda...\n"
        "Bu biroz vaqt olishi mumkin.",
    )
    await cb.answer()

    # Trigger broadcast in background
    asyncio.create_task(
        broadcast.broadcast_announcement(
            bot=cb.bot,
            announcement_id=ann_id,
            custom_title=data["title"],
            custom_text=data["body"],
            photo_file_id=data.get("photo_file_id"),
            admin_id=cb.from_user.id,
        )
    )


@admin_router.callback_query(AdminNewsFSM.confirm, F.data == "news_action_draft")
async def news_action_draft_cb(cb: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    data = await state.get_data()
    expires_dt = datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None

    async with SessionLocal() as db:
        ann = Announcement(
            title=data["title"],
            text=data["body"],
            photo_file_id=data.get("photo_file_id"),
            is_published=False,
            expires_at=expires_dt,
        )
        db.add(ann)
        await db.commit()

    await state.clear()
    await cb.message.answer(
        "💾 E'lon <b>qoralama</b> sifatida saqlandi (mijozlarga yuborilmadi).",
        parse_mode="HTML",
        reply_markup=admin_keyboard(),
    )
    await cb.answer()


@admin_router.callback_query(F.data == "news_action_cancel")
async def news_action_cancel_cb(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await cb.message.answer("❌ E'lon yaratish bekor qilindi.", reply_markup=admin_keyboard())
    await cb.answer()


@admin_router.callback_query(F.data == "news_list_all")
async def news_list_all_cb(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return

    async with SessionLocal() as db:
        announcements = (await db.scalars(select(Announcement).order_by(Announcement.id.desc()))).all()

    if not announcements:
        await cb.message.answer("Hozircha e'lonlar mavjud emas.", reply_markup=admin_news_menu_inline())
        await cb.answer()
        return

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = []
    for a in announcements:
        status = "🟢" if a.is_published else "🟡"
        buttons.append([InlineKeyboardButton(text=f"{status} #{a.id} {a.title[:30]}", callback_data=f"news_view_{a.id}")])

    buttons.append([InlineKeyboardButton(text="➕ Yangi e'lon", callback_data="news_create_new")])
    buttons.append([InlineKeyboardButton(text="🔙 Yangiliklar menyusi", callback_data="news_menu_main")])

    await cb.message.answer("📋 <b>Barcha e'lonlar ro'yxati:</b>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await cb.answer()


@admin_router.callback_query(F.data == "news_menu_main")
async def news_menu_main_cb(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    await cb.message.answer("📰 <b>Yangiliklar boshqaruvi:</b>", parse_mode="HTML", reply_markup=admin_news_menu_inline())
    await cb.answer()


@admin_router.callback_query(F.data.startswith("news_view_"))
async def news_view_item_cb(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    ann_id = int(cb.data.replace("news_view_", ""))

    async with SessionLocal() as db:
        a = await db.get(Announcement, ann_id)

    if not a:
        await cb.answer("E'lon topilmadi.", show_alert=True)
        return

    status_str = "🟢 Chop etilgan (mijozlarga ko'rinadi)" if a.is_published else "🟡 Qoralama (yashirin)"
    exp_str = a.expires_at.strftime("%d.%m.%Y") if a.expires_at else "Muddatsiz"
    text = (
        f"📰 <b>E'lon #{a.id}</b>\n\n"
        f"📌 <b>Sarlavha:</b> {escape(a.title)}\n"
        f"📝 <b>Matn:</b>\n{escape(a.text)}\n\n"
        f"📊 <b>Holati:</b> {status_str}\n"
        f"📅 <b>Muddati:</b> {exp_str}\n"
        f"🕒 <b>Yaratilgan:</b> {a.created_at.strftime('%d.%m.%Y %H:%M') if a.created_at else '—'}"
    )
    kb = news_item_actions_inline(a.id, a.is_published)
    if a.photo_file_id:
        try:
            await cb.message.answer_photo(photo=a.photo_file_id, caption=text, parse_mode="HTML", reply_markup=kb)
            await cb.answer()
            return
        except Exception:
            pass

    await cb.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await cb.answer()


@admin_router.callback_query(F.data.startswith("news_toggle_"))
async def news_toggle_cb(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    ann_id = int(cb.data.replace("news_toggle_", ""))
    async with SessionLocal() as db:
        a = await db.get(Announcement, ann_id)
        if not a:
            await cb.answer("E'lon topilmadi.", show_alert=True)
            return
        a.is_published = not a.is_published
        await db.commit()
        new_status = a.is_published

    status_msg = "🟢 Chop etildi (mijozlarga ko'rinadi)" if new_status else "🔴 Bekor qilindi (yashirildi)"
    await cb.answer(status_msg, show_alert=True)
    # Refresh view
    await news_view_item_cb(cb)


@admin_router.callback_query(F.data.startswith("news_del_"))
async def news_del_cb(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    ann_id = int(cb.data.replace("news_del_", ""))
    await cb.message.answer(
        f"⚠️ <b>#{ann_id} e'lonni o'chirishni tasdiqlaysizmi?</b>",
        parse_mode="HTML",
        reply_markup=confirm_delete_news_inline(ann_id),
    )
    await cb.answer()


@admin_router.callback_query(F.data.startswith("news_confirm_del_"))
async def news_confirm_del_cb(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    ann_id = int(cb.data.replace("news_confirm_del_", ""))
    async with SessionLocal() as db:
        a = await db.get(Announcement, ann_id)
        if a:
            await db.delete(a)
            await db.commit()
    await cb.message.answer("🗑 E'lon o'chirildi.", reply_markup=admin_keyboard())
    await cb.answer()


@admin_router.callback_query(F.data.startswith("news_send_all_"))
async def news_send_all_prompt_cb(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    ann_id = int(cb.data.replace("news_send_all_", ""))
    await cb.message.answer(
        f"📢 <b>#{ann_id} e'lonni barcha mijozlarga yuborishni tasdiqlaysizmi?</b>",
        parse_mode="HTML",
        reply_markup=confirm_broadcast_inline(ann_id),
    )
    await cb.answer()


@admin_router.callback_query(F.data.startswith("news_confirm_send_"))
async def news_confirm_send_cb(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    ann_id = int(cb.data.replace("news_confirm_send_", ""))
    if broadcast.is_broadcasting_active():
        await cb.answer("Hozirda boshqa xabar tarqatish jarayoni ketmoqda. Kuting.", show_alert=True)
        return

    await cb.message.answer("🚀 Xabar yuborish boshlandi. Natija haqida xabar beriladi...")
    await cb.answer()

    asyncio.create_task(
        broadcast.broadcast_announcement(
            bot=cb.bot,
            announcement_id=ann_id,
            admin_id=cb.from_user.id,
        )
    )


# Quick Broadcast button on admin keyboard
@admin_router.message(F.text == "📢 Barchaga xabar yuborish")
async def admin_quick_broadcast_start(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    if broadcast.is_broadcasting_active():
        await message.answer("⚠️ Hozirda boshqa xabar tarqatish jarayoni ketmoqda. Iltimos, kuting.")
        return
    await state.set_state(QuickBroadcastFSM.text)
    await message.answer(
        "📢 <b>Barcha mijozlarga xabar yuborish</b>\n\n"
        "Mijozlarga yuboriladigan xabar matnini kiriting:\n\n"
        "<i>Bekor qilish: /cancel</i>",
        parse_mode="HTML",
    )


@admin_router.message(QuickBroadcastFSM.text)
async def admin_quick_broadcast_text(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    text = message.text.strip() if message.text else ""
    if not text:
        await message.answer("❗ Xabar matni bo'sh bo'lmasligi kerak.")
        return
    await state.update_data(broadcast_text=text)
    await state.set_state(QuickBroadcastFSM.confirm)

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Ha, barchaga yuborilsin!", callback_data="quick_bc_confirm")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="quick_bc_cancel")],
        ]
    )
    await message.answer(
        f"📢 <b>Xabar ko'rinishi:</b>\n\n{escape(text)}\n\n"
        "Barcha mijozlarga yuborishni tasdiqlaysizmi?",
        parse_mode="HTML",
        reply_markup=kb,
    )


@admin_router.callback_query(QuickBroadcastFSM.confirm, F.data == "quick_bc_confirm")
async def quick_bc_confirm_cb(cb: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    data = await state.get_data()
    text = data.get("broadcast_text", "")
    await state.clear()

    await cb.message.answer("🚀 Xabar yuborish boshlandi...")
    await cb.answer()

    asyncio.create_task(
        broadcast.broadcast_announcement(
            bot=cb.bot,
            custom_title="E'lon",
            custom_text=text,
            admin_id=cb.from_user.id,
        )
    )


@admin_router.callback_query(QuickBroadcastFSM.confirm, F.data == "quick_bc_cancel")
async def quick_bc_cancel_cb(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await cb.message.answer("❌ Xabar yuborish bekor qilindi.", reply_markup=admin_keyboard())
    await cb.answer()


# ─────────────────────────────────────────────
# 📍 MODULE 4: Business Location & Map Management
# ─────────────────────────────────────────────
@admin_router.message(F.text == "📍 Manzil va xarita")
async def admin_location_menu(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    loc = await location_manager.get_location()
    text = location_manager.format_admin_location_text(loc)
    has_coords = bool(loc and loc.latitude is not None and loc.longitude is not None)
    has_url = bool(loc and loc.google_maps_url)
    await message.answer(text, parse_mode="HTML", reply_markup=admin_location_menu_inline(has_coords, has_url))


@admin_router.callback_query(F.data == "loc_edit_address")
async def loc_edit_address_cb(cb: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    await state.set_state(AdminLocationFSM.entering_address)
    await cb.message.answer(
        "🏢 <b>Biznes manzilini kiriting:</b>\n"
        "<i>(Masalan: Toshkent sh., Chilonzor tumani, 9-mavze, 12-uy)</i>\n\n"
        "<i>Bekor qilish: /cancel</i>",
        parse_mode="HTML",
    )
    await cb.answer()


@admin_router.message(AdminLocationFSM.entering_address)
async def loc_save_address(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    addr = message.text.strip() if message.text else ""
    if not addr or len(addr) > 500:
        await message.answer("❗ Manzil matni 500 belgidan oshmasligi kerak.")
        return
    await location_manager.save_location(address=addr)
    await state.clear()
    await message.answer(f"✅ Manzil saqlandi:\n<b>{escape(addr)}</b>", parse_mode="HTML", reply_markup=admin_keyboard())


@admin_router.callback_query(F.data == "loc_edit_landmark")
async def loc_edit_landmark_cb(cb: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    await state.set_state(AdminLocationFSM.entering_landmark)
    await cb.message.answer(
        "ℹ️ <b>Mo'ljalni kiriting:</b>\n"
        "<i>(Masalan: Mirzo Ulug'bek metrosi yaqinida)</i>\n\n"
        "<i>Bekor qilish: /cancel</i>",
        parse_mode="HTML",
    )
    await cb.answer()


@admin_router.message(AdminLocationFSM.entering_landmark)
async def loc_save_landmark(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    landmark = message.text.strip() if message.text else ""
    await location_manager.save_location(landmark=landmark)
    await state.clear()
    await message.answer(f"✅ Mo'ljal saqlandi:\n<b>{escape(landmark)}</b>", parse_mode="HTML", reply_markup=admin_keyboard())


@admin_router.callback_query(F.data == "loc_prompt_pin")
async def loc_prompt_pin_cb(cb: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    await state.set_state(AdminLocationFSM.waiting_location_pin)
    await cb.message.answer(
        "📍 <b>Telegram orqali lokatsiya yuborish:</b>\n\n"
        "Telegram xabar yozish maydonidagi 📎 (qisqich) tugmasini bosing va <b>Location (Geopozitsiya)</b> bo'limidan "
        "biznes lokatsiyasini yuboring.\n\n"
        "<i>Bekor qilish: /cancel</i>",
        parse_mode="HTML",
    )
    await cb.answer()


@admin_router.message(AdminLocationFSM.waiting_location_pin, F.location)
async def loc_save_pin(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    lat = message.location.latitude
    lon = message.location.longitude
    await location_manager.save_location(latitude=lat, longitude=lon)
    await state.clear()
    await message.answer(
        f"✅ Lokatsiya koordinatalari saqlandi!\n"
        f"🌐 Kenglik: <code>{lat}</code>, Uzunlik: <code>{lon}</code>",
        parse_mode="HTML",
        reply_markup=admin_keyboard(),
    )


@admin_router.callback_query(F.data == "loc_edit_coords")
async def loc_edit_coords_cb(cb: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    await state.set_state(AdminLocationFSM.entering_coords)
    await cb.message.answer(
        "🌐 <b>Koordinatalarni qo'lda kiriting:</b>\n"
        "Kenglik va uzunlikni vergul bilan ajratib yuboring:\n"
        "<i>(Masalan: 41.2995, 69.2401)</i>\n\n"
        "<i>Bekor qilish: /cancel</i>",
        parse_mode="HTML",
    )
    await cb.answer()


@admin_router.message(AdminLocationFSM.entering_coords)
async def loc_save_manual_coords(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    raw = message.text.strip() if message.text else ""
    parts = raw.split(",") if "," in raw else raw.split()
    if len(parts) != 2:
        await message.answer("❗ Iltimos, ikkita raqamni vergul bilan kiriting (masalan: 41.2995, 69.2401):")
        return
    ok, lat, lon, err = location_manager.validate_coordinates(parts[0], parts[1])
    if not ok:
        await message.answer(f"❗ {err}")
        return

    await location_manager.save_location(latitude=lat, longitude=lon)
    await state.clear()
    await message.answer(
        f"✅ Koordinatalar saqlandi!\n🌐 <code>{lat}, {lon}</code>",
        parse_mode="HTML",
        reply_markup=admin_keyboard(),
    )


@admin_router.callback_query(F.data == "loc_edit_url")
async def loc_edit_url_cb(cb: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    await state.set_state(AdminLocationFSM.entering_url)
    await cb.message.answer(
        "🗺 <b>Google Maps havolasini kiriting:</b>\n"
        "<i>(Masalan: https://maps.google.com/?q=41.2995,69.2401 yoki qisqa havola)</i>\n\n"
        "<i>Bekor qilish: /cancel</i>",
        parse_mode="HTML",
    )
    await cb.answer()


@admin_router.message(AdminLocationFSM.entering_url)
async def loc_save_url(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    url = message.text.strip() if message.text else ""
    ok, err = location_manager.validate_maps_url(url)
    if not ok:
        await message.answer(f"❗ {err}")
        return
    await location_manager.save_location(google_maps_url=url)
    await state.clear()
    await message.answer(
        f"✅ Google Maps havolasi saqlandi:\n{escape(url)}",
        parse_mode="HTML",
        reply_markup=admin_keyboard(),
    )


@admin_router.callback_query(F.data == "loc_preview_customer")
async def loc_preview_customer_cb(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    loc = await location_manager.get_location()
    text = location_manager.format_customer_location_text(loc)
    has_coords = bool(loc and loc.latitude is not None and loc.longitude is not None)
    maps_url = loc.google_maps_url if loc else None

    from app.keyboards import customer_location_inline
    kb = customer_location_inline(maps_url, has_coords)
    await cb.message.answer("👁 <b>Mijoz ko'rinishi (Preview):</b>\n\n" + text, parse_mode="HTML", reply_markup=kb)
    await cb.answer()


@admin_router.callback_query(F.data == "loc_clear_prompt")
async def loc_clear_prompt_cb(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    await cb.message.answer("⚠️ <b>Manzil ma'lumotlarini tozalashni tasdiqlaysizmi?</b>", parse_mode="HTML", reply_markup=confirm_clear_location_inline())
    await cb.answer()


@admin_router.callback_query(F.data == "loc_clear_confirm")
async def loc_clear_confirm_cb(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    await location_manager.clear_location()
    await cb.message.answer("🗑 Manzil ma'lumotlari tozalandi.", reply_markup=admin_keyboard())
    await cb.answer()


@admin_router.callback_query(F.data == "loc_cancel")
async def loc_cancel_cb(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await cb.message.answer("Admin paneli:", reply_markup=admin_keyboard())
    await cb.answer()


# ─────────────────────────────────────────────
# 👥 Customers (paginated)
# ─────────────────────────────────────────────
@admin_router.message(F.text == "👥 Mijozlar")
async def admin_customers(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    await _send_customers_page(message, page=0)


async def _send_customers_page(message: Message, page: int) -> None:
    async with SessionLocal() as db:
        total = await db.scalar(select(func.count()).select_from(Customer)) or 0
        rows = (
            await db.scalars(
                select(Customer).order_by(Customer.id.desc())
                .offset(page * PAGE_SIZE).limit(PAGE_SIZE)
            )
        ).all()
    if not total:
        await message.answer("Hozircha ro'yxatdan o'tgan mijoz yo'q.", reply_markup=admin_keyboard())
        return
    total_pages = ceil(total / PAGE_SIZE)
    lines = []
    for c in rows:
        username = f"@{escape(c.username)}" if c.username else "—"
        reg = c.created_at.strftime("%Y-%m-%d") if c.created_at else "—"
        lines.append(
            f"• <b>{escape(c.full_name or '?')}</b> | {username}\n"
            f"  🆔 <code>{c.telegram_id}</code> | 📅 {reg}"
        )
    text = (
        f"👥 <b>Mijozlar</b> (sahifa {page + 1}/{total_pages}, jami: {total})\n\n"
        + "\n\n".join(lines)
    )
    markup = pagination_inline(page, total_pages, "cust")
    await message.answer(text, parse_mode="HTML", reply_markup=markup)


@admin_router.callback_query(F.data.startswith("cust_page_"))
async def customers_page_cb(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    page = int(cb.data.split("_")[-1])
    await cb.message.delete()
    await _send_customers_page(cb.message, page=page)
    await cb.answer()


# ─────────────────────────────────────────────
# 📋 Admin: View All Services List & Details
# ─────────────────────────────────────────────
@admin_router.message(F.text.in_(["📋 Xizmatlar ro'yxati", "📋 Xizmatlar"]))
async def admin_services_list(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    services = services_manager.get_all_services()
    if not services:
        await message.answer(
            "📋 Hozircha xizmatlar ro'yxati bo'sh.",
            reply_markup=admin_services_list_inline(services),
        )
        return

    lines = []
    for i, s in enumerate(services, 1):
        status = "🟢 Faol" if s.get("is_active", True) else "🔴 Nofaol"
        desc = f"\n   📝 {escape(s.get('description', ''))[:80]}..." if s.get("description") else ""
        lines.append(
            f"{i}. <b>{escape(s['name'])}</b> ({status})\n"
            f"   💰 {escape(s.get('price', '—'))} | ⏱ {escape(s.get('duration', '—'))}"
            f"{desc}"
        )

    text = (
        "📋 <b>Barcha xizmatlar ro'yxati:</b>\n\n"
        + "\n\n".join(lines)
        + "\n\n👇 <i>Batafsil ko'rish, tahrirlash yoki o'chirish uchun xizmatni tanlang:</i>"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=admin_services_list_inline(services))


@admin_router.callback_query(F.data == "admin_list_services")
async def admin_list_services_cb(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    services = services_manager.get_all_services()
    lines = []
    for i, s in enumerate(services, 1):
        status = "🟢 Faol" if s.get("is_active", True) else "🔴 Nofaol"
        lines.append(f"{i}. <b>{escape(s['name'])}</b> ({status}) — {escape(s.get('price', '—'))}")
    text = (
        "📋 <b>Barcha xizmatlar:</b>\n\n"
        + ("\n".join(lines) if lines else "Xizmatlar yo'q.")
        + "\n\n👇 <i>Kerakli xizmat ustiga bosing:</i>"
    )
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=admin_services_list_inline(services))
    await cb.answer()


@admin_router.callback_query(F.data.startswith("admin_view_svc_"))
async def admin_view_service_cb(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    srv_id = cb.data.replace("admin_view_svc_", "")
    s = services_manager.get_service_by_id(srv_id)
    if not s:
        await cb.answer("Xizmat topilmadi.", show_alert=True)
        return

    status_emoji = "🟢 Faol" if s.get("is_active", True) else "🔴 Nofaol"
    desc = escape(s.get("description", "")) or "<i>(Kiritilmagan)</i>"
    add_info = escape(s.get("additional_info", "")) or "<i>(Kiritilmagan)</i>"
    text = (
        f"📋 <b>{escape(s['name'])}</b> ({status_emoji})\n\n"
        f"🆔 <b>ID:</b> <code>{escape(s.get('id', '—'))}</code>\n"
        f"💰 <b>Narxi:</b> {escape(s.get('price', '—'))}\n"
        f"⏱ <b>Davomiyligi:</b> {escape(s.get('duration', '—'))}\n\n"
        f"📝 <b>Tavsifi:</b>\n{desc}\n\n"
        f"✨ <b>Qo'shimcha ma'lumot:</b>\n{add_info}\n\n"
        f"📅 <b>Yaratilgan:</b> {escape(s.get('created_at', '—'))}\n"
        f"🔄 <b>Yangilangan:</b> {escape(s.get('updated_at', '—'))}"
    )
    await cb.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=admin_service_actions_inline(srv_id, s.get("is_active", True)),
    )
    await cb.answer()


# ─────────────────────────────────────────────
# ➕ Add Service Flow
# ─────────────────────────────────────────────
@admin_router.message(F.text.in_(["➕ Yangi xizmat qo'shish", "➕ Xizmat qo'shish"]))
async def admin_add_service_start(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AddServiceFSM.name)
    await message.answer(
        "➕ <b>Yangi xizmat qo'shish</b>\n\n"
        "1️⃣ Xizmat nomini kiriting:\n"
        "<i>(Masalan: Pedikyur)</i>\n\n"
        "<i>Bekor qilish: /cancel</i>",
        parse_mode="HTML",
    )


@admin_router.callback_query(F.data == "admin_add_svc_quick")
async def admin_add_svc_quick_cb(cb: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    await state.set_state(AddServiceFSM.name)
    await cb.message.answer(
        "➕ <b>Yangi xizmat qo'shish</b>\n\n"
        "1️⃣ Xizmat nomini kiriting:\n"
        "<i>(Masalan: Pedikyur)</i>\n\n"
        "<i>Bekor qilish: /cancel</i>",
        parse_mode="HTML",
    )
    await cb.answer()


@admin_router.message(AddServiceFSM.name)
async def add_service_name(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    name = message.text.strip() if message.text else ""
    if not name or len(name) > 200:
        await message.answer("❗ Nomi bo'sh bo'lmasligi va 200 belgidan oshmasligi kerak.")
        return
    await state.update_data(name=name)
    await state.set_state(AddServiceFSM.price)
    await message.answer(f"2️⃣ <b>{escape(name)}</b> narxini kiriting:\n<i>(Masalan: 180 000 so'm)</i>", parse_mode="HTML")


@admin_router.message(AddServiceFSM.price)
async def add_service_price(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    price = message.text.strip() if message.text else ""
    if not price or len(price) > 200:
        await message.answer("❗ Narx bo'sh bo'lmasligi kerak.")
        return
    await state.update_data(price=price)
    await state.set_state(AddServiceFSM.duration)
    await message.answer("3️⃣ Davomiyligini kiriting:\n<i>(Masalan: 60 daqiqa yoki 1-2 soat)</i>", parse_mode="HTML")


@admin_router.message(AddServiceFSM.duration)
async def add_service_duration(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    duration = message.text.strip() if message.text else ""
    await state.update_data(duration=duration)
    await state.set_state(AddServiceFSM.description)
    await message.answer("4️⃣ Batafsil tavsif kiriting:\n<i>(O'tkazib yuborish uchun «-» yozing)</i>", parse_mode="HTML")


@admin_router.message(AddServiceFSM.description)
async def add_service_description(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    raw = message.text.strip() if message.text else ""
    desc = "" if raw == "-" else raw
    await state.update_data(description=desc)
    await state.set_state(AddServiceFSM.additional_info)
    await message.answer("5️⃣ Qo'shimcha ma'lumot kiriting:\n<i>(O'tkazib yuborish uchun «-» yozing)</i>", parse_mode="HTML")


@admin_router.message(AddServiceFSM.additional_info)
async def add_service_additional_info(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    raw = message.text.strip() if message.text else ""
    add_info = "" if raw == "-" else raw
    await state.update_data(additional_info=add_info)
    data = await state.get_data()

    preview = (
        "📋 <b>Yangi xizmat ma'lumotlari:</b>\n\n"
        f"• <b>Nomi:</b> {escape(data['name'])}\n"
        f"• <b>Narxi:</b> {escape(data['price'])}\n"
        f"• <b>Davomiyligi:</b> {escape(data['duration'])}\n"
        f"• <b>Tavsif:</b> {escape(data.get('description') or '—')}\n"
        f"• <b>Qo'shimcha ma'lumot:</b> {escape(data.get('additional_info') or '—')}\n"
        f"• <b>Holati:</b> 🟢 Faol\n\n"
        "Saqlashni tasdiqlaysizmi?"
    )
    await state.set_state(AddServiceFSM.confirm)
    await message.answer(preview, parse_mode="HTML", reply_markup=confirm_add_inline())


@admin_router.callback_query(AddServiceFSM.confirm, F.data == "add_svc_confirm")
async def add_service_confirm_cb(cb: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    data = await state.get_data()
    try:
        new_srv = services_manager.add_service(
            name=data["name"],
            price=data["price"],
            duration=data["duration"],
            description=data.get("description", ""),
            additional_info=data.get("additional_info", ""),
            is_active=True,
        )
    except Exception as exc:
        log.error("Failed to add service: %s", exc)
        await state.clear()
        await cb.message.edit_text("❌ Saqlashda xatolik yuz berdi.")
        await cb.answer()
        return

    await state.clear()
    await cb.message.edit_text(f"✅ <b>{escape(new_srv['name'])}</b> xizmati saqlandi!", parse_mode="HTML")
    await cb.answer()
    await cb.message.answer("Admin paneli:", reply_markup=admin_keyboard())


@admin_router.callback_query(AddServiceFSM.confirm, F.data == "add_svc_cancel")
async def add_service_cancel_cb(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await cb.message.edit_text("❌ Xizmat qo'shish bekor qilindi.")
    await cb.answer()
    await cb.message.answer("Admin paneli:", reply_markup=admin_keyboard())


# ─────────────────────────────────────────────
# ✏️ Edit Service
# ─────────────────────────────────────────────
@admin_router.message(F.text == "✏️ Xizmatni tahrirlash")
async def admin_edit_service_start(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    services = services_manager.get_all_services()
    if not services:
        await message.answer("Tahrirlash uchun xizmatlar mavjud emas.", reply_markup=admin_keyboard())
        return
    await message.answer("✏️ Qaysi xizmatni tahrirlash kerak?", reply_markup=services_inline(services, "edit"))


@admin_router.callback_query(F.data.startswith("svc_edit_"))
@admin_router.callback_query(F.data.startswith("admin_edit_svc_"))
async def edit_service_select_cb(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    srv_id = cb.data.replace("svc_edit_", "").replace("admin_edit_svc_", "")
    s = services_manager.get_service_by_id(srv_id)
    if not s:
        await cb.answer("Xizmat topilmadi.", show_alert=True)
        return

    status_str = "🟢 Faol" if s.get("is_active", True) else "🔴 Nofaol"
    text = (
        f"✏️ <b>{escape(s['name'])}</b> xizmatini tahrirlash\n\n"
        f"• <b>Nomi:</b> {escape(s['name'])}\n"
        f"• <b>Narxi:</b> {escape(s.get('price', '—'))}\n"
        f"• <b>Davomiyligi:</b> {escape(s.get('duration', '—'))}\n"
        f"• <b>Tavsif:</b> {escape(s.get('description', '') or '—')}\n"
        f"• <b>Qo'shimcha:</b> {escape(s.get('additional_info', '') or '—')}\n"
        f"• <b>Holati:</b> {status_str}\n\n"
        "O'zgartirmoqchi bo'lgan maydoningizni tanlang:"
    )
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=edit_fields_inline(srv_id))
    await cb.answer()


@admin_router.callback_query(F.data.startswith("editf_"))
async def edit_service_field_pick_cb(cb: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    parts = cb.data.split("_")
    field = parts[-1]
    srv_id = "_".join(parts[1:-1])

    s = services_manager.get_service_by_id(srv_id)
    if not s:
        await cb.answer("Xizmat topilmadi.", show_alert=True)
        return

    field_names = {
        "name": "Nomi",
        "price": "Narxi",
        "duration": "Davomiyligi",
        "description": "Tavsifi",
        "additional_info": "Qo'shimcha ma'lumoti",
    }
    cur_val = s.get(field, "—")
    await state.update_data(edit_srv_id=srv_id, edit_field=field)
    await state.set_state(EditServiceFSM.new_value)

    await cb.message.edit_text(
        f"✏️ <b>{escape(s['name'])}</b> xizmatining <b>{field_names.get(field, field)}</b> uchun yangi qiymat kiriting:\n\n"
        f"<i>Hozirgi: {escape(str(cur_val))}</i>\n\n"
        f"<i>Bekor qilish: /cancel</i>",
        parse_mode="HTML",
    )
    await cb.answer()


@admin_router.message(EditServiceFSM.new_value)
async def edit_service_save_new_value(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    new_val = message.text.strip() if message.text else ""
    if not new_val or len(new_val) > 2000:
        await message.answer("❗ Qiymat bo'sh bo'lmasligi va 2000 belgidan oshmasligi kerak.")
        return

    data = await state.get_data()
    srv_id = data["edit_srv_id"]
    field = data["edit_field"]
    val_to_save = "" if new_val == "-" else new_val

    updated = services_manager.update_service(srv_id, {field: val_to_save})
    await state.clear()

    if not updated:
        await message.answer("❌ Xizmat topilmadi.", reply_markup=admin_keyboard())
        return

    await message.answer("✅ Muvaffaqiyatli saqlandi!", reply_markup=admin_keyboard())


# ─────────────────────────────────────────────
# 👁 Toggle Service Active Status
# ─────────────────────────────────────────────
@admin_router.message(F.text == "👁 Xizmatni yoqish/o'chirish")
async def admin_toggle_service_start(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    services = services_manager.get_all_services()
    if not services:
        await message.answer("Xizmatlar mavjud emas.", reply_markup=admin_keyboard())
        return
    await message.answer(
        "👁 Faolligini o'zgartirmoqchi bo'lgan xizmatni tanlang:\n"
        "<i>(🟢 Faol — mijozlarga ko'rinadi | 🔴 Nofaol — yashirilgan)</i>",
        parse_mode="HTML",
        reply_markup=services_inline(services, "toggle"),
    )


@admin_router.callback_query(F.data.startswith("svc_toggle_"))
@admin_router.callback_query(F.data.startswith("admin_toggle_svc_"))
async def admin_toggle_service_cb(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    srv_id = cb.data.replace("svc_toggle_", "").replace("admin_toggle_svc_", "")
    new_status, s = services_manager.toggle_service_active(srv_id)
    if not s:
        await cb.answer("Xizmat topilmadi.", show_alert=True)
        return

    status_str = "🟢 Faollashtirildi (mijozlarga ko'rinadi)" if new_status else "🔴 Nofaol qilindi (mijozlardan yashirildi)"
    await cb.answer(f"{s['name']}: {status_str}", show_alert=True)
    await admin_view_service_cb(cb)


# ─────────────────────────────────────────────
# 🗑 Delete Service
# ─────────────────────────────────────────────
@admin_router.message(F.text == "🗑 Xizmatni o'chirish")
async def admin_delete_service_start(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    services = services_manager.get_all_services()
    if not services:
        await message.answer("O'chirish uchun xizmatlar mavjud emas.", reply_markup=admin_keyboard())
        return
    await message.answer("🗑 O'chirmoqchi bo'lgan xizmatni tanlang:", reply_markup=services_inline(services, "del"))


@admin_router.callback_query(F.data.startswith("svc_del_"))
@admin_router.callback_query(F.data.startswith("admin_del_svc_"))
async def delete_service_pick_cb(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    srv_id = cb.data.replace("svc_del_", "").replace("admin_del_svc_", "")
    s = services_manager.get_service_by_id(srv_id)
    if not s:
        await cb.answer("Xizmat topilmadi.", show_alert=True)
        return

    text = (
        f"⚠️ <b>{escape(s['name'])}</b> xizmatini o'chirishni tasdiqlaysizmi?\n\n"
        f"Narxi: {escape(s.get('price', '—'))}\n"
        "Bu amalni ortga qaytarib bo'lmaydi!"
    )
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=confirm_delete_inline(srv_id))
    await cb.answer()


@admin_router.callback_query(F.data.startswith("svc_confirm_del_"))
async def delete_service_confirmed_cb(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    srv_id = cb.data.replace("svc_confirm_del_", "")
    removed = services_manager.delete_service(srv_id)
    if removed:
        await cb.message.edit_text(f"🗑 <b>{escape(removed['name'])}</b> xizmati o'chirildi.", parse_mode="HTML")
    else:
        await cb.message.edit_text("❌ Xizmat topilmadi.")
    await cb.answer()
    await cb.message.answer("Admin paneli:", reply_markup=admin_keyboard())


@admin_router.callback_query(F.data == "svc_cancel")
async def svc_cancel_cb(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await cb.message.edit_text("❌ Bekor qilindi.")
    await cb.answer()
    await cb.message.answer("Admin paneli:", reply_markup=admin_keyboard())


# ─────────────────────────────────────────────
# ⚙️ Business Settings
# ─────────────────────────────────────────────
@admin_router.message(F.text == "⚙️ Biznes sozlamalari")
async def admin_business_settings(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    biz = services_manager.load_business()
    text = (
        "⚙️ <b>Biznes sozlamalari</b>\n\n"
        f"📛 <b>Nomi:</b> {escape(biz.get('name', '—'))}\n"
        f"📄 <b>Tavsif:</b> {escape(biz.get('description', '—'))}\n"
        f"🤝 <b>Operator matni:</b> {escape(biz.get('handoff_text', '—'))}\n"
        f"📏 <b>AI qoidalari:</b> {escape(biz.get('system_rules', '—'))}\n\n"
        "O'zgartirmoqchi bo'lgan ma'lumotni tanlang:"
    )
    await state.clear()
    await message.answer(text, parse_mode="HTML", reply_markup=business_fields_inline())


@admin_router.callback_query(F.data.startswith("biz_field_"))
async def business_field_cb(cb: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    field = cb.data.replace("biz_field_", "")
    labels = {
        "name": "Biznes nomi",
        "description": "Tavsif",
        "handoff_text": "Operator matni",
        "system_rules": "AI qoidalari",
    }
    biz = services_manager.load_business()
    current = biz.get(field, "—")
    await state.update_data(biz_field=field)
    await state.set_state(EditBusinessFSM.new_value)
    await cb.message.edit_text(
        f"✏️ <b>{labels.get(field, field)}</b> uchun yangi qiymat kiriting:\n\n"
        f"<i>Hozirgi: {escape(str(current))}</i>\n\n"
        f"<i>Bekor qilish: /cancel</i>",
        parse_mode="HTML",
    )
    await cb.answer()


@admin_router.callback_query(F.data == "biz_cancel")
async def biz_cancel_cb(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await cb.message.edit_text("❌ Bekor qilindi.")
    await cb.answer()
    await cb.message.answer("Admin paneli:", reply_markup=admin_keyboard())


@admin_router.message(EditBusinessFSM.new_value)
async def business_new_value(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    val = message.text.strip() if message.text else ""
    if not val or len(val) > 2000:
        await message.answer("❗ Qiymat bo'sh bo'lmasligi va 2000 belgidan oshmasligi kerak.")
        return
    data = await state.get_data()
    field = data["biz_field"]
    biz = services_manager.load_business()
    biz[field] = val
    services_manager.save_business(biz)
    await state.clear()
    await message.answer(
        f"✅ <b>{escape(field)}</b> muvaffaqiyatli yangilandi!",
        parse_mode="HTML",
        reply_markup=admin_keyboard(),
    )


# ─────────────────────────────────────────────
# 👤 Customer mode — Switch Back
# ─────────────────────────────────────────────
@admin_router.message(F.text == "👤 Mijoz rejimi")
async def admin_customer_mode(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(
        "👤 Mijoz rejimiga o'tdingiz.\n"
        "Admin paneliga qaytish uchun istalgan vaqt /admin buyrug'ini yuboring.",
        reply_markup=main_keyboard(),
    )
