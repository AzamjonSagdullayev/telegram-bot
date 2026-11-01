from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)


# ─────────────────────────────────────────────
# Customer keyboards
# ─────────────────────────────────────────────
def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Xizmatlar"), KeyboardButton(text="👨‍💼 Operator")],
            [KeyboardButton(text="📰 Yangiliklar"), KeyboardButton(text="📍 Manzilimiz")],
            [KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)],
        ],
        resize_keyboard=True,
    )


def order_contact_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard for phone number input during service order."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telefon raqamimni yuborish", request_contact=True)],
            [KeyboardButton(text="❌ Bekor qilish")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def customer_service_detail_inline(service_id: str) -> InlineKeyboardMarkup:
    """Inline buttons shown under detailed service view."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📞 Buyurtma berish", callback_data=f"order_svc_{service_id}")],
            [
                InlineKeyboardButton(text="📋 Barcha xizmatlar", callback_data="view_all_services"),
                InlineKeyboardButton(text="👨‍💼 Operator bilan bog'lanish", callback_data="contact_operator"),
            ],
        ]
    )


def customer_services_inline(services: list[dict]) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for i, s in enumerate(services, 1):
        btn_text = f"{i}️⃣ {s['name']}"
        row.append(InlineKeyboardButton(text=btn_text, callback_data=f"cust_select_svc_{s['id']}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def customer_location_inline(google_maps_url: str | None, has_coords: bool) -> InlineKeyboardMarkup:
    """Buttons shown under customer location message."""
    buttons = []
    if google_maps_url and (google_maps_url.startswith("http://") or google_maps_url.startswith("https://")):
        buttons.append([InlineKeyboardButton(text="🗺 Google Maps orqali ochish", url=google_maps_url)])
    if has_coords:
        buttons.append([InlineKeyboardButton(text="📍 Lokatsiyani yuborish", callback_data="send_map_pin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ─────────────────────────────────────────────
# Admin main menu keyboard
# ─────────────────────────────────────────────
def admin_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Hisobotlar"), KeyboardButton(text="👥 Mijozlar")],
            [KeyboardButton(text="📥 Buyurtmalar"), KeyboardButton(text="📋 Xizmatlar")],
            [KeyboardButton(text="📰 Yangiliklar"), KeyboardButton(text="📍 Manzil va xarita")],
            [KeyboardButton(text="📢 Barchaga xabar yuborish")],
            [KeyboardButton(text="⚙️ Biznes sozlamalari"), KeyboardButton(text="👤 Mijoz rejimi")],
        ],
        resize_keyboard=True,
    )


# ─────────────────────────────────────────────
# Reports inline keyboards
# ─────────────────────────────────────────────
def reports_periods_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 Bugungi hisobot", callback_data="rep_today"),
                InlineKeyboardButton(text="📅 Haftalik hisobot", callback_data="rep_week"),
            ],
            [
                InlineKeyboardButton(text="📅 Oylik hisobot", callback_data="rep_month"),
                InlineKeyboardButton(text="📊 Umumiy hisobot", callback_data="rep_all"),
            ],
            [
                InlineKeyboardButton(text="🔄 Yangilash", callback_data="rep_refresh"),
            ]
        ]
    )


# ─────────────────────────────────────────────
# Location inline keyboards
# ─────────────────────────────────────────────
def admin_location_menu_inline(has_coords: bool, has_url: bool) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="🏢 Manzilni o'zgartirish", callback_data="loc_edit_address"),
            InlineKeyboardButton(text="ℹ️ Mo'ljalni kiritish", callback_data="loc_edit_landmark"),
        ],
        [
            InlineKeyboardButton(text="📍 Telegram lokatsiya yuborish", callback_data="loc_prompt_pin"),
            InlineKeyboardButton(text="🌐 Koordinata kiritish", callback_data="loc_edit_coords"),
        ],
        [
            InlineKeyboardButton(text="🗺 Google Maps havolasi", callback_data="loc_edit_url"),
            InlineKeyboardButton(text="👁 Mijoz ko'rinishida sinash", callback_data="loc_preview_customer"),
        ],
        [
            InlineKeyboardButton(text="🗑 Lokatsiyani tozalash", callback_data="loc_clear_prompt"),
            InlineKeyboardButton(text="🔙 Admin menyu", callback_data="loc_cancel"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_clear_location_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗑 Ha, tozalash", callback_data="loc_clear_confirm"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="loc_cancel"),
            ]
        ]
    )


# ─────────────────────────────────────────────
# News & Announcements inline keyboards
# ─────────────────────────────────────────────
def admin_news_menu_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Yangi e'lon yaratish", callback_data="news_create_new")],
            [InlineKeyboardButton(text="📋 Barcha e'lonlar", callback_data="news_list_all")],
            [InlineKeyboardButton(text="📢 Barchaga xabar yuborish", callback_data="news_broadcast_menu")],
            [InlineKeyboardButton(text="🔙 Admin menyu", callback_data="svc_cancel")],
        ]
    )


def news_preview_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Barchaga yuborish", callback_data="news_action_broadcast")],
            [InlineKeyboardButton(text="💾 Qoralama sifatida saqlash", callback_data="news_action_draft")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="news_action_cancel")],
        ]
    )


def news_item_actions_inline(announcement_id: int, is_published: bool) -> InlineKeyboardMarkup:
    toggle_text = "🔴 Bekor qilish (yashirish)" if is_published else "🟢 Chop etish"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Barchaga yuborish", callback_data=f"news_send_all_{announcement_id}")],
            [
                InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"news_edit_{announcement_id}"),
                InlineKeyboardButton(text=toggle_text, callback_data=f"news_toggle_{announcement_id}"),
            ],
            [
                InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"news_del_{announcement_id}"),
                InlineKeyboardButton(text="🔙 Ro'yxatga qaytish", callback_data="news_list_all"),
            ]
        ]
    )


def confirm_delete_news_inline(announcement_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗑 Ha, o'chirish", callback_data=f"news_confirm_del_{announcement_id}"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="news_list_all"),
            ]
        ]
    )


def confirm_broadcast_inline(announcement_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📢 Ha, hozir yuborilsin!", callback_data=f"news_confirm_send_{announcement_id}"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="news_list_all"),
            ]
        ]
    )


# ─────────────────────────────────────────────
# Orders management inline keyboards
# ─────────────────────────────────────────────
def order_action_inline(order_id: int, telegram_id: int) -> InlineKeyboardMarkup:
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
            [InlineKeyboardButton(text="🔙 Buyurtmalar ro'yxati", callback_data="orders_list_page_0")]
        ]
    )


def orders_filter_inline(current_filter: str = "all") -> InlineKeyboardMarkup:
    filters = [
        ("Barchasi", "all"),
        ("⏳ Kutilayotgan", "pending"),
        ("✅ Qabul qilingan", "accepted"),
        ("❌ Rad etilgan", "rejected"),
    ]
    buttons = []
    row = []
    for label, key in filters:
        text = f"• {label} •" if key == current_filter else label
        row.append(InlineKeyboardButton(text=text, callback_data=f"ord_filter_{key}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ─────────────────────────────────────────────
# Services & general admin inline keyboards
# ─────────────────────────────────────────────
def admin_services_list_inline(services: list[dict]) -> InlineKeyboardMarkup:
    buttons = []
    for i, s in enumerate(services, 1):
        status = "🟢" if s.get("is_active", True) else "🔴"
        btn_text = f"{i}. {s['name']} {status}"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"admin_view_svc_{s['id']}")])
    buttons.append([
        InlineKeyboardButton(text="➕ Yangi xizmat qo'shish", callback_data="admin_add_svc_quick"),
        InlineKeyboardButton(text="🔙 Admin menyu", callback_data="svc_cancel"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_service_actions_inline(service_id: str, is_active: bool) -> InlineKeyboardMarkup:
    toggle_text = "🔴 Nofaol qilish" if is_active else "🟢 Faollashtirish"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"admin_edit_svc_{service_id}"),
                InlineKeyboardButton(text=toggle_text, callback_data=f"admin_toggle_svc_{service_id}"),
            ],
            [
                InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"admin_del_svc_{service_id}"),
                InlineKeyboardButton(text="🔙 Ro'yxatga qaytish", callback_data="admin_list_services"),
            ]
        ]
    )


def services_inline(services: list[dict], action: str) -> InlineKeyboardMarkup:
    buttons = []
    for i, s in enumerate(services, 1):
        status = "🟢" if s.get("is_active", True) else "🔴"
        buttons.append([
            InlineKeyboardButton(
                text=f"{i}. {s['name']} {status}",
                callback_data=f"svc_{action}_{s['id']}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="svc_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def edit_fields_inline(service_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Nomini o'zgartirish", callback_data=f"editf_{service_id}_name"),
                InlineKeyboardButton(text="💰 Narxini o'zgartirish", callback_data=f"editf_{service_id}_price"),
            ],
            [
                InlineKeyboardButton(text="⏱ Davomiyligini o'zgartirish", callback_data=f"editf_{service_id}_duration"),
                InlineKeyboardButton(text="📝 Tavsifini o'zgartirish", callback_data=f"editf_{service_id}_description"),
            ],
            [
                InlineKeyboardButton(text="ℹ️ Qo'shimcha ma'lumotni o'zgartirish", callback_data=f"editf_{service_id}_additional_info"),
            ],
            [
                InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"admin_view_svc_{service_id}"),
            ]
        ]
    )


def confirm_delete_inline(service_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🗑 Ha, o'chirish", callback_data=f"svc_confirm_del_{service_id}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="svc_cancel"),
        ]
    ])


def confirm_add_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Saqlash", callback_data="add_svc_confirm"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="add_svc_cancel"),
        ]
    ])


def business_fields_inline() -> InlineKeyboardMarkup:
    fields = [
        ("📛 Nomi", "name"),
        ("📄 Tavsif", "description"),
        ("🤝 Operator matni", "handoff_text"),
        ("📏 Qoidalar (AI)", "system_rules"),
    ]
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"biz_field_{key}")]
        for label, key in fields
    ]
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="biz_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def pagination_inline(page: int, total_pages: int, prefix: str) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    if page > 0:
        row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"{prefix}_page_{page - 1}"))
    if page < total_pages - 1:
        row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"{prefix}_page_{page + 1}"))
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)
