"""
Customer-facing handlers for AzamAI Business Bot.
Supports interactive service selection by number, viewing full service details,
placing service booking inquiries with admin notifications, and AI assistant chat.
"""
from datetime import datetime
from html import escape
import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select, func

from app.config import settings
from app.db import SessionLocal
from app.models import Customer, Lead, ChatMessage, ServiceOrder
from app.ai import ask_ai
from app.keyboards import (
    main_keyboard,
    admin_keyboard,
    customer_service_detail_inline,
    customer_services_inline,
    order_contact_keyboard,
)
from app import services_manager

log = logging.getLogger(__name__)

router = Router()


# ─────────────────────────────────────────────
# Customer FSM States
# ─────────────────────────────────────────────
class CustomerServiceFSM(StatesGroup):
    selecting_service = State()


class CustomerOrderFSM(StatesGroup):
    entering_name = State()
    entering_phone = State()


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
async def register_customer(message: Message) -> None:
    async with SessionLocal() as db:
        row = await db.scalar(select(Customer).where(Customer.telegram_id == message.from_user.id))
        if row is None:
            row = Customer(telegram_id=message.from_user.id)
            db.add(row)
        row.full_name = message.from_user.full_name or ""
        row.username = message.from_user.username or ""
        await db.commit()


def _get_number_emoji(n: int) -> str:
    digits = {
        "0": "0️⃣", "1": "1️⃣", "2": "2️⃣", "3": "3️⃣", "4": "4️⃣",
        "5": "5️⃣", "6": "6️⃣", "7": "7️⃣", "8": "8️⃣", "9": "9️⃣",
    }
    s = str(n)
    if n <= 10:
        return "".join(digits.get(c, c) for c in s)
    return f"#{n}"


def _format_services_list(services: list[dict]) -> str:
    lines = []
    for i, s in enumerate(services, 1):
        num_str = _get_number_emoji(i)
        lines.append(f"{num_str} {escape(s['name'])}")
    return (
        "💇 <b>Bizning xizmatlarimiz</b>\n\n"
        + "\n".join(lines)
        + "\n\n👇 <i>Batafsil ma'lumot olish uchun xizmat raqamini yuboring.</i>"
    )


def _format_service_detail(s: dict) -> str:
    name = escape(s.get("name", ""))
    price = escape(s.get("price", "—"))
    duration = escape(s.get("duration", "—"))
    desc = escape(s.get("description", ""))
    add_info = escape(s.get("additional_info", ""))

    text = (
        f"💅 <b>{name}</b>\n\n"
        f"💰 <b>Narxi:</b> {price}\n\n"
        f"⏱ <b>Davomiyligi:</b> {duration}\n\n"
    )
    if desc:
        text += f"📝 <b>Tavsif:</b>\n{desc}\n\n"
    if add_info:
        text += f"✨ <b>Qo'shimcha ma'lumot:</b>\n{add_info}\n"
    return text.strip()


async def _notify_admins_new_order(bot, order_data: dict) -> None:
    text = (
        "🔔 <b>Yangi xizmat buyurtmasi</b>\n\n"
        f"👤 <b>Mijoz:</b> {escape(order_data['name'])}\n"
        f"📞 <b>Telefon:</b> {escape(order_data['phone'])}\n"
        f"💅 <b>Xizmat:</b> {escape(order_data['service_name'])}\n"
        f"💰 <b>Narxi:</b> {escape(order_data['service_price'])}\n"
        f"🕒 <b>Vaqti:</b> {escape(order_data['created_at'])}\n"
        f"🆔 <b>Telegram ID:</b> <code>{order_data['telegram_id']}</code>"
    )
    for admin_id in settings.admins:
        try:
            await bot.send_message(admin_id, text, parse_mode="HTML")
        except Exception as exc:
            log.warning("Could not notify admin %s: %s", admin_id, exc)


# ─────────────────────────────────────────────
# /start
# ─────────────────────────────────────────────
@router.message(Command("start"))
async def start(message: Message, state: FSMContext) -> None:
    await register_customer(message)
    await state.clear()
    biz = services_manager.load_business()

    if message.from_user.id in settings.admins:
        await message.answer(
            f"👨‍💼 Admin sifatida xush kelibsiz!\n"
            f"Biznes: <b>{escape(biz.get('name', ''))}</b>\n"
            f"Admin panelini ochish uchun quyidagi tugmalardan foydalaning:",
            reply_markup=admin_keyboard(),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            f"Assalomu alaykum! 👋\n"
            f"Men <b>{escape(biz.get('name', ''))}</b> virtual yordamchisiman.\n"
            f"Quyidagi menyu orqali xizmatlar bilan tanishishingiz yoki savolingizni yozishingiz mumkin.",
            reply_markup=main_keyboard(),
            parse_mode="HTML",
        )


