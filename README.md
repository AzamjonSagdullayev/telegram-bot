# AzamAI Business — Telegram AI Assistant & Interactive Admin Bot

Telegram orqali bizneslar uchun mo'ljallangan sun'iy intellektli yordamchi va interaktiv boshqaruv tizimi.

## 🚀 Asosiy imkoniyatlar

1. **Interaktiv xizmatlar tanlovi (Mijozlar uchun):**
   - `📋 Xizmatlar` bosilganda barcha faol xizmatlar raqamlangan ro'yxatda chiqadi (1️⃣, 2️⃣, 3️⃣...).
   - Mijoz xizmat raqamini (masalan: `4`) xabar qilib yuborsa, bot aynan shu xizmat haqida to'liq ma'lumotni chiqaradi.
   - Noto'g'ri raqamlar (0, manfiy yoki mavjud bo'lmagan) kiritilganda tushunarli ogohlantirish beriladi.
   - Matnli savollar bevosita AI yordamchiga yo'naltiriladi.
   - Har bir xizmat ostida `📞 Buyurtma berish`, `📋 Barcha xizmatlar` va `👨‍💼 Operator bilan bog'lanish` tugmalari mavjud.

2. **Xizmatga buyurtma berish (Booking inquiry):**
   - Mijoz `📞 Buyurtma berish` tugmasini bosganda ismi va telefon raqami so'raladi.
   - Buyurtma bazaga (`service_orders` va `leads` jadvallariga) saqlanadi.
   - Barcha adminlarga tezkor bildirishnoma (notification) yuboriladi.

3. **Telegram Admin Paneli:**
   - `📊 Statistika` — mijozlar, kontaktlar, xizmat buyurtmalari, xabarlar va xizmatlar soni.
   - `👥 Mijozlar` — sahifalangan mijozlar ro'yxati (10 tadan).
   - `📥 Kontaktlar` — mijozlar telefon raqamlari.
   - `📋 Xizmatlar ro'yxati` — har bir xizmatni batafsil ko'rish va boshqarish.
   - `➕ Yangi xizmat qo'shish` — bosqichma-bosqich (nomi, narxi, davomiyligi, tavsifi, qo'shimcha ma'lumot) va saqlashdan oldin ko'rib chiqish.
   - `✏️ Xizmatni tahrirlash` — har qanday xizmat maydonini alohida o'zgartirish.
   - `👁 Xizmatni yoqish/o'chirish` — faollik holatini o'zgartirish (nofaol xizmatlar mijozlarga ko'rinmaydi).
   - `🗑 Xizmatni o'chirish` — tasdiqlash bilan xavfsiz o'chirish.
   - `⚙️ Biznes sozlamalari` — biznes nomi, tavsif, operator matni va AI qoidalarini Telegram'dan tahrirlash.
   - `👤 Mijoz rejimi` — admin uchun mijoz rejimiga o'tib botni tekshirish.

---

## 🛠 O'rnatish va ishga tushirish

### 1. `.env` faylini sozlash

```bash
cp .env.example .env
nano .env
```

Quyidagi o'zgaruvchilarni to'ldiring:
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
```

### 2. Docker bilan ishga tushirish

```bash
# Konteynerlarni qurish va ishga tushirish
docker compose up -d --build

# Holatni tekshirish
docker compose ps

# Loglarni kuzatish
docker compose logs --tail=100 -f bot
```

---

## 📦 Xizmatlar ma'lumotlar tuzilmasi (`business.json`)

Har bir xizmat quyidagi to'liq maydonlarga ega:
- `id` — noyob identifikator (masalan: `srv_1`)
- `name` — xizmat nomi
- `price` — narxi
- `duration` — davomiyligi
- `description` — batafsil tavsif
- `additional_info` — qo'shimcha ma'lumotlar
- `is_active` — faollik holati (`true` yoki `false`)
- `created_at` — yaratilgan sana
- `updated_at` — oxirgi o'zgartirilgan sana

Barcha o'zgarishlar `business.json` fayliga darhol yoziladi va Docker restartdan keyin ham saqlanib qoladi.

---

## 🗄 Ma'lumotlar bazasi va migratsiya

Mavjud jadvallar (`customers`, `leads`, `chat_messages`) saqlangan holda yangi `service_orders` jadvali qo'shildi:
- `id` — primary key
- `telegram_id` — mijozning Telegram ID raqami
- `customer_name` — buyurtmachi ismi
- `phone` — telefon raqami
- `service_id` — xizmat ID si
- `service_name` — xizmat nomi
- `service_price` — xizmat narxi
- `status` — buyurtma holati (`yangi`, `tasdiqlangan`, va h.k.)
- `created_at` — buyurtma vaqti

Bot ishga tushganda SQLAlchemy `init_db()` funksiyasi orqali ushbu jadval avtomatik tarzda yaratiladi. Hech qanday qo'lda SQL komanda yozish talab qilinmaydi va mavjud ma'lumotlar saqlanadi.

---

## 🧪 Sinov ssenariylari

1. **Mijoz xizmatlar ro'yxatini ochadi:**
   - `📋 Xizmatlar` tugmasini bosing.
   - Faol xizmatlar raqamlangan ro'yxatda chiqadi.
2. **Xizmat raqamini yuborish:**
   - Botga `4` raqamini yuboring.
   - 4-xizmatning to'liq ma'lumotlari chiqadi.
3. **Noto'g'ri raqam kiritish:**
   - Botga `0`, `-1` yoki `99` yuboring.
   - Noto'g'ri raqam haqida ogohlantirish chiqadi.
4. **Buyurtma berish:**
   - `📞 Buyurtma berish` tugmasini bosing.
   - Ism va telefon raqamingizni yuboring.
   - Mijozga tasdiqnoma, adminlarga esa bildirishnoma boradi.
5. **Admin xizmat boshqaruvi:**
   - `/admin` buyrug'ini yuboring.
   - `📋 Xizmatlar ro'yxati` orqali xizmatlarni ko'ring.
   - `➕ Yangi xizmat qo'shish` orqali yangi xizmat qo'shing.
   - `👁 Xizmatni yoqish/o'chirish` orqali xizmatni nofaol qilib ko'ring va mijoz ro'yxatida yashiringanini tekshiring.
