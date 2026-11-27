# Tarixchi Abdulloh — Telegram Mini App

Bot `/start` bosilganda **«📖 Ilovani ochish»** tugmasini chiqaradi, test, reyting, audio va kitoblar esa
Telegram ichida ochiladigan ilovada ishlaydi.

## Ishga tushirish

```bash
pip install -r requirements.txt

export BOT_TOKEN="BotFather'dan olingan yangi token"
export WEBAPP_URL="https://sizning-domeningiz.uz"     # ilova joylashgan HTTPS manzil
export GEMINI_API_KEY="AIza..."                        # ixtiyoriy: Gemini AI bilan fayldan savol ajratish (aistudio.google.com/apikey)

python run.py          # bot + veb-server (PORT=8080)
```

**Muhim:** Telegram Mini App faqat **HTTPS** manzilda ishlaydi. Sinash uchun `cloudflared tunnel --url http://localhost:8080`
yoki `ngrok http 8080` bergan manzilni `WEBAPP_URL` ga yozing. Doimiy ishlash uchun VPS + nginx (SSL) yoki Render/Railway.
BotFather → `/mybots` → Bot → *Bot Settings → Menu Button* ham ilovani ochishi uchun `WEBAPP_URL` ni kiritishingiz shart emas
(bot o'zi o'rnatadi).

## ⚠️ Token xavfsizligi
Eski `config.py` ichida bot tokeni ochiq yozilgan edi. Uni **BotFather → /revoke** orqali almashtiring va endi tokenni
faqat `BOT_TOKEN` muhit o'zgaruvchisida saqlang (yangi `config.py` kodga token yozmaydi).

## Rollar
- **Admin** — `config.py` dagi `ADMIN_PHONES` (ro'yxatdan o'tishda yuborilgan telefon raqam) yoki `ADMIN_IDS` (Telegram ID, vergul bilan) orqali.
- **Foydalanuvchi** — faqat test yechadi, reyting/audio/kitoblarni ko'radi.

## Admin imkoniyatlari (ilovadagi «Admin» bo'limi)
| Funksiya | Qayerda |
|---|---|
| Fayldan (Word/PDF/TXT) savollarni qo'shish — sinf, fan, mavzuni avtomatik ajratadi, oldindan ko'rsatadi | Admin → *Sun'iy intellekt bilan fayldan qo'shish* |
| Bitta savolni qo'lda qo'shish | Admin → *Savol qo'shish* |
| Har bir savol tagida **Tahrirlash / O'chirish** | Test paytida va Admin → *Savollar bazasi* |
| **Sinfni / mavzuni o'chirish** (🗑 tugmalari) | Sinf va mavzu ro'yxatlarida |
| Audio qo'shish/o'chirish | *Audiolar* bo'limi (yoki Admin) |
| Kitob qo'shish — birinchi kitob qo'shilgach **«Kitoblar»** bo'limi hamma uchun paydo bo'ladi | Admin → *Kitob qo'shish* |

### Fayl formati
Standart: savol matni, `A) B) C) D)` variantlar va `Javob: B` qatori. `1-MAVZU. …` sarlavhalari mavzu bo'ladi,
`8 sinf` / `O'zbekiston tarixi` sarlavhalari yoki fayl nomidan sinf va fan aniqlanadi.
Format nostandart bo'lsa yoki sinf/mavzu aniqlanmasa — `GEMINI_API_KEY` bo'lganda Gemini AI o'zi ajratadi (model: `GEMINI_MODEL`, standart `gemini-2.5-flash`).
Qo'shishda takroriy savollar o'tkazib yuboriladi; «eski savollarni almashtirish» belgisi bilan sinf+fanni yangilash mumkin.

## Foydalanuvchi uchun
- Eski botdagi hamma narsa: ro'yxatdan o'tish, 3-2-1 sanoq, sinf → fan → mavzu (yoki «Barcha mavzular»), har savolga 30 soniya,
  variantlar aralashtiriladi, «Tugatish», batafsil natija (to'g'ri / xato / o'tkazib yuborilgan).
- **Reyting:** har to'g'ri javob = **0,5 ball**; haftalik (7 kun), 1 oylik (30 kun), 3 oylik (90 kun).
- **Qo'shimchalar:** kunlik seriya 🔥, daraja tizimi, **«Xatolar ustida ishlash»** (oxirgi xato qilingan savollar), audio pleer (tezlik, ±15 s).

## Ma'lumotlar
Hammasi `data/` papkasida: `users.db` (foydalanuvchilar, savollar, ball), `audio/`, `books/`.
Birinchi ishga tushishda `questions.json` bazaga o'tkaziladi (11-sinf olib tashlangan, 8-sinf O'zbekiston tarixi — 31 mavzu, 580 savol — yangi fayldan).
Zaxira uchun `data/` papkasini nusxalab turing.

## Fayllar
```
run.py        bot + server        server.py   API (Flask)       bot.py     /start va ro'yxatdan o'tish
db.py         baza                importer.py fayl/AI parser    config.py  sozlamalar
static/       index.html, style.css, app.js, bg.svg (Registon fon rasmi)
```
Mahalliy sinash (Telegramsiz): `DEV_MODE=1 python run.py` (BOT_TOKEN bermasangiz faqat veb-server ishlaydi), so'ng brauzerda
`http://localhost:8080/?dev=<telegram_id>`. **Serverda DEV_MODE ni hech qachon yoqmang.**