# ─────────────────────────────────────────────
# 📋 Customer: Services List
# ─────────────────────────────────────────────
@router.message(F.text.in_(["📋 Xizmatlar", "📋 Barcha xizmatlar"]))
async def show_services_list(message: Message, state: FSMContext) -> None:
    await register_customer(message)
    active_services = services_manager.get_active_services()
    if not active_services:
        await message.answer("Hozircha xizmatlar ro'yxati mavjud emas.", reply_markup=main_keyboard())
        return

    text = _format_services_list(active_services)
    await state.set_state(CustomerServiceFSM.selecting_service)
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=customer_services_inline(active_services),
    )


@router.callback_query(F.data == "view_all_services")
async def view_all_services_cb(cb: CallbackQuery, state: FSMContext) -> None:
    active_services = services_manager.get_active_services()
    if not active_services:
        await cb.message.answer("Hozircha xizmatlar mavjud emas.")
        await cb.answer()
        return

    text = _format_services_list(active_services)
    await state.set_state(CustomerServiceFSM.selecting_service)
    await cb.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=customer_services_inline(active_services),
    )
    await cb.answer()


# ─────────────────────────────────────────────
# Customer Selects Service via Inline Button
# ─────────────────────────────────────────────
@router.callback_query(F.data.startswith("cust_select_svc_"))
async def customer_select_service_cb(cb: CallbackQuery, state: FSMContext) -> None:
    srv_id = cb.data.replace("cust_select_svc_", "")
    s = services_manager.get_service_by_id(srv_id)
    if not s or not s.get("is_active", True):
        await cb.answer("Bu xizmat hozirda mavjud emas.", show_alert=True)
        return

    text = _format_service_detail(s)
    await state.set_state(CustomerServiceFSM.selecting_service)
    await cb.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=customer_service_detail_inline(srv_id),
    )
    await cb.answer()


# ─────────────────────────────────────────────
# Customer: Select Service by Sending Number
# ─────────────────────────────────────────────
@router.message(CustomerServiceFSM.selecting_service)
async def process_service_number_selection(message: Message, state: FSMContext) -> None:
    await register_customer(message)
    raw = message.text.strip() if message.text else ""

    # Check if input is an integer (positive, zero, or negative)
    is_number = False
    try:
        num = int(raw)
        is_number = True
    except ValueError:
        is_number = False

    if is_number:
        srv, total = services_manager.get_active_service_by_number(num)
        if srv:
            text = _format_service_detail(srv)
            await message.answer(
                text,
                parse_mode="HTML",
                reply_markup=customer_service_detail_inline(srv["id"]),
            )
        else:
            # Invalid number error
            await message.answer(
                f"⚠️ <b>Noto'g'ri xizmat raqami kiritildi.</b>\n\n"
                f"Mavjud xizmatlar: <b>1</b> dan <b>{total}</b> gacha.\n"
                f"Iltimos, kerakli raqamni yuboring yoki quyidagi ro'yxatdan tanlang.",
                parse_mode="HTML",
            )
        return

    # Non-number input while in selecting state:
    if raw in ["📋 Xizmatlar", "📋 Barcha xizmatlar"]:
        active = services_manager.get_active_services()
        await message.answer(
            _format_services_list(active),
            parse_mode="HTML",
            reply_markup=customer_services_inline(active),
        )
        return

    if raw in ["👨‍💼 Operator", "👨‍💼 Operator bilan bog'lanish"]:
        await state.clear()
        biz = services_manager.load_business()
        await message.answer(biz.get("handoff_text", "Operator bilan bog'laning."))
        return

    if raw == "/cancel":
        await state.clear()
        await message.answer("Xizmat tanlash bekor qilindi.", reply_markup=main_keyboard())
        return

    # User asked a normal question — clear state and pass directly to AI chat!
    await state.clear()
    await ai_chat(message, state)


