# 📖 AzamAI Business Bot — To'liq Ishlatish Yo'riqnomasi

> Versiya: 2.1 | Til: O'zbek | Oxirgi yangilanish: 2026-11-01

---

## 📑 Mundarija

1. [Tizim talablari va arxitektura](#1-tizim-talablari-va-arxitektura)
2. [O'rnatish va Docker orqali ishga tushirish](#2-ornatish-va-docker-orqali-ishga-tushirish)
3. [ADMIN_IDS sozlash](#3-admin_ids-sozlash)
4. [Mijozlar uchun: Interaktiv xizmat tanlash va buyurtma berish](#4-mijozlar-uchun-interaktiv-xizmat-tanlash-va-buyurtma-berish)
   - [📋 Xizmatlar ro'yxatini ko'rish](#-xizmatlar-royxatini-korish)
   - [🔢 Raqam orqali xizmatni tanlash](#-raqam-orqali-xizmatni-tanlash)
   - [📞 Xizmatga buyurtma berish](#-xizmatga-buyurtma-berish)
   - [💬 AI yordamchi bilan suhbat](#-ai-yordamchi-bilan-suhbat)
5. [Admin paneli qo'llanmasi](#5-admin-paneli-qollanmasi)
   - [📊 Statistika va buyurtmalar](#-statistika-va-buyurtmalar)
   - [👥 Mijozlar ro'yxati](#-mijozlar-royxati)
   - [📥 Kontaktlar](#-kontaktlar)
   - [📋 Xizmatlar ro'yxati va batafsil ko'rish](#-xizmatlar-royxati-va-batafsil-korish)
   - [➕ Yangi xizmat qo'shish (bosqichma-bosqich)](#-yangi-xizmat-qoshish-bosqichma-bosqich)
   - [✏️ Xizmatni tahrirlash](#-xizmatni-tahrirlash)
   - [👁 Xizmatni yoqish / o'chirish (faollik)](#-xizmatni-yoqish--ochirish-faollik)
   - [🗑 Xizmatni o'chirish (tasdiqlash bilan)](#-xizmatni-ochirish-tasdiqlash-bilan)
   - [⚙️ Biznes sozlamalari](#-biznes-sozlamalari)
   - [👤 Mijoz rejimi](#-mijoz-rejimi)
6. [Admin bildirishnomalari (Notifications)](#6-admin-bildirishnomalari-notifications)
7. [Buyruqlar ro'yxati](#7-buyruqlar-royxati)
8. [Docker boshqaruv buyruqlari](#8-docker-boshqaruv-buyruqlari)
9. [Loglarni tekshirish](#9-loglarni-tekshirish)
10. [Ko'p uchraydigan savollar va yechimlar](#10-kop-uchraydigan-savollar-va-yechimlar)
11. [Loyihadagi oxirgi o'zgarishlar tarixi va ma'lumotlar tuzilmasi (Changelog)](#11-loyihadagi-oxirgi-ozgarishlar-tarixi-va-malumotlar-tuzilmasi-changelog)

---

## 1. Tizim talablari va arxitektura

| Komponent | Tavsif |
|---|---|
| Aiogram 3 | Asinxron Telegram bot frameworki (FSM MemoryStorage) |
| PostgreSQL 16 | Mijozlar, kontaktlar, xabarlar va buyurtmalar bazasi |
| SQLAlchemy 2.0 | Asinxron ORM |
| `business.json` | Xizmatlar va biznes sozlamalari (Docker read-write mount) |
| OpenAI API | AI maslahatchi tili va muloqoti |

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
POSTGRES_PASSWORD=1705
DATABASE_URL=postgresql+asyncpg://azam:1705@db:5432/azam_ai
AI_BASE_URL=https://api.openai.com/v1
AI_API_KEY=sk-proj-...
AI_MODEL=gpt-4o-mini
AI_TEMPERATURE=0.4
BUSINESS_CONFIG_PATH=business.json
```

### 2.3 Botni ishga tushirish

```bash
docker compose up -d --build
```

### 2.4 Ishlayotganini tekshirish

```bash
docker compose ps
```

---

## 3. ADMIN_IDS sozlash

1. O'zingizning numeric Telegram ID raqamingizni aniqlash uchun Telegram'da `@userinfobot` ga xabar yuboring.
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

## 4. Mijozlar uchun: Interaktiv xizmat tanlash va buyurtma berish

### 📋 Xizmatlar ro'yxatini ko'rish

Mijoz pastdagi `📋 Xizmatlar` tugmasini bosadi.

Bot faqat faol xizmatlarni dinamik raqamlangan ko'rinishda chiqaradi:

```
💇 Bizning xizmatlarimiz

1️⃣ Manikyur
2️⃣ Gel lak
3️⃣ Soch bo'yash
4️⃣ Qosh dizayni

👇 Batafsil ma'lumot olish uchun xizmat raqamini yuboring.
```

Shuningdek, xabar ostida qulay bir-bosishli inline tugmalar ham taqdim etiladi.

---

### 🔢 Raqam orqali xizmatni tanlash

Mijoz botga xizmat raqamini yozib yuboradi (masalan: `2` yoki `4`).

Bot aynan shu raqamdagi xizmatning to'liq ma'lumotlarini taqdim etadi:

```
💅 Pedikyur

💰 Narxi: 180 000 so'm

⏱ Davomiyligi: 60 daqiqa

📝 Tavsif:
Oyoq tirnoqlarini parvarish qilish, shakllantirish va professional ishlov berish. Jarayon maxsus steril vositalar yordamida amalga oshiriladi.

✨ Qo‘shimcha ma'lumot:
Professional mutaxassis tomonidan bajariladi.
```

**Tugmalar:**
- `📞 Buyurtma berish`
- `📋 Barcha xizmatlar`
- `👨‍💼 Operator bilan bog‘lanish`

**Xatoliklarni boshqarish:**
- Agar mijoz `0`, manfiy son yoki xizmatlar sonidan katta raqam yuborsa:
  `⚠️ Noto'g'ri xizmat raqami kiritildi. Mavjud xizmatlar: 1 dan 4 gacha. Iltimos, kerakli raqamni yuboring.`
- Agar mijoz matnli savol bersa (masalan: *"Samarqandda filial bormi?"*):
  Bot xizmat tanlash holatidan chiqib, savolni avtomatik ravishda AI yordamchiga yo'naltiradi.

---

### 📞 Xizmatga buyurtma berish

1. Mijoz xizmat tafsilotlarida `📞 Buyurtma berish` tugmasini bosadi.
2. Bot buyurtmachi ismini so'raydi (avtomatik taklif etadi).
3. Bot telefon raqamini so'raydi (`📱 Telefon raqamimni yuborish` tugmasi yoki matnli raqam orqali).
4. Buyurtma qabul qilingach:
   - Mijozga tasdiq xabari beriladi.
   - Baza (`service_orders` va `leads`) jadvallariga saqlanadi.
   - Barcha adminlarga tezkor bildirishnoma boradi.

---

### 💬 AI yordamchi bilan suhbat

Mijoz istalgan vaqtda biznesga oid savollarni yozishi mumkin. AI faqat biznes tasdiqlagan ma'lumotlar va faol xizmatlar asosida muloyim javob beradi.

---

## 5. Admin paneli qo'llanmasi

Admin `/admin` buyrug'i yoki `/start` orqali admin panelini ochadi:

```
[ 📊 Statistika ]  [ 👥 Mijozlar ]
[ 📥 Kontaktlar ]  [ 📋 Xizmatlar ro'yxati ]
[ ➕ Yangi xizmat qo'shish ] [ ✏️ Xizmatni tahrirlash ]
[ 🗑 Xizmatni o'chirish ] [ 👁 Xizmatni yoqish/o'chirish ]
[ ⚙️ Biznes sozlamalari ] [ 👤 Mijoz rejimi ]
```

---

### 📊 Statistika va buyurtmalar

`📊 Statistika` tugmasi bosilganda:
- Ro'yxatdan o'tgan mijozlar soni
- Qoldirilgan kontaktlar (leadlar) soni
- Qabul qilingan xizmat buyurtmalari soni
- AI bilan muloqot xabarlari soni
- Jami xizmatlar (faol va nofaol ko'rsatkichlari bilan)

---

### 📋 Xizmatlar ro'yxati va batafsil ko'rish

`📋 Xizmatlar ro'yxati` tugmasi bosilganda:
- Barcha xizmatlar ro'yxati (🟢 faol / 🔴 nofaol holati bilan) ko'rsatiladi.
- Admin istalgan xizmat ustiga bosib, uning barcha parametrlarini ko'rishi mumkin:
  - Nomi, narxi, davomiyligi
  - Batafsil tavsifi
  - Qo'shimcha ma'lumoti
  - Yaratilgan va yangilangan vaqti
- To'g'ridan-to'g'ri shu yerdan `✏️ Tahrirlash`, `👁 Faollikni o'zgartirish` yoki `🗑 O'chirish` mumkin.

---

### ➕ Yangi xizmat qo'shish (bosqichma-bosqich)

`➕ Yangi xizmat qo'shish` tugmasini bosing:
1. **Xizmat nomi:** (masalan: `Pedikyur`)
2. **Narxi:** (masalan: `180 000 so'm`)
3. **Davomiyligi:** (masalan: `60 daqiqa`)
4. **Batafsil tavsifi:** (yoki o'tkazib yuborish uchun `-`)
5. **Qo'shimcha ma'lumot:** (yoki o'tkazib yuborish uchun `-`)
6. **Tasdiqlash ko'rinishi:** Bot kiritilgan barcha ma'lumotlarni ko'rsatadi.
   - `✅ Saqlash` tugmasi bosilgach, xizmat darhol saqlanadi va mijozlarga ko'rinadi.
   - `❌ Bekor qilish` amaliyotni bekor qiladi.

---

### ✏️ Xizmatni tahrirlash

1. `✏️ Xizmatni tahrirlash` tugmasini bosing.
2. Xizmatni tanlang.
3. Kerakli maydonni tanlang:
   - `✏️ Nomini o'zgartirish`
   - `💰 Narxini o'zgartirish`
   - `⏱ Davomiyligini o'zgartirish`
   - `📝 Tavsifini o'zgartirish`
   - `ℹ️ Qo'shimcha ma'lumotni o'zgartirish`
4. Yangi qiymatni yuboring. O'zgarishlar darhol saqlanadi.

---

### 👁 Xizmatni yoqish / o'chirish (faollik)

1. `👁 Xizmatni yoqish/o'chirish` tugmasini bosing.
2. Xizmatni tanlang.
3. Xizmat holati teskarisiga o'zgaradi:
   - Agar faol bo'lsa → 🔴 **Nofaol qilinadi** (mijozlardan yashiriladi va mijoz raqam orqali ham uni tanlay olmaydi).
   - Agar nofaol bo'lsa → 🟢 **Faollashtiriladi** (yana mijozlar ro'yxatida ko'rinadi).

---

### 🗑 Xizmatni o'chirish (tasdiqlash bilan)

1. `🗑 Xizmatni o'chirish` tugmasini bosing.
2. O'chiriladigan xizmatni tanlang.
3. Bot xizmat ma'lumotlarini chiqarib, tasdiq so'raydi:
   - `🗑 Ha, o'chirish` — butunlay o'chiriladi.
   - `❌ Bekor qilish` — o'chirish bekor qilinadi.

---

### ⚙️ Biznes sozlamalari

- Biznes nomi, tavsifi, operator kontakti va AI qoidalarini to'g'ridan-to'g'ri Telegram orqali tahrirlash imkoniyati.

---

### 👤 Mijoz rejimi

- Admin sifatida mijoz rejimiga o'tib, bot mijozlar uchun qanday ishlashini sinab ko'rish.
- Adminlik huquqi saqlanadi; istalgan vaqtda `/admin` orqali qaytish mumkin.

---

## 6. Admin bildirishnomalari (Notifications)

Mijoz xizmatga buyurtma berganda, barcha adminlarga quyidagi xabar yetkaziladi:

```
🔔 Yangi xizmat buyurtmasi

👤 Mijoz: Azam
📞 Telefon: +998901234567
💅 Xizmat: Pedikyur
💰 Narxi: 180 000 so'm
🕒 Vaqti: 2026-11-01 14:30
🆔 Telegram ID: 6686448989
```

---

## 7. Buyruqlar ro'yxati

| Buyruq | Kim uchun | Vazifasi |
|---|---|---|
| `/start` | Hamma | Botni ishga tushirish (admin uchun admin panel ochiladi) |
| `/admin` | Adminlar | Admin panelini ochish |
| `/cancel` | Hamma | Har qanday faol jarayonni bekor qilish |
| `/stats` | Adminlar | Qisqa statistika |
| `/leads` | Adminlar | So'nggi kontaktlar |

---

## 8. Docker boshqaruv buyruqlari

```bash
# Yangi kod bilan qayta qurish va ishga tushirish
docker compose up -d --build

# Konteynerlar holati
docker compose ps

# Botni qayta ishga tushirish (rebuild qilmasdan)
docker compose restart bot

# To'xtatish (ma'lumotlar saqlanadi)
docker compose down
```

> ⚠️ **Hech qachon `docker compose down -v` buyrug'ini ishlatmang!** Bu ma'lumotlar bazasini o'chirib yuboradi.

---

## 9. Loglarni tekshirish

```bash
# Botning oxirgi 100 ta logini ko'rish
docker compose logs --tail=100 bot

# Jonli kuzatish (real-time)
docker compose logs -f bot

# Faqat xatoliklarni filtrlab ko'rish
docker compose logs bot 2>&1 | grep -i error
```

---

## 10. Ko'p uchraydigan savollar va yechimlar

1. **"Sizda admin huquqi yo'q" xatosi:**
   - `.env` faylida `ADMIN_IDS` ga Telegram numeric ID ingiz kiritilganini tekshiring va `docker compose up -d` buyrug'ini bering.
2. **Xizmat qo'shilsa-yu, restartdan so'ng yo'qolib qolsa:**
   - `docker-compose.yml` da `./business.json:/app/business.json:rw` o'rnatilganini tekshiring (barcha o'zgarishlar mezbon tizimga to'g'ridan-to'g'ri yoziladi).
3. **Mijoz xizmat raqamini yuborganida javob bermasa:**
   - Xizmat faol holatdaligini tekshiring. Nofaol xizmatlar mijozlarga ko'rinmaydi va tanlab bo'lmaydi.

---

## 11. Loyihadagi oxirgi o'zgarishlar tarixi va ma'lumotlar tuzilmasi (Changelog)

### 📌 11.1 Kiritilgan o'zgarishlar mohiyati

Oldingi versiyada mijoz `📋 Xizmatlar` tugmasini bosganda faqat oddiy matnli xizmatlar ro'yxati ko'rsatilardi va u bilan interaktiv muloqot qilib bo'lmasdi. Xizmatlarni boshqarish imkoniyatlari ham cheklangan edi.

**Oxirgi yangilanishda amalga oshirilgan ishlar:**
1. **Interaktiv raqamli tanlov:** Mijoz botga xizmat raqamini (masalan: `4`) yuborishi bilan aynan shu xizmatning to'liq sahifasi ochiladi.
2. **Buyurtma berish mexanizmi (`ServiceOrder`):** Mijoz xizmatni ko'rib, `📞 Buyurtma berish` tugmasi orqali o'z ismi va raqamini qoldiradi.
3. **Adminlarga tezkor ogohlantirish:** Har bir buyurtma haqida barcha adminlarga Telegram orqali formatlangan bildirishnoma yetkaziladi.
4. **Admin tomonidan xizmatlarni to'liq boshqarish:** Xizmat qo'shish (5 bosqichli preview bilan), tahrirlash, o'chirish va faollashtirish/nofaol qilish imkoniyati yaratildi.
5. **AI yordamchining faol xizmatlarga bog'lanishi:** AI faqat faol (`is_active=True`) xizmatlarni tavsiya qiladi.

---

### 🗃 11.2 Xizmatlar ma'lumotlar tuzilmasi (`business.json`)

Har bir xizmat obyekti quyidagi to'liq tuzilishga ega:

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

#### Maydonlar tavsifi:
| Maydon | Turi | Tavsif | Misol |
|---|---|---|---|
| `id` | `str` | Noyob xizmat identifikatori | `"srv_1"` |
| `name` | `str` | Xizmat nomi | `"Manikyur"` |
| `price` | `str` | Xizmat narxi | `"120 000 so'mdan"` |
| `duration` | `str` | Davomiyligi | `"60 daqiqa"` |
| `description` | `str` | Xizmatning to'liq tavsifi | `"Apparatli tozalash..."` |
| `additional_info` | `str` | Qo'shimcha eslatma yoki qulayliklar | `"Steril vositalar..."` |
| `is_active` | `bool` | Mijozlarga ko'rinish holati (`true`/`false`) | `true` |
| `created_at` | `str` | Yaratilgan sana va vaqt | `"2026-10-31 18:00"` |
| `updated_at` | `str` | Oxirgi tahrirlangan vaqt | `"2026-11-01 14:00"` |

---

### 🗄 11.3 Ma'lumotlar bazasi tuzilmasi (`ServiceOrder`)

Mavjud jadvallarga qo'shimcha ravishda PostgreSQL da yangi `service_orders` jadvali joriy qilindi:

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

---

### 📂 11.4 Fayllar kesimida o'zgarishlar

1. **`app/services_manager.py` (Yangi):**
   - Xizmatlarni xavfsiz boshqarish bo'yicha markaziy modul.
   - Atomik yozish (`.tmp` fayl orqali almashtirish) kiritilgan bo'lib, fayl buzilishining oldini oladi.
   - `get_active_service_by_number(num)` — foydalanuvchi yuborgan 1-asosli raqamni aniq topadi.
2. **`app/handlers.py`:**
   - `CustomerServiceFSM.selecting_service` holati qo'shildi.
   - Raqam yuborilganda xizmat tafsilotlari chiqadi, nomutanosib raqamlar do'stona xatolik bilan qaytariladi.
   - Matnli savollar AI chatga uzluksiz o'tkaziladi.
   - `CustomerOrderFSM` — xizmatga buyurtma berish jarayoni va barcha adminlarga bildirishnoma yuborish funksiyasi qo'shildi.
3. **`app/admin_handlers.py`:**
   - Xizmatlarni to'liq boshqarish menyulari va FSM jarayonlari (`AddServiceFSM`, `EditServiceFSM`) kengaytirildi.
   - Har bir xizmat holatini yoqish/o'chirish (`👁 Xizmatni yoqish/o'chirish`) qo'shildi.
4. **`app/keyboards.py`:**
   - Xizmat tafsilotlari ostidagi inline tugmalar (`📞 Buyurtma berish`, `📋 Barcha xizmatlar`, `👨‍💼 Operator bilan bog'lanish`).
   - Admin xizmatlarini tahrirlash va tasdiqlash klaviaturalari qo'shildi.
5. **`app/ai.py`:**
   - Tizim prompti filtri faqat faol xizmatlarni AI ga taqdim etadigan qilindi.

---

*Hujjat to'liq yangilandi va loyiha ishchi holatda.*
