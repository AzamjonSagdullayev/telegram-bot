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
    """
    Inline buttons for interactive service selection.
    Customer can either tap an inline button or type the number in chat.
    """
    buttons = []
    # Display 2 services per row for clean readability
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


# ─────────────────────────────────────────────
# Admin main menu keyboard
# ─────────────────────────────────────────────
def admin_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="👥 Mijozlar")],
            [KeyboardButton(text="📥 Kontaktlar"), KeyboardButton(text="📋 Xizmatlar ro'yxati")],
            [KeyboardButton(text="➕ Yangi xizmat qo'shish"), KeyboardButton(text="✏️ Xizmatni tahrirlash")],
            [KeyboardButton(text="🗑 Xizmatni o'chirish"), KeyboardButton(text="👁 Xizmatni yoqish/o'chirish")],
            [KeyboardButton(text="⚙️ Biznes sozlamalari"), KeyboardButton(text="👤 Mijoz rejimi")],
        ],
        resize_keyboard=True,
    )


# ─────────────────────────────────────────────
# Admin inline keyboards
# ─────────────────────────────────────────────
def admin_services_list_inline(services: list[dict]) -> InlineKeyboardMarkup:
    """Shows all services with active/inactive indicators for admin inspection."""
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
    """Actions when viewing a specific service in admin panel."""
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
    """General service selection list for admin: action = 'edit' | 'delete' | 'toggle'"""
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
    """Field selection for editing a service."""
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
    """Confirm or cancel adding a new service."""
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
