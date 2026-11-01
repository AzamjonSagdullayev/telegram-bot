"""
Customer-facing handlers for AzamAI Business Bot.
Supports interactive service selection by number, viewing full service details,
submitting service booking inquiries with admin alerts, reading business news,
viewing the business location and interactive map pin, and chatting with AI.
"""
from datetime import datetime
from html import escape
import logging
from zoneinfo import ZoneInfo

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select, func

from app.config import settings
from app.db import SessionLocal
from app.models import Customer, Lead, ChatMessage, ServiceOrder, Announcement
from app.ai import ask_ai
from app.keyboards import (
    main_keyboard,
    admin_keyboard,
    customer_service_detail_inline,
    customer_services_inline,
    customer_location_inline,
    order_contact_keyboard,
)
from app import services_manager
from app import location_manager
from app.notifications import notify_new_customer, notify_new_order

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
    entering_note = State()


# ─────────────────────────────────────────────
# Registration Helper (notifies admin ONLY once for new users)
# ─────────────────────────────────────────────
async def register_customer(message: Message) -> Customer:
    """
    Registers the customer in PostgreSQL.
    Triggers notify_new_customer ONLY when a genuinely new customer is created.
    """
    async with SessionLocal() as db:
        row = await db.scalar(select(Customer).where(Customer.telegram_id == message.from_user.id))
        is_new = False
        if row is None:
            is_new = True
            row = Customer(telegram_id=message.from_user.id)
            db.add(row)

        row.full_name = message.from_user.full_name or ""
        row.username = message.from_user.username or ""
        await db.commit()
        await db.refresh(row)

        if is_new:
            total_customers = await db.scalar(select(func.count()).select_from(Customer)) or 1
            # Trigger admin notification
            try:
                await notify_new_customer(message.bot, row, total_customers)
            except Exception as exc:
                log.warning("Could not send new customer notification: %s", exc)

        return row


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
            f"Biznes: <b>{escape(biz.get('name', ''))}</b>\n\n"
            "Admin panelini boshqarish uchun quyidagi tugmalardan foydalaning:",
            reply_markup=admin_keyboard(),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            f"Assalomu alaykum! 👋\n"
            f"Men <b>{escape(biz.get('name', ''))}</b> virtual yordamchisiman.\n"
            f"Quyidagi menyu orqali xizmatlar bilan tanishishingiz, yangiliklarni o'qishingiz yoki savolingizni yozishingiz mumkin.",
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

    if raw in ["📰 Yangiliklar"]:
        await state.clear()
        await customer_news(message)
        return

    if raw in ["📍 Manzilimiz"]:
        await state.clear()
        await customer_location(message)
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

    # User asked a normal question — clear state and pass directly to AI chat
    await state.clear()
    await ai_chat(message, state)


# ─────────────────────────────────────────────
# 📰 Customer: Business News & Announcements
# ─────────────────────────────────────────────
@router.message(F.text == "📰 Yangiliklar")
async def customer_news(message: Message) -> None:
    await register_customer(message)
    now = datetime.now(ZoneInfo(settings.timezone))

    async with SessionLocal() as db:
        announcements = (
            await db.scalars(
                select(Announcement)
                .where(Announcement.is_published == True)
                .order_by(Announcement.id.desc())
                .limit(5)
            )
        ).all()

    # Filter out expired announcements
    active_news = []
    for a in announcements:
        if a.expires_at and a.expires_at < now:
            continue
        active_news.append(a)

    if not active_news:
        await message.answer("Hozircha yangi yangiliklar mavjud emas.", reply_markup=main_keyboard())
        return

    await message.answer("📰 <b>So‘nggi yangiliklar va e'lonlar:</b>\n", parse_mode="HTML")

    for a in active_news:
        exp_str = f"\n📅 <i>Amal qilish muddati: {a.expires_at.strftime('%d.%m.%Y')} gacha</i>" if a.expires_at else ""
        caption = (
            f"🎉 <b>{escape(a.title)}</b>\n\n"
            f"{escape(a.text)}"
            f"{exp_str}"
        )
        if a.photo_file_id:
            try:
                await message.answer_photo(photo=a.photo_file_id, caption=caption, parse_mode="HTML")
            except Exception:
                await message.answer(caption, parse_mode="HTML")
        else:
            await message.answer(caption, parse_mode="HTML")


