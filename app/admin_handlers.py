"""
Admin panel handlers for AzamAI Business Bot.
Supports viewing, adding, editing, deleting, activating/deactivating services.
All admin modifications persist immediately to business.json.
Admin authorisation is verified on every action.
"""
import json
import logging
from html import escape
from math import ceil
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select

from app.config import settings
from app.db import SessionLocal
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
)
from app.models import ChatMessage, Customer, Lead, ServiceOrder
from app import services_manager

log = logging.getLogger(__name__)

admin_router = Router()

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


# ─────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────
def is_admin(user_id: int) -> bool:
    return user_id in settings.admins


async def _deny(message: Message) -> None:
    await message.answer("⛔ Sizda admin huquqi yo'q.")


async def _deny_cb(cb: CallbackQuery) -> None:
    await cb.answer("⛔ Ruxsat yo'q.", show_alert=True)


def _fmt_admin_service_detail(s: dict, index: int | None = None) -> str:
    status_emoji = "🟢 Faol" if s.get("is_active", True) else "🔴 Nofaol"
    num_prefix = f"#{index} " if index else ""
    desc = escape(s.get("description", "")) or "<i>(Kiritilmagan)</i>"
    add_info = escape(s.get("additional_info", "")) or "<i>(Kiritilmagan)</i>"
    return (
        f"📋 <b>{num_prefix}{escape(s['name'])}</b> ({status_emoji})\n\n"
        f"🆔 <b>ID:</b> <code>{escape(s.get('id', '—'))}</code>\n"
        f"💰 <b>Narxi:</b> {escape(s.get('price', '—'))}\n"
        f"⏱ <b>Davomiyligi:</b> {escape(s.get('duration', '—'))}\n\n"
        f"📝 <b>Tavsifi:</b>\n{desc}\n\n"
        f"✨ <b>Qo'shimcha ma'lumot:</b>\n{add_info}\n\n"
        f"📅 <b>Yaratilgan:</b> {escape(s.get('created_at', '—'))}\n"
        f"🔄 <b>Yangilangan:</b> {escape(s.get('updated_at', '—'))}"
    )


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
# 📊 Statistics
# ─────────────────────────────────────────────
@admin_router.message(F.text == "📊 Statistika")
async def admin_stats(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await _deny(message)
        return
    async with SessionLocal() as db:
        customers = await db.scalar(select(func.count()).select_from(Customer))
        leads = await db.scalar(select(func.count()).select_from(Lead))
        orders = await db.scalar(select(func.count()).select_from(ServiceOrder))
        messages = await db.scalar(select(func.count()).select_from(ChatMessage))

    all_services = services_manager.get_all_services()
    active_count = sum(1 for s in all_services if s.get("is_active", True))
    inactive_count = len(all_services) - active_count

    await message.answer(
        "📊 <b>Bot statistikasi</b>\n\n"
        f"👥 Mijozlar: <b>{customers or 0}</b>\n"
        f"📥 Kontaktlar (leadlar): <b>{leads or 0}</b>\n"
        f"📦 Xizmat buyurtmalari: <b>{orders or 0}</b>\n"
        f"💬 Saqlangan xabarlar: <b>{messages or 0}</b>\n\n"
        f"📋 Jami xizmatlar: <b>{len(all_services)}</b> ta\n"
        f"   🟢 Faol: <b>{active_count}</b> ta\n"
        f"   🔴 Nofaol: <b>{inactive_count}</b> ta",
        parse_mode="HTML",
        reply_markup=admin_keyboard(),
    )


# ─────────────────────────────────────────────
# 👥 Customers (paginated)
# ─────────────────────────────────────────────
@admin_router.message(F.text == "👥 Mijozlar")
async def admin_customers(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await _deny(message)
        return
    await _send_customers_page(message, page=0)


async def _send_customers_page(message: Message, page: int) -> None:
    async with SessionLocal() as db:
        total = await db.scalar(select(func.count()).select_from(Customer))
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
            f"  🆔 {c.telegram_id} | 📅 {reg}"
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
# 📥 Contacts / Leads (paginated)
# ─────────────────────────────────────────────
@admin_router.message(F.text == "📥 Kontaktlar")
async def admin_leads(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await _deny(message)
        return
    await _send_leads_page(message, page=0)


async def _send_leads_page(message: Message, page: int) -> None:
    async with SessionLocal() as db:
        total = await db.scalar(select(func.count()).select_from(Lead))
        rows = (
            await db.scalars(
                select(Lead).order_by(Lead.id.desc())
                .offset(page * PAGE_SIZE).limit(PAGE_SIZE)
            )
        ).all()
    if not total:
        await message.answer("Hozircha kontakt yo'q.", reply_markup=admin_keyboard())
        return
    total_pages = ceil(total / PAGE_SIZE)
    lines = []
    for lead in rows:
        date = lead.created_at.strftime("%Y-%m-%d %H:%M") if lead.created_at else "—"
        lines.append(
            f"• <b>{escape(lead.name or '?')}</b>\n"
            f"  📞 {escape(lead.phone)} | 🆔 {lead.telegram_id} | 📅 {date}"
        )
    text = (
        f"📥 <b>Kontaktlar</b> (sahifa {page + 1}/{total_pages}, jami: {total})\n\n"
        + "\n\n".join(lines)
    )
    markup = pagination_inline(page, total_pages, "lead")
    await message.answer(text, parse_mode="HTML", reply_markup=markup)


@admin_router.callback_query(F.data.startswith("lead_page_"))
async def leads_page_cb(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await _deny_cb(cb)
        return
    page = int(cb.data.split("_")[-1])
    await cb.message.delete()
    await _send_leads_page(cb.message, page=page)
    await cb.answer()


# ─────────────────────────────────────────────
# 📋 Admin: View All Services List & Details
# ─────────────────────────────────────────────
@admin_router.message(F.text.in_(["📋 Xizmatlar ro'yxati", "📋 Xizmatlar"]))
async def admin_services_list(message: Message) -> None:
    if not is_admin(message.from_user.id):
        # Let customer router handle it
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
        lines.append(
            f"{i}. <b>{escape(s['name'])}</b> ({status}) — {escape(s.get('price', '—'))}"
        )
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
    text = _fmt_admin_service_detail(s)
    await cb.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=admin_service_actions_inline(srv_id, s.get("is_active", True)),
    )
    await cb.answer()


# ─────────────────────────────────────────────
# ➕ Add Service — Step-by-Step FSM Flow
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
        "<i>Bekor qilish uchun: /cancel</i>",
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
        "<i>Bekor qilish uchun: /cancel</i>",
        parse_mode="HTML",
    )
    await cb.answer()


@admin_router.message(AddServiceFSM.name)
async def add_service_name(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    name = message.text.strip()
    if not name or len(name) > 200:
        await message.answer("❗ Nomi bo'sh bo'lmasligi va 200 belgidan oshmasligi kerak.")
        return
    await state.update_data(name=name)
    await state.set_state(AddServiceFSM.price)
    await message.answer(
        f"2️⃣ <b>{escape(name)}</b> xizmati narxini kiriting:\n"
        "<i>(Masalan: 180 000 so'm)</i>",
        parse_mode="HTML",
    )


@admin_router.message(AddServiceFSM.price)
async def add_service_price(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    price = message.text.strip()
    if not price or len(price) > 200:
        await message.answer("❗ Narx bo'sh bo'lmasligi va 200 belgidan oshmasligi kerak.")
        return
    await state.update_data(price=price)
    await state.set_state(AddServiceFSM.duration)
    await message.answer(
        "3️⃣ Xizmat davomiyligini kiriting:\n"
        "<i>(Masalan: 60 daqiqa yoki 1-2 soat)</i>",
        parse_mode="HTML",
    )


@admin_router.message(AddServiceFSM.duration)
async def add_service_duration(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    duration = message.text.strip()
    if not duration or len(duration) > 200:
        await message.answer("❗ Davomiylik bo'sh bo'lmasligi va 200 belgidan oshmasligi kerak.")
        return
    await state.update_data(duration=duration)
    await state.set_state(AddServiceFSM.description)
    await message.answer(
        "4️⃣ Batafsil tavsif kiriting:\n"
        "<i>(O'tkazib yuborish uchun «-» yozing)</i>",
        parse_mode="HTML",
    )


@admin_router.message(AddServiceFSM.description)
async def add_service_description(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    raw = message.text.strip()
    desc = "" if raw == "-" else raw
    await state.update_data(description=desc)
    await state.set_state(AddServiceFSM.additional_info)
    await message.answer(
        "5️⃣ Qo'shimcha ma'lumot kiriting:\n"
        "<i>(Masalan: Steril vositalardan foydalaniladi. O'tkazib yuborish uchun «-» yozing)</i>",
        parse_mode="HTML",
    )


@admin_router.message(AddServiceFSM.additional_info)
async def add_service_additional_info(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    raw = message.text.strip()
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
    await cb.message.edit_text(
        f"✅ <b>{escape(new_srv['name'])}</b> xizmati muvaffaqiyatli saqlandi!",
        parse_mode="HTML",
    )
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
    await message.answer(
        "✏️ Qaysi xizmatni tahrirlash kerak?",
        reply_markup=services_inline(services, "edit"),
    )


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
    # format: editf_{service_id}_{field}
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
        f"<i>Bekor qilish uchun: /cancel</i>",
        parse_mode="HTML",
    )
    await cb.answer()


@admin_router.message(EditServiceFSM.new_value)
async def edit_service_save_new_value(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    new_val = message.text.strip()
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
        await message.answer("❌ Xizmat topilmadi yoki saqlashda xato.", reply_markup=admin_keyboard())
        return

    await message.answer("✅ Muvaffaqiyatli saqlandi!", reply_markup=admin_keyboard())
    text = _fmt_admin_service_detail(updated)
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=edit_fields_inline(srv_id),
    )


# ─────────────────────────────────────────────
# 👁 Activate / Deactivate (Toggle) Service
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

    # Refresh view
    text = _fmt_admin_service_detail(s)
    await cb.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=admin_service_actions_inline(srv_id, new_status),
    )


# ─────────────────────────────────────────────
# 🗑 Delete Service — Confirmation Flow
# ─────────────────────────────────────────────
@admin_router.message(F.text == "🗑 Xizmatni o'chirish")
async def admin_delete_service_start(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    services = services_manager.get_all_services()
    if not services:
        await message.answer("O'chirish uchun xizmatlar mavjud emas.", reply_markup=admin_keyboard())
        return
    await message.answer(
        "🗑 O'chirmoqchi bo'lgan xizmatni tanlang:",
        reply_markup=services_inline(services, "del"),
    )


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
        f"Bu amalni ortga qaytarib bo'lmaydi!"
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
        await cb.message.edit_text(
            f"🗑 <b>{escape(removed['name'])}</b> xizmati o'chirildi.",
            parse_mode="HTML",
        )
    else:
        await cb.message.edit_text("❌ Xizmat topilmadi yoki allaqachon o'chirilgan.")
    await cb.answer()
    await cb.message.answer("Admin paneli:", reply_markup=admin_keyboard())


# ─────────────────────────────────────────────
# svc_cancel — Universal Inline Cancel
# ─────────────────────────────────────────────
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
        f"<i>Bekor qilish uchun: /cancel</i>",
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
    val = message.text.strip()
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
