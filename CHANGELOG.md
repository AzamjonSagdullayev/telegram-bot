# 📋 O'zgarishlar Tarixi (Changelog) — AzamAI Business

---

## 🚀 Versiya 2.2 (2026-11-01) — Bildirishnomalar, Jonli Hisobotlar, Yangiliklar Tarqatish va Manzil/Xarita

Ushbu versiyada tizim 4 ta yirik modul bilan boyitildi:
1. **Biznes yangiliklari va ommaviy xabar yuborish (Module 1).**
2. **Real-vaqtli admin bildirishnomalari va buyurtmani tasdiqlash (Module 2).**
3. **Hisobotlar, jonli tahlil va avtomatik kunlik 21:00 sarhisob (Module 3).**
4. **Biznes manzili va interaktiv xarita boshqaruvi (Module 4).**

---

### 🗄 1. Yangi ma'lumotlar bazasi modellari (`app/models.py`)

PostgreSQL ga 5 ta yangi jadval qo'shildi va `service_orders` kengaytirildi:

1. **`announcements`:**
   - `id`, `title`, `text`, `photo_file_id`, `is_published`, `expires_at`, `created_at`, `updated_at`.
2. **`broadcast_campaigns`:**
   - `id`, `announcement_id`, `title`, `text`, `photo_file_id`, `status`, `total_recipients`, `successful_deliveries`, `failed_deliveries`, `started_at`, `finished_at`.
3. **`business_locations`:**
   - `id`, `address`, `landmark`, `latitude`, `longitude`, `google_maps_url`, `is_active`, `updated_at`.
4. **`daily_report_logs`:**
   - `id`, `report_date` (unique `YYYY-MM-DD`), `sent_at`, `recipients_count`, `summary_text`.
5. **`admin_actions`:**
   - `id`, `admin_id`, `action_type`, `details`, `created_at`.
6. **`service_orders` (Kengaytirildi):**
   - `note` (mijozning buyurtmaga qo'shimcha izohi), `handled_by_admin` (qabul/rad etgan admin ID), `updated_at`.

---

### 📂 2. Fayllar kesimidagi o'zgarishlar

1. **`app/notifications.py` (Yangi modul):**
   - Markazlashtirilgan bildirishnomalar servisi.
   - Yangi mijoz birinchi marta ro'yxatdan o'tganda adminlarga bildirishnoma (`notify_new_customer`).
   - Yangi buyurtma tushganda `✅ Qabul qilish`, `❌ Rad etish`, `💬 Mijoz bilan bog'lanish` tugmalari bilan adminga bildirishnoma (`notify_new_order`).
   - Buyurtma qabul yoki rad etilganda mijozga darhol xushxabar yoki tushuntirish yuborish (`notify_customer_order_status`).

2. **`app/broadcast.py` (Yangi modul):**
   - Asinxron, xavfsiz va tezlik cheklovlariga (rate limit ~25 xabar/sekund) mos xabar tarqatuvchi dvigatel.
   - Takroriy bosishdan himoya qiluvchi `asyncio.Lock` mexanizmi.
   - Bloklangan foydalanuvchilar (`TelegramForbiddenError`) jarayonni to'xtatmaydi.
   - Yakunda adminga muvaffaqiyatli va yetkazilmaganlar soni bo'yicha hisobot.

3. **`app/reports.py` (Yangi modul):**
   - `Asia/Tashkent` vaqt mintaqasi asosida kunlik, haftalik va oylik ko'rsatkichlarni hisoblash.
   - Har kuni soat **21:00 da (Toshkent vaqti)** barcha adminlarga kunlik hisobot yuboruvchi scheduler (`daily_report_scheduler`).
   - `DailyReportLog` jadvali orqali takroriy yuborilishdan 100% himoya (idempotentlik).

4. **`app/location_manager.py` (Yangi modul):**
   - Biznes manzili, mo'ljali, koordinatalari va Google Maps havolasini boshqarish.
   - Koordinatalar (-90..+90, -180..+180) va URL validatsiyasi.
   - Mijozga manzil matni, Google Maps inline havolasi va Telegram xarita geopozitsiyasini yuborish.

5. **`app/handlers.py`:**
   - Mijoz uchun `📰 Yangiliklar` va `📍 Manzilimiz` tugmalari qo'shildi.
   - Yangi foydalanuvchi birinchi marta kirganda adminga bir marta xabar borishi ta'minlandi (`register_customer`).
   - Buyurtma berish jarayoniga ixtiyoriy izoh (masalan: *"Soat 15:00 ga"*) kiritish bosqichi qo'shildi.

6. **`app/admin_handlers.py`:**
   - `📊 Hisobotlar` — jonli dashboard va davriy tahlillar.
   - `📥 Buyurtmalar` — buyurtmalar ro'yxati, `ord_acc_` va `ord_rej_` tugmalari orqali buyurtmani tasdiqlash/rad etish.
   - `📰 Yangiliklar` — e'lonlar yaratish (matn + rasm + muddat), tahrirlash, o'chirish, chop etish.
   - `📍 Manzil va xarita` — manzil, mo'ljal, Telegram lokatsiya pin, koordinata va Google Maps boshqaruvi.
   - `📢 Barchaga xabar yuborish` — tezkor ommaviy xabar yuborish.

7. **`app/keyboards.py`:**
   - Yangilangan mijoz va admin menyu klaviaturalari hamda barcha yangi inline boshqaruv tugmalari.

8. **`app/db.py`:**
   - Mavjud bazalarni buzmasdan yangilaydigan `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` migratsiyalari.

9. **`app/main.py`:**
   - Fonda ishga tushuvchi `daily_report_scheduler(bot)` vazifasi qo'shildi.

---

## 🚀 Versiya 2.1 (2026-11-01) — Interaktiv Xizmatlar va Admin Boshqaruvi
- Xizmatlarni raqam orqali interaktiv tanlash (1, 2, 3...).
- Xizmatlarning 9 maydonli to'liq sxemasi (`business.json`).
- Admin tomonidan xizmatlarni qo'shish, tahrirlash, o'chirish va faollashtirish.

---

## 🚀 Versiya 2.0 (2026-10-31) — Telegram Admin Paneli
- Telegram ichidagi tugmali admin paneli.
- Admin autentifikatsiyasi (`ADMIN_IDS`).
- Statistika va mijozlar ro'yxati.
