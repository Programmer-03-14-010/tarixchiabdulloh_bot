# -*- coding: utf-8 -*-
"""
Fayldan (docx / txt / pdf) savollarni ajratib olish.

1) Avval tez va bepul "lokal" parser ishlaydi (A) B) C) D) + "Javob: B" formatidagi fayllar).
2) Agar format nostandart bo'lsa yoki sinf/fan/mavzu aniqlanmagan bo'lsa — AI (Google Gemini) yordamga keladi
   (GEMINI_API_KEY berilgan bo'lsa).
"""
import io
import json
import re
from concurrent.futures import ThreadPoolExecutor

import config
from db import norm_name

SKIP_LINE_RE = re.compile(r"\.(docx?|pdf|txt)\s*$", re.I)           # "8 SINF QO'LLANMA.docx" kabi manba qatorlari
OPT_RE = re.compile(r"^\(?([A-Da-d])[\)\.\]]\s*(.+)$")
ANS_RE = re.compile(r"^(?:to['’ʻ‘]?g['’ʻ‘]?ri\s+)?(?:javob|answer)\s*[:\-–]?\s*\(?([A-Da-d])\)?\b", re.I)
TOPIC_RE = re.compile(r"^(\d+)\s*[-–.]?\s*MAVZU\s*[.:\-–]?\s*(.+)$", re.I)
BRACKET_RE = re.compile(r"^#?\d*\.?\s*\[([^|\]]+)\|([^|\]]+)\|([^\]]+)\]\s*$")
QNUM_RE = re.compile(r"^(?:savol\s*)?#?\d+\s*[\.\):]\s*(.+)$", re.I)
QPREFIX_RE = re.compile(r"^savol\s*#?\d*\s*:\s*(.+)$", re.I)
GRADE_HEAD_RE = re.compile(r"^(\d{1,2})\s*[-–]?\s*sinf\b[\s:.\-–]*(.{0,40})$", re.I)
SUBJECT_HEAD_RE = re.compile(r"^(o['’ʻ‘]?zbekiston tarixi|jahon tarixi)\s*[:.]?$", re.I)


def _n(s: str) -> str:
    s = (s or "").replace("ʻ", "'").replace("‘", "'").replace("’", "'").replace("ʼ", "'")
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------------------
def extract_text(filename: str, data: bytes) -> str:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext == "docx":
        from docx import Document
        doc = Document(io.BytesIO(data))
        lines = [p.text for p in doc.paragraphs]
        for t in doc.tables:
            for row in t.rows:
                lines.extend(cell.text for cell in row.cells)
        return "\n".join(lines)
    if ext == "pdf":
        try:
            from pypdf import PdfReader
        except ImportError as e:
            raise ValueError("PDF o'qish uchun 'pypdf' o'rnatilmagan (pip install pypdf)") from e
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    for enc in ("utf-8-sig", "cp1251", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", "ignore")


# ---------------------------------------------------------------------------
def parse_local(text: str):
    """Qaytaradi: (items, skipped). item = {grade, subject, topic, question, options[4], answer}"""
    items, skipped = [], 0
    grade = subject = topic = None
    q, opts, ans = None, [], None

    def flush():
        nonlocal q, opts, ans, skipped
        if q:
            m = {k: v for k, v in opts}
            if len(m) == 4 and ans in m and len({_n(v) for v in m.values()}) == 4:
                items.append({
                    "grade": grade, "subject": subject, "topic": topic,
                    "question": _n(q), "options": [_n(m[k]) for k in "ABCD"], "answer": _n(m[ans]),
                })
            else:
                skipped += 1
        q, opts, ans = None, [], None

    for raw in text.split("\n"):
        line = raw.strip()
        if not line or SKIP_LINE_RE.search(line):
            continue
        mb = BRACKET_RE.match(line)
        if mb:
            flush()
            grade, subject, topic = (norm_name(x) for x in mb.groups())
            continue
        mt = TOPIC_RE.match(line)
        if mt and len(line) < 220:
            flush()
            topic = norm_name(mt.group(2))
            continue
        mg = GRADE_HEAD_RE.match(line)
        if mg and not q and not OPT_RE.match(line):
            flush()
            grade = f"{int(mg.group(1))}-sinf"
            rest = mg.group(2)
            ms = SUBJECT_HEAD_RE.match(rest.strip()) if rest else None
            if ms:
                subject = _subject_name(ms.group(1))
            continue
        ms = SUBJECT_HEAD_RE.match(line)
        if ms and not q:
            subject = _subject_name(ms.group(1))
            continue
        ma = ANS_RE.match(line)
        if ma and q:
            ans = ma.group(1).upper()
            flush()
            continue
        mo = OPT_RE.match(line)
        if mo and q and len(opts) < 4:
            opts.append((mo.group(1).upper(), mo.group(2)))
            continue
        # Savol matni (yoki uning davomi)
        if q and not opts:
            q += " " + line
        else:
            flush()
            mq = QPREFIX_RE.match(line) or QNUM_RE.match(line)
            q = mq.group(1) if mq else line
    flush()
    return items, skipped


def _subject_name(s: str) -> str:
    return "Jahon tarixi" if s.lower().startswith("jahon") else "O'zbekiston tarixi"


def detect_meta(filename: str, text: str):
    """Fayl nomi/boshidan sinf va fanni taxmin qiladi."""
    probe = _n(filename + " " + text[:1500]).lower()
    grade = subject = None
    m = re.search(r"(\d{1,2})\s*[-–]?\s*sinf", probe)
    if m:
        grade = f"{int(m.group(1))}-sinf"
    fn = _n(filename).lower()
    if re.search(r"o'?zbek", fn):
        subject = "O'zbekiston tarixi"
    elif re.search(r"jahon|dunyo|world", fn):
        subject = "Jahon tarixi"
    return grade, subject


# ---------------------------------------------------------------------------
# AI qismi
# ---------------------------------------------------------------------------
def ai_enabled() -> bool:
    return bool(config.GEMINI_API_KEY)


def _ask_json(system: str, user: str, max_tokens: int = 8000):
    """Gemini REST API (qo'shimcha kutubxona kerak emas). Javobni JSON sifatida qaytaradi."""
    import urllib.request
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL}:generateContent"
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "maxOutputTokens": 8192,   # Gemini'ning "fikrlash" tokenlari ham shu limitga kiradi
            "temperature": 0,
        },
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": config.GEMINI_API_KEY},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    parts = data["candidates"][0]["content"]["parts"]
    text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    return json.loads(text)


