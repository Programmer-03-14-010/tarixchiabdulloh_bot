# Tarix bilim bot (Telegram) — v2

@QuizBot uslubidagi tarix test boti: ro'yxatdan o'tish → "Testni boshlash"
tugmasi → 3-2-1 sanoq → sinf/fan/mavzu tanlash → 35 soniyalik taymerli
test savollari → batafsil natija (to'g'ri/xato/o'tkazib yuborilgan).

## Ishga tushirish

```bash
pip install -r requirements.txt
export BOT_TOKEN="123456:ABC-DEF..."   # yoki bot.py faylida to'g'ridan-to'g'ri yozing
python bot.py
```

## Bot qanday ishlaydi

1. `/start` — ro'yxatdan o'tmagan bo'lsa, ism-familya va telefon raqami
   (kontakt tugmasi orqali) so'raladi.
2. Ro'yxatdan o'tgach (yoki keyingi `/start`/`/menu`'da) **"🎯 Testni
   boshlash"** tugmasi chiqadi.
3. Tugma bosilgach, bot **3️⃣ → 2️⃣ → 1️⃣ → 🚀 Boshladik!** sanog'ini
   ko'rsatadi.
4. Keyin **sinf → fan → mavzu (test to'plami)** tanlanadi. Har bir mavzu
   nechta savoldan iboratligi tugma ustida ko'rsatiladi; "🎲 Barcha
   mavzular" tugmasi shu fandagi barcha savollarni birlashtiradi.
5. Mavzu tanlangach, @QuizBot uslubidagi ma'lumot kartochkasi chiqadi
   (nom, savollar soni, har bir savol uchun vaqt) va **"🏁 Boshlash"**
   tugmasi bilan test boshlanadi.
6. Savollar Telegramning **o'z quiz-so'rovnoma (poll)** formatida
   yuboriladi — bu degani har bir savol ostida **haqiqiy, Telegramning
   o'zi chizadigan 35 soniyalik teskari sanoq doirasi** ko'rinadi (bu
   qo'lda yozilgan taymerdan ancha ishonchli va tez ishlaydi). Javob
   berilgach, to'g'ri/xato ekani darhol ko'rinadi. 35 soniya ichida
   javob berilmasa, savol avtomatik yopiladi va **"o'tkazib yuborilgan"**
   sifatida hisoblanadi.
7. Istalgan vaqt `/stop` buyrug'i bilan testni erta yakunlash mumkin.
8. Oxirida: ism-familya, ✅ to'g'ri, ❌ xato, ⏭ o'tkazib yuborilgan
   sonlari va har bir savol bo'yicha batafsil ro'yxat yuboriladi.

## Yangi savollarni QIYNALMASDAN qo'shish

Barcha savollar `savollar/` papkasidagi `.txt` fayllarda saqlanadi.
Yangi savol qo'shish uchun:

1. `savollar/` papkasiga yangi `.txt` fayl qo'shing (yoki mavjudini
   tahrirlang) — quyidagi formatda:

   ```
   #1. [6-sinf | Jahon tarixi | Qadimgi Misr va Mesopotamiya]
   Savol #1: Yangi Bobil podsholigini ravnaq topdirgan hukmdor kim?
   A) Navuxodonosor II
   B) Xammurapi
   C) Kipr II
   D) Doro I
   To'g'ri javob: A
   ```

   - `[ ]` ichida: **Sinf | Fan | Mavzu** (mavzu = botda alohida
     "test to'plami" bo'lib chiqadi).
   - Har bir savol albatta 4 ta variant (A, B, C, D) va bitta
     "To'g'ri javob:" qatoriga ega bo'lishi kerak.
   - Savollar orasida bo'sh qator qoldiring.
   - Variantlar tartibi (A/B/C/D o'rni) muhim emas — bot ularni har
     safar avtomatik aralashtirib beradi.

2. Terminalda shu buyruqni ishga tushiring:

   ```bash
   python savollar_qoshish.py
   ```

   Bu `savollar/` papkasidagi barcha `.txt` fayllarni o'qib,
   takrorlanuvchi savollarni olib tashlab, `questions.json` faylini
   yangilaydi.

3. Botni qayta ishga tushiring (yoki ishlab tursa, keyingi foydalanuvchi
   sessiyasida yangi savollar avtomatik ko'rinadi, chunki `questions.json`
   bot ishga tushganda o'qiladi — katta o'zgarish kiritgach botni qayta
   ishga tushirish tavsiya etiladi).

## MUHIM — hozirgi savollar bazasi haqida

Siz yuborgan `500_tarix_testlari.txt` faylida 500 ta yozuv bo'lsa-da,
tekshirganimda ular orasida atigi **30 ta noyob savol** borligi
aniqlandi (qolganlari xuddi shu 30 taning takrorlari edi). Hozircha
bot shu **30 ta savol** bilan ishlaydi:

- 6-sinf: Jahon tarixi (10 ta), O'zbekiston tarixi (5 ta)
- 7-sinf: Jahon tarixi (5 ta), O'zbekiston tarixi (5 ta)
- 8-sinf: Tarix (5 ta)

Ko'proq savol qo'shmoqchi bo'lsangiz, yuqoridagi bo'limda ko'rsatilgan
formatda yangi `.txt` fayl tayyorlab, `savollar/` papkasiga qo'shib,
`savollar_qoshish.py` ni ishga tushirishingiz kifoya.

## Keyingi bosqich uchun rejalashtirilgan (hozircha amalga oshirilmagan)

Suhbatda aytilgan quyidagi ikkita funksiya **hozircha qo'shilmadi**,
chunki ular alohida katta ish talab qiladi — xohlasangiz keyingi safar
so'rang:

- 🏆 Foydalanuvchilarni reyting/o'rinlarga joylashtirish (leaderboard)
- 🌐 O'zbekcha / ruscha / inglizcha til tanlash imkoniyati

## Fayllar tuzilishi

```
bot.py                  — asosiy bot kodi
questions.json          — savollar bazasi (avtomatik yaratiladi)
savollar_qoshish.py     — matn fayldan questions.json yasovchi skript
savollar/               — bu yerga .txt formatdagi savol fayllarini joylang
requirements.txt
users.db                — ro'yxatdan o'tgan foydalanuvchilar (avtomatik yaratiladi)
```
"# tarixchiabdulloh_bot" 
