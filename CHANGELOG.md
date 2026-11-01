# 📋 O'zgarishlar Tarixi (Changelog) — AzamAI Business

Ushbu hujjatda Telegram bot tizimiga kiritilgan barcha so'nggi o'zgarishlar, yangi funksiyalar va ma'lumotlar tuzilmasi haqida batafsil ma'lumot keltirilgan.

---

## 🚀 Versiya 2.1 (2026-11-01) — Interaktiv Xizmatlar va Admin Boshqaruvi

### 🎯 1. Asosiy maqsad va kiritilgan yangiliklar

Avvalgi versiyada mijozlar `📋 Xizmatlar` tugmasini bosganlarida faqat umumiy matnli ro'yxat ko'rsatilardi. Mijozlar xizmat haqida batafsil ma'lumot ololmas va to'g'ridan-to'g'ri Telegram orqali buyurtma qoldirolmas edi.

**Yangi versiyadagi yangiliklar:**
- **Interaktiv xizmat tanlash:** Mijoz xizmat raqamini (masalan: `4`) yuborganida, bot o'sha xizmatning to'liq tavsifi, narxi, davomiyligi va qo'shimcha ma'lumotlarini chiqaradi.
- **Xizmatga buyurtma berish (`📞 Buyurtma berish`):** Mijoz bir tugma orqali ism va telefon raqamini kiritib, xizmatga buyurtma (inquiry) qoldiradi.
- **Admin bildirishnomalari:** Har bir yangi buyurtma haqida barcha adminlarga tezkor ma'lumot yuboriladi.
- **To'liq Admin xizmatlar boshqaruvi:** Xizmat qo'shish (tasdiqlash bilan), tahrirlash, o'chirish va faollashtirish/nofaol qilish.
- **Faol/Nofaol xizmatlar filtri:** Nofaol qilingan xizmatlar mijozlarga ko'rinmaydi va AI tomonidan tavsiya etilmaydi.

---

## 🗃 2. Ma'lumotlar tuzilmasi

### 2.1 Xizmatlar obyekti (`business.json`)

Har bir xizmat quyidagi 9 ta maydondan iborat:

```json
{
  "id": "srv_1",
  "name": "Manikyur",
  "price": "120 000 so'mdan",
  "duration": "60 daqiqa",
  "description": "Klassik va apparatli manikyur. Tirnoqlarni tozalash, chiroyli shakl berish va kutikulaga professional ishlov berish.",
  "additional_info": "Steril va bir martalik vositalardan foydalaniladi.",
  "is_active": true,
  "created_at": "2026-10-31 18:00",
  "updated_at": "2026-11-01 14:00"
}
```

| Maydon | Turi | Majburiy | Tavsifi |
|---|---|---|---|
| `id` | String | Ha | Noyob xizmat identifikatori (`srv_1`, `srv_2`...) |
| `name` | String | Ha | Xizmat nomi |
| `price` | String | Ha | Xizmat narxi |
| `duration` | String | Ha | Davomiyligi |
| `description` | String | Yo'q | Xizmatning to'liq tavsifi |
| `additional_info` | String | Yo'q | Qo'shimcha qulayliklar yoki eslatmalar |
| `is_active` | Boolean | Ha | `true` bo'lsa mijozlarga ko'rinadi, `false` bo'lsa yashirin |
| `created_at` | String | Ha | Yaratilgan sana va vaqt |
| `updated_at` | String | Ha | Oxirgi tahrirlangan sana va vaqt |

---

### 2.2 Ma'lumotlar bazasi (`ServiceOrder` modeli)

`app/models.py` fayliga PostgreSQL uchun yangi model qo'shildi:

```python
class ServiceOrder(Base):
    __tablename__ = "service_orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    customer_name: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(50))
    service_id: Mapped[str] = mapped_column(String(100), default="")
    service_name: Mapped[str] = mapped_column(String(255), default="")
    service_price: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(50), default="yangi")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

*Eslatma: Mavjud `customers`, `leads` va `chat_messages` jadvallariga tegilmadi va ular to'liq saqlandi.*

---

## 📂 3. Fayllar kesimidagi o'zgarishlar

### 1. `app/services_manager.py` (Yangi modul)
- `load_business()` va `save_business()` — xavfsiz va atomik yozish mexanizmi bilan.
- `get_active_services()` — faqat `is_active=True` bo'lgan xizmatlarni qaytaradi.
- `get_active_service_by_number(num)` — foydalanuvchi kiritgan raqam bo'yicha xizmatni topadi.
- `add_service()`, `update_service()`, `delete_service()`, `toggle_service_active()`.

### 2. `app/handlers.py` (O'zgartirildi)
- Mijoz xizmatlar ro'yxatini ko'rganda `CustomerServiceFSM.selecting_service` holati ishga tushadi.
- Raqam kiritilganda xizmat tafsilotlari ko'rsatiladi.
- Noto'g'ri raqamlar (0, manfiy yoki mavjud bo'lmagan) uchun tushunarli xabar beriladi.
- Agar mijoz matnli savol yuborsa, AI assistent muloqotiga avtomatik o'tkaziladi.
- `CustomerOrderFSM` orqali buyurtma qabul qilinadi va barcha adminlarga tezkor xabar yuboriladi.

### 3. `app/admin_handlers.py` (O'zgartirildi)
- `📋 Xizmatlar ro'yxati` — barcha xizmatlar holati bilan ko'rsatiladi.
- `➕ Yangi xizmat qo'shish` — 5 bosqichli FSM va saqlashdan oldin Preview.
- `✏️ Xizmatni tahrirlash` — har bir parametr alohida inline tugma bilan tahrirlanadi.
- `👁 Xizmatni yoqish/o'chirish` — faollik holatini bir bosishda almashtirish.
- `🗑 Xizmatni o'chirish` — tasdiqlash dialogi orqali o'chirish.

### 4. `app/keyboards.py` (O'zgartirildi)
- `customer_services_inline()` — interaktiv xizmatlar tanlash tugmalari.
- `customer_service_detail_inline()` — xizmat ostidagi buyurtma va qaytish tugmalari.
- `order_contact_keyboard()` — buyurtma vaqtida telefon yuborish klaviaturasi.
- `admin_services_list_inline()` va `admin_service_actions_inline()`.

### 5. `app/ai.py` (O'zgartirildi)
- AI yordamchi promptiga faqat faol xizmatlar uzatiladi.

### 6. `business.json` (O'zgartirildi)
- Barcha xizmatlar yangi 9 maydonli sxemaga o'tkazildi.

---

## 🛠 4. Ishga tushirish va tekshirish

```bash
# 1. Konteynerlarni qayta qurish va fonda ishga tushirish
docker compose up -d --build

# 2. Holatni tekshirish
docker compose ps

# 3. Loglarni tekshirish
docker compose logs --tail=50 bot
```
