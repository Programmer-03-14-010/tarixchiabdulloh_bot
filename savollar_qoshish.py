# -*- coding: utf-8 -*-
"""
savollar_qoshish.py
--------------------
Yangi savollarni botga QIYNALMASDAN qo'shish uchun skript.

QANDAY ISHLATILADI:
1. "savollar" papkasi ichiga .txt fayl(lar) qo'shing (yoki mavjudini tahrirlang).
   Har bir savol quyidagi FORMATDA yozilishi kerak (bo'sh qatordan keyin
   navbatdagi savol boshlanadi):

    #1. [6-sinf | Jahon tarixi | Qadimgi Misr va Mesopotamiya]
    Savol #1: Yangi Bobil podsholigini ravnaq topdirgan hukmdor kim?
    A) Navuxodonosor II
    B) Xammurapi
    C) Kipr II
    D) Doro I
    To'g'ri javob: A

   - [ ] ichidagi 3 ta qism: Sinf | Fan | Mavzu (mavzu — bo'lim nomi bo'lib,
     botda alohida "test to'plami" sifatida chiqadi).
   - "#1." dagi raqam va "Savol #1:" dagi raqam istalgan bo'lishi mumkin,
     ular shunchaki matn uchun, dastur ularga qaramaydi.
   - To'g'ri javob A, B, C yoki D harfi bilan ko'rsatiladi.

2. Terminalda shu papkada turib buyruqni ishga tushiring:

       python savollar_qoshish.py

3. Skript "savollar/" papkasidagi BARCHA .txt fayllarni o'qib,
   ularni birlashtirib, takrorlanuvchi (bir xil) savollarni olib tashlab,
   yangi "questions.json" faylini yaratadi. Botni qayta ishga tushirsangiz
   (yoki ishlab turgan bo'lsa, keyingi /start'da) yangi savollar ko'rinadi.

Eslatma: variantlarning tartibi (A/B/C/D o'rni) botda har safar
AVTOMATIK ARALASHTIRILADI, shuning uchun bu yerda qanday tartibda
yozishingiz muhim emas — faqat to'g'ri javobni to'g'ri harf bilan
belgilang.
"""

import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SOURCE_DIR = BASE_DIR / "savollar"
OUTPUT_FILE = BASE_DIR / "questions.json"

BLOCK_RE = re.compile(
    r"#?\d*\.?\s*\[([^\|\]]+)\|([^\|\]]+)\|([^\]]+)\]\s*\n"
    r"Savol\s*#?\d*:?\s*(.+?)\n"
    r"A\)\s*(.+?)\n"
    r"B\)\s*(.+?)\n"
    r"C\)\s*(.+?)\n"
    r"D\)\s*(.+?)\n"
    r"To'?g'?ri javob:\s*([ABCD])",
    re.MULTILINE,
)


def parse_file(path: Path):
    text = path.read_text(encoding="utf-8")
    results = []
    for m in BLOCK_RE.finditer(text):
        grade, subject, topic, question, a, b, c, d, correct = m.groups()
        opts = {"A": a.strip(), "B": b.strip(), "C": c.strip(), "D": d.strip()}
        results.append(
            {
                "grade": grade.strip(),
                "subject": subject.strip(),
                "topic": topic.strip(),
                "question": question.strip(),
                "options": [opts["A"], opts["B"], opts["C"], opts["D"]],
                "answer": opts[correct.strip()],
            }
        )
    return results


def main():
    if not SOURCE_DIR.exists():
        raise SystemExit(
            f"'{SOURCE_DIR}' papkasi topilmadi. Iltimos, shu nomdagi papka yarating "
            "va ichiga savollar yozilgan .txt fayl(lar) joylang."
        )

    txt_files = sorted(SOURCE_DIR.glob("*.txt"))
    if not txt_files:
        raise SystemExit(f"'{SOURCE_DIR}' papkasida .txt fayl topilmadi.")

    all_items = []
    for path in txt_files:
        items = parse_file(path)
        print(f"{path.name}: {len(items)} ta savol topildi")
        all_items.extend(items)

    # Takrorlanuvchilarni olib tashlash
    seen = set()
    unique_items = []
    for item in all_items:
        key = (item["question"], tuple(item["options"]), item["answer"])
        if key not in seen:
            seen.add(key)
            unique_items.append(item)

    duplicates = len(all_items) - len(unique_items)
    print(f"\nJami topilgan: {len(all_items)} ta")
    print(f"Takroriy (olib tashlandi): {duplicates} ta")
    print(f"Noyob savollar: {len(unique_items)} ta")

    # grade -> subject -> topic -> [questions]
    nested = {}
    for item in unique_items:
        g = nested.setdefault(item["grade"], {})
        s = g.setdefault(item["subject"], {})
        t = s.setdefault(item["topic"], [])
        t.append(
            {
                "question": item["question"],
                "options": item["options"],
                "answer": item["answer"],
            }
        )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(nested, f, ensure_ascii=False, indent=1)

    print(f"\n'{OUTPUT_FILE.name}' fayli yangilandi. ✅")
    print("Botni qayta ishga tushiring (yoki keyingi /start'da yangi savollar ko'rinadi).")


if __name__ == "__main__":
    main()