# ─────────────────────────────────────────────
# 📞 Service Order Request Flow
# ─────────────────────────────────────────────
@router.callback_query(F.data.startswith("order_svc_"))
async def start_service_order_cb(cb: CallbackQuery, state: FSMContext) -> None:
    srv_id = cb.data.replace("order_svc_", "")
    s = services_manager.get_service_by_id(srv_id)
    if not s:
        await cb.answer("Xizmat topilmadi.", show_alert=True)
        return

    await state.update_data(
        order_srv_id=srv_id,
        order_srv_name=s.get("name", ""),
        order_srv_price=s.get("price", ""),
    )

    full_name = cb.from_user.full_name or ""
    await state.set_state(CustomerOrderFSM.entering_name)

    prompt = (
        f"📞 <b>«{escape(s['name'])}» xizmatiga buyurtma berish</b>\n\n"
        f"1️⃣ Iltimos, ismingizni kiriting:\n"
    )
    if full_name:
        prompt += f"<i>(Agar ismingiz <b>{escape(full_name)}</b> bo'lsa, uni yozishingiz yoki «+» yuborishingiz mumkin)</i>"
    else:
        prompt += "<i>(Masalan: Azam)</i>"

    await cb.message.answer(prompt, parse_mode="HTML")
    await cb.answer()


@router.message(CustomerOrderFSM.entering_name)
async def order_process_name(message: Message, state: FSMContext) -> None:
    raw = message.text.strip() if message.text else ""
    if raw == "/cancel":
        await state.clear()
        await message.answer("Buyurtma bekor qilindi.", reply_markup=main_keyboard())
        return

    if raw in ["+", "-"] or not raw:
        name = message.from_user.full_name or "Mijoz"
    else:
        name = raw

    await state.update_data(order_name=name)
    await state.set_state(CustomerOrderFSM.entering_phone)
    await message.answer(
        f"2️⃣ Rahmat, <b>{escape(name)}</b>!\n\n"
        f"Endi telefon raqamingizni yuboring:\n"
        f"<i>Pastdagi tugma orqali kontaktni ulashishingiz yoki raqamni yozib qoldirishingiz mumkin (masalan: +998901234567).</i>",
        parse_mode="HTML",
        reply_markup=order_contact_keyboard(),
    )


@router.message(CustomerOrderFSM.entering_phone, F.contact)
async def order_process_contact(message: Message, state: FSMContext) -> None:
    phone = message.contact.phone_number
    await _complete_order(message, state, phone)


@router.message(CustomerOrderFSM.entering_phone)
async def order_process_phone_text(message: Message, state: FSMContext) -> None:
    raw = message.text.strip() if message.text else ""
    if raw in ["/cancel", "❌ Bekor qilish"]:
        await state.clear()
        await message.answer("Buyurtma bekor qilindi.", reply_markup=main_keyboard())
        return

    digits = [c for c in raw if c.isdigit()]
    if len(digits) < 7:
        await message.answer(
            "❗ Iltimos, to'g'ri telefon raqami kiriting (kamida 7 ta raqam):\n"
            "<i>Masalan: +998901234567</i>",
            parse_mode="HTML",
        )
        return

    await _complete_order(message, state, raw)


async def _complete_order(message: Message, state: FSMContext, phone: str) -> None:
    data = await state.get_data()
    name = data.get("order_name") or message.from_user.full_name or "Mijoz"
    srv_id = data.get("order_srv_id", "")
    srv_name = data.get("order_srv_name", "Xizmat")
    srv_price = data.get("order_srv_price", "—")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    async with SessionLocal() as db:
        order = ServiceOrder(
            telegram_id=message.from_user.id,
            customer_name=name,
            phone=phone,
            service_id=srv_id,
            service_name=srv_name,
            service_price=srv_price,
            status="yangi",
        )
        db.add(order)
        # Also ensure lead table has this contact
        db.add(Lead(telegram_id=message.from_user.id, name=name, phone=phone))
        await db.commit()

    await state.clear()

    await message.answer(
        "✅ <b>Buyurtmangiz muvaffaqiyatli qabul qilindi!</b>\n\n"
        f"💅 <b>Xizmat:</b> {escape(srv_name)}\n"
        f"💰 <b>Narxi:</b> {escape(srv_price)}\n"
        f"👤 <b>Buyurtmachi:</b> {escape(name)}\n"
        f"📞 <b>Telefon:</b> {escape(phone)}\n\n"
        "Tez orada mutaxassisimiz siz bilan bog'lanadi. Rahmat!",
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )

    # Notify admins
    order_info = {
        "name": name,
        "phone": phone,
        "service_name": srv_name,
        "service_price": srv_price,
        "created_at": now_str,
        "telegram_id": message.from_user.id,
    }
    await _notify_admins_new_order(message.bot, order_info)


