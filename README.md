# AzamAI Business — Telegram AI Assistant, Notifications & Admin Management Bot

Telegram orqali bizneslar uchun mo'ljallangan sun'iy intellektli yordamchi, real-vaqtli admin bildirishnomalari, yangiliklar tarqatish, jonli hisobotlar va interaktiv xarita tizimi.

---

## 🚀 Asosiy imkoniyatlar

### 1. 📰 Yangiliklar va e'lonlar (Module 1):
- **Mijozlar uchun:** `📰 Yangiliklar` tugmasi orqali biznesning so'nggi aksiyalari, chegirmalari va e'lonlarini ko'rish (matn va rasmli e'lonlar qo'llab-quvvatlanadi).
- **Admin uchun:** Yangiliklar boshqaruvi:
  - ➕ Yangi e'lon yaratish (Sarlavha, Matn, Rasm, Amal qilish muddati va Preview).
  - 📋 Barcha e'lonlar ro'yxati (🟢 Chop etilgan / 🟡 Qoralama).
  - ✏️ Tahrirlash, 🗑 O'chirish, 🟢/🔴 Chop etishni yoqish/o'chirish.
  - 📢 **Barcha mijozlarga xabar yuborish (Broadcast):** Telegram API tezlik cheklovlariga (rate limits) to'liq mos keladigan asinxron, xavfsiz va xatoliklarga chidamli xabar tarqatish mexanizmi. Yakunda admin uchun batafsil yetkazilish hisoboti (muvaffaqiyatli / yetkazilmaganlar soni).

### 2. 🔔 Real-vaqtli admin bildirishnomalari (Module 2):
- **Yangi mijoz:** Har bir haqiqiy yangi foydalanuvchi botni birinchi marta ishga tushirganda adminga bildirishnoma boradi. Qayta `/start` bosilganda takroriy xabar yuborilmaydi.
- **Yangi xizmat buyurtmasi:** Mijoz buyurtma berganda adminga darhol to'liq ma'lumot (ism, telefon, xizmat, narx, izoh, buyurtma ID) yetkaziladi.
- **Interaktiv Qabul qilish / Rad etish:** Bildirishnomaning o'zida `✅ Qabul qilish`, `❌ Rad etish` va `💬 Mijoz bilan bog'lanish` tugmalari mavjud.
  - Admin qaror qabul qilishi bilan status bazada yangilanadi va mijozga darhol xushxabar yoki izoh yuboriladi.

### 3. 📊 Jonli hisobotlar va avtomatik kunlik tahlil (Module 3):
- **Hisobotlar paneli (`📊 Hisobotlar`):**
  - Jami mijozlar, bugungi, haftalik va oylik yangi mijozlar o'sishi.
  - Jami buyurtmalar (Kutilayotgan, Qabul qilingan, Rad etilgan).
  - Xizmatlar va e'lonlar soni.
- **Davrlar bo'yicha hisobot:** `📅 Bugungi hisobot`, `📅 Haftalik hisobot`, `📅 Oylik hisobot`, `📊 Umumiy hisobot`. Barcha sanalar `Asia/Tashkent` vaqti bo'yicha hisoblanadi.
- **Avtomatik kunlik hisobot:** Har kuni soat **21:00 da (Toshkent vaqti)** barcha adminlarga kunlik faoliyat sarhisobi yuboriladi. Bot qayta yoqilganda takroriy xabar yuborilishining oldini oluvchi idempotency (bazada qayd etish) tizimi mavjud.

### 4. 📍 Biznes manzili va interaktiv xarita (Module 4):
- **Mijozlar uchun:** `📍 Manzilimiz` tugmasi:
  - Biznesning to'liq manzili va mo'ljali.
  - `🗺 Google Maps orqali ochish` inline havolasi.
  - `📍 Lokatsiyani yuborish` orqali Telegram'ning haqiqiy xarita nuqtasi (geopozitsiya).
- **Admin uchun:** `📍 Manzil va xarita`:
  - Manzil va mo'ljal matnini kiritish/tahrirlash.
  - Telegram orqali geopozitsiya yuborish (`Location` yuborilganda koordinatalar avtomatik olinadi).
  - Qo'lda kenglik va uzunlik (latitude, longitude) kiritish (aniq oraliq tekshiruvi bilan).
  - Google Maps havolasini sozlash.
  - Mijoz ko'rinishida sinab ko'rish (Preview).

### 5. 🤖 Avvalgi barcha imkoniyatlar saqlangan:
- Sun'iy intellektli AI assistent (OpenAI GPT).
- Xizmatlarni raqam orqali interaktiv tanlash (1, 2, 3...).
- Xizmatlar boshqaruvi (qo'shish, tahrirlash, o'chirish, faollashtirish).
- PostgreSQL bazasi va Docker Compose.

---

## 🛠 O'rnatish va sozlash

### 1. `.env` fayli namunasi

```env
BOT_TOKEN=123456789:ABCDefghIJKLmnOPQRstuvwxyz
ADMIN_IDS=6686448989,123456789
POSTGRES_PASSWORD=kuchli_parol
DATABASE_URL=postgresql+asyncpg://azam:kuchli_parol@db:5432/azam_ai
AI_BASE_URL=https://api.openai.com/v1
AI_API_KEY=sk-proj-...
AI_MODEL=gpt-4o-mini
AI_TEMPERATURE=0.4
BUSINESS_CONFIG_PATH=business.json