def ai_classify(filename: str, text: str):
    """Fayl qaysi sinf va fanga tegishli ekanini AI aniqlaydi."""
    system = ("Sen o'zbek maktab tarix darsliklari bo'yicha yordamchisan. Faqat JSON qaytar: "
              '{"grade": "8-sinf", "subject": "O\'zbekiston tarixi" yoki "Jahon tarixi"}. '
              "Aniqlab bo'lmasa, qiymatni null qil.")
    try:
        r = _ask_json(system, f"Fayl nomi: {filename}\n\nMatndan parcha:\n{text[:3500]}", 300)
        g = norm_name(r.get("grade") or "") or None
        s = norm_name(r.get("subject") or "") or None
        return g, s
    except Exception:
        return None, None


def ai_extract(text: str, filename: str):
    """Nostandart matndan savollarni AI ajratib oladi (sinf/fan/mavzuni ham o'zi belgilaydi)."""
    system = (
        "Sen o'zbek tili va tarix fani bo'yicha mutaxassissan. Berilgan matndan test savollarini ajratib ol. "
        "Faqat JSON massiv qaytar, boshqa matn yozma. Har element: "
        '{"grade": "8-sinf", "subject": "O\'zbekiston tarixi" yoki "Jahon tarixi", "topic": "mavzu nomi", '
        '"question": "...", "options": ["A variant", "B variant", "C variant", "D variant"], "answer_index": 0}. '
        "answer_index — to'g'ri variantning 0..3 oralig'idagi indeksi. Aniq to'rtta variantli savollarnigina ol. "
        "Matnni o'zgartirma, faqat ajratib ol. Sinf yoki mavzu matnda bo'lmasa, mazmundan xulosa qil; "
        "bilmasang null qoldir."
    )
    chunks, cur = [], ""
    for line in text.split("\n"):
        if len(cur) + len(line) > 6000 and cur:
            chunks.append(cur)
            cur = ""
        cur += line + "\n"
    if cur.strip():
        chunks.append(cur)

    def run(chunk):
        try:
            return _ask_json(system, f"Fayl: {filename}\n\n{chunk}")
        except Exception:
            return []

    out = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        for res in ex.map(run, chunks):
            for it in res if isinstance(res, list) else []:
                try:
                    opts = [_n(x) for x in it["options"]]
                    idx = int(it["answer_index"])
                    if len(opts) == 4 and 0 <= idx < 4 and len(set(opts)) == 4:
                        out.append({
                            "grade": norm_name(it.get("grade") or "") or None,
                            "subject": norm_name(it.get("subject") or "") or None,
                            "topic": norm_name(it.get("topic") or "") or None,
                            "question": _n(it["question"]), "options": opts, "answer": opts[idx],
                        })
                except (KeyError, TypeError, ValueError):
                    continue
    return out


def ai_assign_topics(items, existing_topics):
    """Mavzusi yo'q savollarga AI mavzu tanlaydi (mavjud mavzularni afzal ko'radi)."""
    system = ("Har bir savol uchun qisqa mavzu nomini tanla. Mavjud mavzulardan mosini ishlat, mos kelmasa yangisini yoz. "
              "Faqat JSON massiv qaytar: har savol uchun bitta satr (savollar tartibida).")
    todo = [i for i in items if not i.get("topic")]
    for start in range(0, len(todo), 40):
        batch = todo[start:start + 40]
        listing = "\n".join(f"{n + 1}. {b['question']}" for n, b in enumerate(batch))
        try:
            res = _ask_json(system, f"Mavjud mavzular: {json.dumps(existing_topics, ensure_ascii=False)}\n\nSavollar:\n{listing}", 3000)
            for b, t in zip(batch, res):
                b["topic"] = norm_name(str(t)) or None
        except Exception:
            pass