# ─────────────────────────────────────────────
# 👨‍💼 Operator
# ─────────────────────────────────────────────
@router.message(F.text == "👨‍💼 Operator")
@router.callback_query(F.data == "contact_operator")
async def operator(event: Message | CallbackQuery) -> None:
    biz = services_manager.load_business()
    text = biz.get("handoff_text", "Operator bilan bog'laning.")
    if isinstance(event, CallbackQuery):
        await event.message.answer(text)
        await event.answer()
    else:
        await event.answer(text)


# ─────────────────────────────────────────────
# 📞 Contact (General Phone Sharing)
# ─────────────────────────────────────────────
@router.message(F.contact)
async def contact(message: Message) -> None:
    c = message.contact
    if c.user_id and c.user_id != message.from_user.id:
        await message.answer("Iltimos, o'zingizning telefon raqamingizni yuboring.")
        return
    async with SessionLocal() as db:
        db.add(Lead(
            telegram_id=message.from_user.id,
            name=message.from_user.full_name or "",
            phone=c.phone_number,
        ))
        await db.commit()
    await message.answer("Rahmat! Raqamingiz qabul qilindi. Tez orada bog'lanamiz.")


# ─────────────────────────────────────────────
# /stats (Legacy Admin Command)
# ─────────────────────────────────────────────
@router.message(Command("stats"))
async def stats(message: Message) -> None:
    if message.from_user.id not in settings.admins:
        return
    async with SessionLocal() as db:
        users = await db.scalar(select(func.count()).select_from(Customer))
        leads = await db.scalar(select(func.count()).select_from(Lead))
        orders = await db.scalar(select(func.count()).select_from(ServiceOrder))
    await message.answer(f"📊 Mijozlar: {users or 0}\nKontaktlar: {leads or 0}\nBuyurtmalar: {orders or 0}")


# ─────────────────────────────────────────────
# /leads (Legacy Admin Command)
# ─────────────────────────────────────────────
@router.message(Command("leads"))
async def leads(message: Message) -> None:
    if message.from_user.id not in settings.admins:
        return
    async with SessionLocal() as db:
        rows = (await db.scalars(select(Lead).order_by(Lead.id.desc()).limit(20))).all()
    if not rows:
        await message.answer("Hozircha kontakt yo'q.")
        return
    await message.answer("\n".join(f"• {x.name}: {x.phone}" for x in rows))


# ─────────────────────────────────────────────
# AI Chat — Catch-All Text Handler
# ─────────────────────────────────────────────
@router.message(F.text)
async def ai_chat(message: Message, state: FSMContext) -> None:
    # If admin in active state, do not route to AI
    current_state = await state.get_state()
    if current_state is not None and message.from_user.id in settings.admins:
        return

    raw = message.text.strip() if message.text else ""

    # If message is a single number, check if it matches an active service
    if raw.isdigit():
        num = int(raw)
        srv, _ = services_manager.get_active_service_by_number(num)
        if srv:
            text = _format_service_detail(srv)
            await message.answer(
                text,
                parse_mode="HTML",
                reply_markup=customer_service_detail_inline(srv["id"]),
            )
            return

    await register_customer(message)
    await message.bot.send_chat_action(message.chat.id, "typing")
    biz = services_manager.load_business()

    async with SessionLocal() as db:
        rows = (await db.scalars(
            select(ChatMessage).where(ChatMessage.telegram_id == message.from_user.id)
            .order_by(ChatMessage.id.desc()).limit(10)
        )).all()
        rows.reverse()
        history = [{"role": x.role, "content": x.content} for x in rows]
        history.append({"role": "user", "content": message.text})
        answer = await ask_ai(history, biz)
        db.add(ChatMessage(telegram_id=message.from_user.id, role="user", content=message.text))
        db.add(ChatMessage(telegram_id=message.from_user.id, role="assistant", content=answer))
        await db.commit()

    kb = admin_keyboard() if message.from_user.id in settings.admins else main_keyboard()
    await message.answer(answer, reply_markup=kb)