# ─────────────────────────────────────────────
# 📍 Customer: Business Location & Map
# ─────────────────────────────────────────────
@router.message(F.text == "📍 Manzilimiz")
async def customer_location(message: Message) -> None:
    await register_customer(message)
    loc = await location_manager.get_location()

    text = location_manager.format_customer_location_text(loc)
    has_coords = bool(loc and loc.latitude is not None and loc.longitude is not None)
    maps_url = loc.google_maps_url if loc else None

    kb = customer_location_inline(maps_url, has_coords)
    await message.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data == "send_map_pin")
async def customer_send_map_pin_cb(cb: CallbackQuery) -> None:
    loc = await location_manager.get_location()
    if loc and loc.latitude is not None and loc.longitude is not None:
        await cb.message.answer_location(latitude=loc.latitude, longitude=loc.longitude)
        await cb.answer()
    else:
        await cb.answer("Xarita koordinatalari topilmadi.", show_alert=True)


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
    await state.update_data(order_phone=phone)
    await state.set_state(CustomerOrderFSM.entering_note)
    await message.answer(
        "3️⃣ Buyurtmaga qo'shimcha izoh yoki xohlagan vaqtingizni yozing:\n"
        "<i>(Masalan: Soat 15:00 ga yozilmoqchiman. O'tkazib yuborish uchun «-» yozing)</i>",
        parse_mode="HTML",
    )


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

    await state.update_data(order_phone=raw)
    await state.set_state(CustomerOrderFSM.entering_note)
    await message.answer(
        "3️⃣ Buyurtmaga qo'shimcha izoh yoki xohlagan vaqtingizni yozing:\n"
        "<i>(Masalan: Soat 15:00 ga yozilmoqchiman. O'tkazib yuborish uchun «-» yozing)</i>",
        parse_mode="HTML",
    )


@router.message(CustomerOrderFSM.entering_note)
async def order_process_note(message: Message, state: FSMContext) -> None:
    raw = message.text.strip() if message.text else ""
    if raw == "/cancel":
        await state.clear()
        await message.answer("Buyurtma bekor qilindi.", reply_markup=main_keyboard())
        return

    note = "" if raw == "-" else raw
    data = await state.get_data()
    name = data.get("order_name") or message.from_user.full_name or "Mijoz"
    phone = data.get("order_phone", "")
    srv_id = data.get("order_srv_id", "")
    srv_name = data.get("order_srv_name", "Xizmat")
    srv_price = data.get("order_srv_price", "—")

    async with SessionLocal() as db:
        order = ServiceOrder(
            telegram_id=message.from_user.id,
            customer_name=name,
            phone=phone,
            service_id=srv_id,
            service_name=srv_name,
            service_price=srv_price,
            note=note,
            status="yangi",
        )
        db.add(order)
        # Also ensure lead table has this contact
        db.add(Lead(telegram_id=message.from_user.id, name=name, phone=phone))
        await db.commit()
        await db.refresh(order)

    await state.clear()

    note_line = f"\n📝 <b>Izoh:</b> {escape(note)}" if note else ""
    await message.answer(
        "✅ <b>Buyurtmangiz muvaffaqiyatli qabul qilindi!</b>\n\n"
        f"🆔 <b>Buyurtma ID:</b> #{order.id}\n"
        f"💇 <b>Xizmat:</b> {escape(srv_name)}\n"
        f"💰 <b>Narxi:</b> {escape(srv_price)}\n"
        f"👤 <b>Buyurtmachi:</b> {escape(name)}\n"
        f"📞 <b>Telefon:</b> {escape(phone)}"
        f"{note_line}\n\n"
        "Tez orada mutaxassisimiz siz bilan bog'lanadi. Rahmat!",
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )

    # Real-time admin notification
    try:
        await notify_new_order(message.bot, order)
    except Exception as exc:
        log.warning("Could not send admin new order notification: %s", exc)


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
# /stats & /leads (Legacy Admin Commands preserved)
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
