# 📖 AzamAI Business Bot — To'liq Ishlatish Yo'riqnomasi

> Versiya: 2.2 | Til: O'zbek | Oxirgi yangilanish: 2026-11-01

---

## 📑 Mundarija

1. [Tizim talablari va arxitektura](#1-tizim-talablari-va-arxitektura)
2. [O'rnatish va Docker orqali ishga tushirish](#2-ornatish-va-docker-orqali-ishga-tushirish)
3. [ADMIN_IDS sozlash](#3-admin_ids-sozlash)
4. [Mijozlar menyusi va imkoniyatlari](#4-mijozlar-menyusi-va-imkoniyatlari)
   - [📋 Xizmatlar ro'yxati va tanlash](#-xizmatlar-royxati-va-tanlash)
   - [📞 Xizmatga buyurtma berish](#-xizmatga-buyurtma-berish)
   - [📰 Yangiliklar va e'lonlar](#-yangiliklar-va-elonlar)
   - [📍 Biznes manzili va xarita](#-biznes-manzili-va-xarita)
   - [💬 AI yordamchi bilan suhbat](#-ai-yordamchi-bilan-suhbat)
5. [Admin paneli — to'liq qo'llanma](#5-admin-paneli--toliq-qollanma)
   - [📊 Hisobotlar va jonli statistika](#-hisobotlar-va-jonli-statistika)
   - [📥 Buyurtmalarni boshqarish (Qabul qilish / Rad etish)](#-buyurtmalarni-boshqarish-qabul-qilish--rad-etish)
   - [📰 Yangiliklarni boshqarish va xabar tarqatish](#-yangiliklarni-boshqarish-va-xabar-tarqatish)
   - [📍 Manzil va xaritani sozlash](#-manzil-va-xaritani-sozlash)
   - [📢 Barchaga tezkor xabar yuborish](#-barchaga-tezkor-xabar-yuborish)
   - [📋 Xizmatlar boshqaruvi](#-xizmatlar-boshqaruvi)
   - [👥 Mijozlar ro'yxati](#-mijozlar-royxati)
   - [⚙️ Biznes sozlamalari](#-biznes-sozlamalari)
   - [👤 Mijoz rejimi](#-mijoz-rejimi)
6. [Real-vaqtli admin bildirishnomalari (Notifications)](#6-real-vaqtli-admin-bildirishnomalari-notifications)
7. [Avtomatik kunlik hisobot (Daily Report Scheduler)](#7-avtomatik-kunlik-hisobot-daily-report-scheduler)
8. [Buyruqlar ro'yxati](#8-buyruqlar-royxati)
9. [Docker boshqaruv buyruqlari](#9-docker-boshqaruv-buyruqlari)
10. [Loglarni tekshirish](#10-loglarni-tekshirish)
11. [Ko'p uchraydigan savollar va yechimlar](#11-kop-uchraydigan-savollar-va-yechimlar)
12. [Loyihadagi o'zgarishlar tarixi va ma'lumotlar tuzilmasi (Changelog)](#12-loyihadagi-ozgarishlar-tarixi-va-malumotlar-tuzilmasi-changelog)

---

## 1. Tizim talablari va arxitektura

| Komponent | Versiya / Tavsif |
|---|---|
| Aiogram 3 | 3.13+ (Asinxron Telegram bot frameworki, FSM) |
| PostgreSQL | 16 (Alpin bazasi, 9 ta munosabatli jadval) |
| SQLAlchemy | 2.0+ (Asinxron asyncpg drayveri) |
| `business.json` | Xizmatlar va biznes ma'lumotlari (Docker read-write mount) |
| OpenAI API | GPT-4o-mini sun'iy intellekt modeli |
| Timezone | `Asia/Tashkent` (kunlik chegaralar va hisobotlar) |

---

## 2. O'rnatish va Docker orqali ishga tushirish

### 2.1 Papkaga o'tish

```bash
cd /home/azamjon/Downloads/azam_ai_business
```

### 2.2 `.env` faylini sozlash

```bash
cp .env.example .env
nano .env
```

Namunaviy parametrlar:
```env
BOT_TOKEN=9249786946:AAHkVHrlS4JfKlwbV-iF2Sb7WTw05YqL7V4
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

### 2.3 Botni ishga tushirish

```bash
docker compose up -d --build
```

### 2.4 Ishlayotganini tekshirish

```bash
docker compose ps
docker compose logs --tail=50 bot
```

---

## 3. ADMIN_IDS sozlash

1. O'zingizning numeric Telegram ID raqamingizni bilish uchun Telegram'da `@userinfobot` ga yozing.
2. `.env` faylida `ADMIN_IDS` ga ID raqamingizni yozing:
   ```env
   # Bitta admin:
   ADMIN_IDS=6686448989

   # Bir nechta admin (vergul bilan):
   ADMIN_IDS=6686448989,987654321
   ```
3. Qayta yuklash:
   ```bash
   docker compose up -d
   ```

---

## 4. Mijozlar menyusi va imkoniyatlari

Mijoz botni ishga tushirganda quyidagi klaviatura taqdim etiladi:

```
[ 📋 Xizmatlar ]   [ 👨‍💼 Operator ]
[ 📰 Yangiliklar ] [ 📍 Manzilimiz ]
[ 📞 Telefon raqamni yuborish ]
```

### 📋 Xizmatlar ro'yxati va tanlash
- `📋 Xizmatlar` bosilganda barcha faol xizmatlar raqamlangan ro'yxatda chiqadi (1️⃣, 2️⃣, 3️⃣...).
- Mijoz xizmat raqamini (masalan: `4`) yuborsa, bot aynan shu xizmatning to'liq ma'lumotlarini chiqaradi.
- Xatoliklar nazorati: 0, manfiy yoki mavjud bo'lmagan raqamlar yuborilganda do'stona ogohlantirish beriladi.

### 📞 Xizmatga buyurtma berish
- Xizmat ostidagi `📞 Buyurtma berish` tugmasi bosiladi.
- Bot mijozning ismini, telefon raqamini va ixtiyoriy izohini (masalan: *"Soat 15:00 ga"*) so'raydi.
- Buyurtma PostgreSQL `service_orders` va `leads` jadvallariga saqlanadi.
- Barcha adminlarga tezkor bildirishnoma boradi.

### 📰 Yangiliklar va e'lonlar
- `📰 Yangiliklar` tugmasi bosilganda biznesning so'nggi e'lonlari, aksiyalari va chegirmalari ko'rsatiladi.
- Matnli hamda rasmli e'lonlar qo'llab-quvvatlanadi.
- Muddati o'tgan e'lonlar avtomatik tarzda yashiriladi.

### 📍 Biznes manzili va xarita
- `📍 Manzilimiz` tugmasi bosilganda:
  - Biznesning to'liq manzili va mo'ljali chiqadi.
  - `🗺 Google Maps orqali ochish` — brauzer yoki ilovada xaritani ochadi.
  - `📍 Lokatsiyani yuborish` — Telegram'ning asl geopozitsiyasini (xarita nuqtasi) yuboradi.

### 💬 AI yordamchi bilan suhbat
- Mijoz istalgan savolini yozishi mumkin. Sun'iy intellekt faqat biznes tasdiqlagan ma'lumotlar va faol xizmatlar asosida tezkor javob beradi.

---

## 5. Admin paneli — to'liq qo'llanma

Admin `/admin` buyrug'i yoki `/start` orqali admin paneliga kiradi:

```
[ 📊 Hisobotlar ]  [ 👥 Mijozlar ]
[ 📥 Buyurtmalar ] [ 📋 Xizmatlar ]
[ 📰 Yangiliklar ] [ 📍 Manzil va xarita ]
[ 📢 Barchaga xabar yuborish ]
[ ⚙️ Biznes sozlamalari ] [ 👤 Mijoz rejimi ]
```

---

### 📊 Hisobotlar va jonli statistika

`📊 Hisobotlar` tugmasi bosilganda to'liq tahliliy dashboard ko'rsatiladi:
- Jami mijozlar, bugungi, haftalik va oylik yangi mijozlar soni.
- Jami buyurtmalar (⏳ Kutilayotgan, ✅ Qabul qilingan, ❌ Rad etilgan).
- Xizmatlar va e'lonlar holati.

**Davrlar bo'yicha hisobotlar (Inline tugmalar):**
- `📅 Bugungi hisobot` — aynan bugungi sana bo'yicha ko'rsatkichlar.
- `📅 Haftalik hisobot` — joriy dushanbadan boshlab hisoblangan ko'rsatkichlar.
- `📅 Oylik hisobot` — joriy oyning 1-sanasidan boshlab hisoblangan ko'rsatkichlar.
- `📊 Umumiy hisobot` — barcha vaqtlar bo'yicha to'liq ko'rsatkichlar.
- `🔄 Yangilash` — real vaqtda yangilash.

---

### 📥 Buyurtmalarni boshqarish (Qabul qilish / Rad etish)

1. Yangi buyurtma tushganda barcha adminlarga xabar boradi:
   ```
   🔔 YANGI XIZMAT BUYURTMASI!

   👤 Mijoz: Azam
   📞 Telefon: +998901234567
   💇 Xizmat: Pedikyur
   💰 Narxi: 180 000 so‘m
   📝 Izoh: Soat 15:00 ga yozilmoqchi.
   🕒 Sana: 01.11.2026, 17:30
   🆔 Buyurtma ID: #104
   ```
2. Adminga 3 ta tugma beriladi:
   - `✅ Qabul qilish` — buyurtma qabul qilinadi, admin xabariga qaysi admin ko'rib chiqqani yoziladi va mijozga tasdiq xabari yuboriladi.
   - `❌ Rad etish` — buyurtma rad etiladi va mijozga sababli muloyim tushuntirish yuboriladi.
   - `💬 Mijoz bilan bog'lanish` — mijozning shaxsiy Telegram profiliga yo'naltiradi.
3. Shuningdek, `📥 Buyurtmalar` menyusi orqali avvalgi barcha buyurtmalar ro'yxatini sahifalab (10 tadan) ko'rish mumkin.

---

### 📰 Yangiliklarni boshqarish va xabar tarqatish

`📰 Yangiliklar` menyusi orqali:
1. `➕ Yangi e'lon yaratish`:
   - 1-qadam: Sarlavha
   - 2-qadam: Asosiy matn
   - 3-qadam: Rasm yuklash (yoki `-` tashlab ketish)
   - 4-qadam: Amal qilish muddati (masalan: `15.11.2026` yoki `-`)
   - 5-qadam: **Preview** ko'rinishi:
     - `✅ Barchaga yuborish` — saqlanadi, chop etiladi va darhol barcha mijozlarga tarqatiladi.
     - `💾 Qoralama sifatida saqlash` — keyinchalik ishlatish uchun saqlanadi.
     - `❌ Bekor qilish`.
2. `📋 Barcha e'lonlar` — mavjud e'lonlarni ko'rish, tahrirlash, o'chirish yoki istalgan vaqtda barchaga qayta yuborish.

---

### 📍 Manzil va xaritani sozlash

`📍 Manzil va xarita` menyusi orqali:
- `🏢 Manzilni o'zgartirish` — biznesning matnli manzilini kiritish.
- `ℹ️ Mo'ljalni kiritish` — mo'ljal kiritish (masalan: *Metroning 2-chiqishi*).
- `📍 Telegram lokatsiya yuborish` — admin Telegram ilovasi orqali to'g'ridan-to'g'ri xarita nuqtasini (`Location`) yuboradi, bot koordinatalarni avtomatik saqlaydi.
- `🌐 Koordinata kiritish` — qo'lda kiritish (masalan: `41.2995, 69.2401`).
- `🗺 Google Maps havolasi` — Google Maps havolasini kiritish (URL formati tekshiriladi).
- `👁 Mijoz ko'rinishida sinash` — mijozga qanday ko'rinishini tekshirish.
- `🗑 Lokatsiyani tozalash` — barcha manzil ma'lumotlarini o'chirish.

---

### 📢 Barchaga tezkor xabar yuborish

Asosiy admin klaviaturasidagi `📢 Barchaga xabar yuborish` tugmasi orqali tezkor matn kiritib, barcha foydalanuvchilarga xabar tarqatish mumkin.
- Jarayon asinxron va xavfsiz (rate-limiting ~25 xabar/sekund).
- Botni bloklagan foydalanuvchilar umumiy jarayonni to'xtatmaydi.
- Xabar yetkazib bo'lingach, adminga yakuniy hisobot taqdim etiladi.

---

### 📋 Xizmatlar boshqaruvi
- `📋 Xizmatlar ro'yxati` — barcha xizmatlar (🟢 faol / 🔴 nofaol).
- `➕ Yangi xizmat qo'shish` — bosqichma-bosqich: nomi, narxi, davomiyligi, tavsifi, qo'shimcha ma'lumotlari.
- `✏️ Xizmatni tahrirlash` — har bir maydonni alohida tahrirlash.
- `👁 Xizmatni yoqish/o'chirish` — faollikni o'zgartirish (nofaol xizmatlar mijozlarga ko'rinmaydi).
- `🗑 Xizmatni o'chirish` — tasdiqlash bilan o'chirish.

---

### 👥 Mijozlar ro'yxati
- Botdan foydalangan barcha mijozlar (ismi, username, Telegram ID, ro'yxatdan o'tgan sana) sahifalab (10 tadan) ko'rsatiladi.

---

### ⚙️ Biznes sozlamalari
- Biznes nomi, tavsifi, operator kontakti va AI ko'rsatmalarini to'g'ridan-to'g'ri Telegram orqali tahrirlash.

---

### 👤 Mijoz rejimi
- Admin huquqini saqlagan holda botni oddiy mijoz sifatida sinab ko'rish imkoniyati. `/admin` orqali qaytiladi.

---

## 6. Real-vaqtli admin bildirishnomalari (Notifications)

1. **Yangi foydalanuvchi:**
   Faqat yangi mijoz birinchi marta botga kirganda barcha adminlarga yuboriladi:
   ```
   🆕 Yangi foydalanuvchi!

   👤 Ism: Azam Sagdullayev
   🔗 Username: @example
   🆔 Telegram ID: 123456789
   🕒 Sana: 01.11.2026
   📊 Jami foydalanuvchilar: 125
   ```
2. **Yangi xizmat buyurtmasi:**
   Mijoz buyurtma berishi bilan interaktiv tugmalar (`✅ Qabul qilish`, `❌ Rad etish`, `💬 Mijoz bilan bog'lanish`) bilan adminga boradi.

---

## 7. Avtomatik kunlik hisobot (Daily Report Scheduler)

- Har kuni soat **21:00 da (Asia/Tashkent)** fonda ishlovchi scheduler barcha adminlarga kunlik hisobot yuboradi:
  ```
  📊 KUNLIK HISOBOT

  📅 Sana: 01.11.2026

  🆕 Yangi mijozlar: 18
  📥 Yangi buyurtmalar: 12
  ✅ Qabul qilingan: 9
  ⏳ Kutilayotgan: 3
  ❌ Rad etilgan: 0
  ```
- **Idempotency mexanizmi:** Har bir yuborilgan hisobot `daily_report_logs` jadvaliga qayd etiladi. Bot qayta yoqilsa ham shu kun uchun qayta takroriy xabar yuborilmaydi.

---

## 8. Buyruqlar ro'yxati

| Buyruq | Kim uchun | Vazifasi |
|---|---|---|
| `/start` | Hamma | Botni ishga tushirish (admin uchun admin panel ochiladi) |
| `/admin` | Adminlar | Admin panelini ochish |
| `/cancel` | Hamma | Faol FSM amalini bekor qilish |
| `/stats` | Adminlar | Qisqa statistika (eski format saqlangan) |
| `/leads` | Adminlar | So'nggi kontaktlar |

---

## 9. Docker boshqaruv buyruqlari

```bash
# 1. Yangi kod bilan qayta qurish va ishga tushirish
docker compose up -d --build

# 2. Konteynerlar holati
docker compose ps

# 3. Botni qayta ishga tushirish
docker compose restart bot

# 4. To'xtatish (ma'lumotlar saqlanadi)
docker compose down
```

> ⚠️ **Hech qachon `docker compose down -v` buyrug'ini ishlatmang!** Bu PostgreSQL bazasini o'chiradi.

---

## 10. Loglarni tekshirish

```bash
# Botning oxirgi 100 ta logini ko'rish
docker compose logs --tail=100 bot

# Jonli kuzatish (real-time)
docker compose logs -f bot

# Faqat xatoliklarni filtrlab ko'rish
docker compose logs bot 2>&1 | grep -i error
```

---

## 11. Ko'p uchraydigan savollar va yechimlar

1. **"Sizda admin huquqi yo'q" xatosi:**
   - `.env` faylida `ADMIN_IDS` ga raqamli Telegram ID ingiz yozilganini tekshiring va `docker compose up -d` buyrug'ini bering.
2. **Xabar tarqatish (broadcast) to'xtab qolmaydimi?**
   - Yo'q, tizim har bir foydalanuvchini alohida xavfsiz blokda qayta ishlaydi. Bloklagan foydalanuvchilar o'tkazib yuboriladi va oxirida hisobot beriladi.
3. **Kunlik hisobot vaqtini o'zgartirish mumkinmi?**
   - Ha, `.env` faylida `DAILY_REPORT_TIME=20:00` kabi istalgan vaqtni (Toshkent vaqti bo'yicha) belgilashingiz mumkin.

---

## 12. Loyihadagi o'zgarishlar tarixi va ma'lumotlar tuzilmasi (Changelog)

### Versiya 2.2 yangiliklari:
- `announcements` jadvali — biznes yangiliklari va chegirmalari.
- `broadcast_campaigns` jadvali — xabar tarqatish monitoringi.
- `business_locations` jadvali — manzil, koordinatalar va Google Maps.
- `daily_report_logs` jadvali — kunlik hisobotlar arxivi.
- `service_orders` kengaytirildi (`note`, `handled_by_admin`, `updated_at`).
- Avtomatik kunlik 21:00 scheduler `app/reports.py`.
- Markazlashtirilgan real-vaqtli bildirishnomalar `app/notifications.py`.
- Mijoz klaviaturasiga `📰 Yangiliklar` va `📍 Manzilimiz` qo'shildi.

---

*Loyiha to'liq tayyor, sinovdan o'tgan va Docker konteynerida barqaror ishlamoqda.*