# Vaqt mintaqasi va kunlik hisobot vaqti
TIMEZONE=Asia/Tashkent
DAILY_REPORT_TIME=21:00
```

### 2. Docker bilan ishga tushirish

```bash
# 1. Konteynerlarni qayta qurish va ishga tushirish
docker compose up -d --build

# 2. Holatni tekshirish
docker compose ps

# 3. Bot loglarini kuzatish
docker compose logs --tail=100 -f bot
```

---

## 🗄 Ma'lumotlar bazasi tuzilmasi

Loyiha PostgreSQL 16 va SQLAlchemy 2.0 dan foydalanadi. Jami 9 ta jadval:
1. `customers` — ro'yxatdan o'tgan mijozlar (Telegram ID, ism, username, sana).
2. `service_orders` — xizmat buyurtmalari (mijoz, xizmat, narx, izoh, status, qabul qilgan admin).
3. `leads` — mijozlar kontaktlari.
4. `chat_messages` — AI bilan yozishmalar tarixi.
5. `announcements` — biznes e'lonlari va yangiliklari.
6. `broadcast_campaigns` — xabar tarqatish kampaniyalari va yetkazilish statistikasi.
7. `business_locations` — biznes manzili, koordinatalari va Google Maps havolasi.
8. `daily_report_logs` — kunlik avtomatik hisobotlar jurnali (takroriy yuborilishdan himoya).
9. `admin_actions` — admin harakatlari jurnali.

Barcha jadvallar bot ishga tushganda `init_db()` orqali avtomatik ravishda xavfsiz va buzmasdan (non-destructive) tekshiriladi va yaratiladi.

---

## 🧪 Sinov bo'yicha ko'rsatmalar

1. **Yangi mijoz:** Boshqa Telegram akkauntdan `/start` yuboring -> Admin chatiga bir marta yangi foydalanuvchi kartochkasi boradi. Qayta `/start` yuborganda adminga takroriy xabar bormaydi.
2. **Buyurtma berish:** Xizmatni tanlang, `📞 Buyurtma berish` bosing, ism, telefon va ixtiyoriy izoh qoldiring -> Adminga qabul qilish/rad etish tugmalari bilan buyurtma yetib boradi.
3. **Qaror qabul qilish:** Admindan `✅ Qabul qilish` yoki `❌ Rad etish` tugmasini bosing -> Mijozga status yetib boradi, admin xabarida esa qaysi admin ko'rib chiqqani qayd etiladi.
4. **Yangiliklar:** Admindan `📰 Yangiliklar` -> `➕ Yangi e'lon yaratish` orqali e'lon tayyorlang va `✅ Barchaga yuborish` bosing -> Mijozlarga yetkaziladi va adminga yetkazilish hisoboti beriladi.
5. **Hisobotlar:** Admindan `📊 Hisobotlar` bosing -> Jonli tahliliy ma'lumotlar va davrlar bo'yicha hisobotlar chiqadi.
6. **Manzil:** Admindan `📍 Manzil va xarita` orqali manzil, koordinata yoki lokatsiya yuboring -> Mijoz `📍 Manzilimiz` tugmasini bosganda ushbu ma'lumotlar chiqadi.
