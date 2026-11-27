# -*- coding: utf-8 -*-
"""Flask API + ilova (Telegram Mini App) serveri."""
import hashlib
import hmac
import json
import os
import random
import re
import secrets
import time
from functools import wraps
from urllib.parse import parse_qsl

from flask import Flask, abort, g, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

import config
import db
import importer
from db import conn, grade_key, norm_name

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 300 * 1024 * 1024  # 300 MB gacha (audio/kitob)

AUDIO_EXT = {"mp3", "m4a", "ogg", "oga", "wav", "aac", "opus", "flac"}
BOOK_EXT = {"pdf", "epub", "doc", "docx", "txt", "djvu", "fb2"}
LEVELS = [(0, "Yangi o'quvchi"), (25, "Tarix havaskori"), (100, "Yilnomachi"), (250, "Tarixshunos"), (500, "Alloma")]


# ---------------------------------------------------------------------------
# Autentifikatsiya (Telegram initData tekshiruvi)
# ---------------------------------------------------------------------------
def verify_init_data(init_data: str):
    if not init_data or not config.BOT_TOKEN:
        return None
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    their_hash = pairs.pop("hash", None)
    if not their_hash:
        return None
    check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", config.BOT_TOKEN.encode(), hashlib.sha256).digest()
    mine = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(mine, their_hash):
        return None
    if time.time() - int(pairs.get("auth_date", "0")) > 86400 * 2:
        return None
    return json.loads(pairs.get("user", "{}"))


def require_user(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        tg = None
        if config.DEV_MODE and request.headers.get("X-Dev-User"):
            uid = int(request.headers["X-Dev-User"])
            tg = {"id": uid, "first_name": request.headers.get("X-Dev-Name", f"Dev {uid}"), "username": ""}
        else:
            tg = verify_init_data(request.headers.get("X-Telegram-Init-Data", ""))
        if not tg or "id" not in tg:
            return jsonify(error="Avtorizatsiya xatosi. Ilovani Telegram ichidan oching."), 401
        name = (tg.get("first_name", "") + " " + tg.get("last_name", "")).strip() or "Foydalanuvchi"
        db.save_user(tg["id"], name, username=tg.get("username", "") or "")
        g.uid = tg["id"]
        g.user = db.get_user(tg["id"])
        g.is_admin = bool(g.user["is_admin"])
        return fn(*a, **kw)
    return wrapper


def require_admin(fn):
    @wraps(fn)
    @require_user
    def wrapper(*a, **kw):
        if not g.is_admin:
            return jsonify(error="Bu amal faqat adminlar uchun."), 403
        return fn(*a, **kw)
    return wrapper


# ---------------------------------------------------------------------------
# Yordamchilar
# ---------------------------------------------------------------------------
def local_day(ts: int) -> int:
    return (ts + config.TZ_OFFSET_HOURS * 3600) // 86400


def compute_streak(c, uid: int) -> int:
    rows = c.execute("SELECT DISTINCT ts FROM answer_log WHERE user_id=? ORDER BY ts DESC LIMIT 2000", (uid,)).fetchall()
    days = sorted({local_day(r["ts"]) for r in rows}, reverse=True)
    if not days:
        return 0
    today = local_day(int(time.time()))
    if days[0] < today - 1:
        return 0
    streak, expect = 0, days[0]
    for d in days:
        if d == expect:
            streak += 1
            expect -= 1
        elif d < expect:
            break
    return streak


def mistakes_qids(c, uid: int):
    """Foydalanuvchi oxirgi marta XATO javob bergan (va hali mavjud) savollar."""
    rows = c.execute(
        """SELECT l.qid FROM answer_log l
           JOIN (SELECT qid, MAX(id) mid FROM answer_log WHERE user_id=? GROUP BY qid) m ON m.mid = l.id
           JOIN questions q ON q.id = l.qid
           WHERE l.correct = 0""", (uid,)).fetchall()
    return [r["qid"] for r in rows]


def rating_rows(c, days: int):
    since = int(time.time()) - days * 86400
    return c.execute(
        """SELECT s.user_id, u.full_name, ROUND(SUM(s.points), 1) AS pts, COUNT(*) AS answers
           FROM scores s JOIN users u ON u.telegram_id = s.user_id
           WHERE s.ts >= ? GROUP BY s.user_id ORDER BY pts DESC, MIN(s.ts) ASC""", (since,)).fetchall()


def stats_for(uid: int):
    c = conn()
    tot = c.execute("SELECT COALESCE(SUM(points),0) p, COUNT(*) n FROM scores WHERE user_id=?", (uid,)).fetchone()
    tests = c.execute("SELECT COUNT(*) FROM sessions WHERE user_id=? AND finished=1", (uid,)).fetchone()[0]
    wrong = c.execute("SELECT COUNT(*) FROM answer_log WHERE user_id=? AND correct=0", (uid,)).fetchone()[0]
    correct_n = c.execute("SELECT COUNT(*) FROM answer_log WHERE user_id=? AND correct=1", (uid,)).fetchone()[0]
    streak = compute_streak(c, uid)
    mist = len(mistakes_qids(c, uid))
    week_rank = None
    for i, r in enumerate(rating_rows(c, 7), start=1):
        if r["user_id"] == uid:
            week_rank = i
            break
    c.close()
    pts = round(tot["p"], 1)
    level, nxt = LEVELS[0][1], None
    for i, (need, name) in enumerate(LEVELS):
        if pts >= need:
            level = name
            nxt = LEVELS[i + 1] if i + 1 < len(LEVELS) else None
    return {
        "points": pts, "correct": correct_n, "wrong": wrong, "tests": tests, "streak": streak,
        "mistakes": mist, "week_rank": week_rank, "level": level,
        "next_level": {"name": nxt[1], "need": nxt[0]} if nxt else None,
    }


def user_payload():
    u = g.user
    return {"id": u["telegram_id"], "name": u["full_name"], "is_admin": g.is_admin}


def q_public(r, shuffle=True):
    opts = json.loads(r["options"])
    if shuffle:
        random.shuffle(opts)
    return {"id": r["id"], "question": r["question"], "options": opts}


# ---------------------------------------------------------------------------
# Sahifa va umumiy
# ---------------------------------------------------------------------------
@app.after_request
def no_cache(resp):
    if request.path.startswith("/api/") or request.path == "/":
        resp.headers["Cache-Control"] = "no-store"
    return resp


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/config")
def api_config():
    c = conn()
    has_books = c.execute("SELECT COUNT(*) FROM books").fetchone()[0] > 0
    c.close()
    return jsonify(time=config.TIME_PER_QUESTION, points=config.POINTS_PER_CORRECT,
                   has_books=has_books, ai=importer.ai_enabled())


@app.post("/api/auth")
@require_user
def api_auth():
    return jsonify(user=user_payload(), stats=stats_for(g.uid))


@app.get("/api/me")
@require_user
def api_me():
    return jsonify(user=user_payload(), stats=stats_for(g.uid))


@app.get("/api/tree")
@require_user
def api_tree():
    c = conn()
    rows = c.execute("SELECT grade, subject, topic, COUNT(*) n FROM questions GROUP BY grade, subject, topic ORDER BY MIN(id)").fetchall()
    c.close()
    tree = {}
    for r in rows:
        tree.setdefault(r["grade"], {}).setdefault(r["subject"], []).append({"topic": r["topic"], "count": r["n"]})
    out = []
    for gname in sorted(tree, key=grade_key):
        subs = []
        for sname in sorted(tree[gname]):
            topics = tree[gname][sname]
            subs.append({"subject": sname, "count": sum(t["count"] for t in topics), "topics": topics})
        out.append({"grade": gname, "count": sum(s["count"] for s in subs), "subjects": subs})
    return jsonify(tree=out)


# ---------------------------------------------------------------------------
# Test jarayoni
# ---------------------------------------------------------------------------
@app.post("/api/quiz/start")
@require_user
def quiz_start():
    d = request.get_json(force=True)
    c = conn()
    if d.get("mode") == "mistakes":
        qids = mistakes_qids(c, g.uid)
        random.shuffle(qids)
        qids = qids[:30]
        title = "Xatolar ustida ishlash"
        rows = [c.execute("SELECT * FROM questions WHERE id=?", (i,)).fetchone() for i in qids]
    else:
        grade, subject, topic = d.get("grade"), d.get("subject"), d.get("topic")
        if topic in (None, "*"):
            rows = c.execute("SELECT * FROM questions WHERE grade=? AND subject=?", (grade, subject)).fetchall()
            title = f"{grade}, {subject} — Barcha mavzular"
        else:
            rows = c.execute("SELECT * FROM questions WHERE grade=? AND subject=? AND topic=?", (grade, subject, topic)).fetchall()
            title = f"{grade}, {subject} — {topic}"
        rows = list(rows)
        random.shuffle(rows)
        count = int(d.get("count") or 0)
        if count > 0:
            rows = rows[:count]
    rows = [r for r in rows if r]
    if not rows:
        c.close()
        return jsonify(error="Bu bo'lim uchun hozircha savollar yo'q."), 404
    sid = secrets.token_urlsafe(12)
    c.execute("INSERT INTO sessions (id, user_id, title, qids, started) VALUES (?,?,?,?,?)",
              (sid, g.uid, title, json.dumps([r["id"] for r in rows]), int(time.time())))
    c.commit()
    c.close()
    return jsonify(session_id=sid, title=title, time=config.TIME_PER_QUESTION,
                   questions=[q_public(r) for r in rows])


@app.post("/api/quiz/answer")
@require_user
def quiz_answer():
    d = request.get_json(force=True)
    c = conn()
    s = c.execute("SELECT * FROM sessions WHERE id=? AND user_id=? AND finished=0", (d.get("session_id"), g.uid)).fetchone()
    if not s:
        c.close()
        return jsonify(error="Test sessiyasi topilmadi."), 404
    qid = int(d.get("qid", 0))
    results = json.loads(s["results"])
    if qid not in json.loads(s["qids"]) or any(r["qid"] == qid for r in results):
        c.close()
        return jsonify(error="Bu savolga javob allaqachon berilgan."), 400
    q = c.execute("SELECT * FROM questions WHERE id=?", (qid,)).fetchone()
    if not q:
        c.close()
        return jsonify(error="Savol topilmadi."), 404
    choice = d.get("choice")
    if choice is None:
        status = "skipped"
    else:
        status = "correct" if choice == q["answer"] else "wrong"
    now = int(time.time())
    pts = config.POINTS_PER_CORRECT if status == "correct" else 0
    results.append({"qid": qid, "status": status, "choice": choice})
    c.execute("UPDATE sessions SET results=? WHERE id=?", (json.dumps(results, ensure_ascii=False), s["id"]))
    if status != "skipped":
        c.execute("INSERT INTO answer_log (user_id, qid, correct, ts) VALUES (?,?,?,?)", (g.uid, qid, int(status == "correct"), now))
    if pts:
        c.execute("INSERT INTO scores (user_id, points, ts) VALUES (?,?,?)", (g.uid, pts, now))
    c.commit()
    c.close()
    return jsonify(status=status, answer=q["answer"], points=pts)


@app.post("/api/quiz/finish")
@require_user
def quiz_finish():
    d = request.get_json(force=True)
    c = conn()
    s = c.execute("SELECT * FROM sessions WHERE id=? AND user_id=?", (d.get("session_id"), g.uid)).fetchone()
    if not s:
        c.close()
        return jsonify(error="Test sessiyasi topilmadi."), 404
    results = json.loads(s["results"])
    c.execute("UPDATE sessions SET finished=1 WHERE id=?", (s["id"],))
    c.commit()
    detail = []
    for r in results:
        q = c.execute("SELECT question, answer FROM questions WHERE id=?", (r["qid"],)).fetchone()
        detail.append({"question": q["question"] if q else "(o'chirilgan savol)", "status": r["status"],
                       "choice": r["choice"], "answer": q["answer"] if q else ""})
    c.close()
    cnt = lambda st: sum(1 for r in results if r["status"] == st)
    correct = cnt("correct")
    return jsonify(title=s["title"], correct=correct, wrong=cnt("wrong"), skipped=cnt("skipped"),
                   total=len(results), points=round(correct * config.POINTS_PER_CORRECT, 1),
                   detail=detail, stats=stats_for(g.uid))


# ---------------------------------------------------------------------------
# Reyting
# ---------------------------------------------------------------------------
PERIODS = {"week": 7, "month": 30, "quarter": 90}


@app.get("/api/rating")
@require_user
def api_rating():
    period = request.args.get("period", "week")
    days = PERIODS.get(period, 7)
    c = conn()
    rows = rating_rows(c, days)
    c.close()
    top = [{"rank": i, "id": r["user_id"], "name": r["full_name"], "points": r["pts"], "answers": r["answers"]}
           for i, r in enumerate(rows[:50], start=1)]
    me = next(({"rank": i, "points": r["pts"]} for i, r in enumerate(rows, start=1) if r["user_id"] == g.uid), None)
    return jsonify(period=period, days=days, top=top, me=me, participants=len(rows))


# ---------------------------------------------------------------------------
# Audio va kitoblar
# ---------------------------------------------------------------------------
def _save_upload(file_storage, folder, allowed):
    ext = (file_storage.filename.rsplit(".", 1)[-1] if "." in file_storage.filename else "").lower()
    if ext not in allowed:
        raise ValueError("Fayl turi qo'llab-quvvatlanmaydi. Ruxsat: " + ", ".join(sorted(allowed)))
    name = f"{secrets.token_hex(6)}_{secure_filename(file_storage.filename) or 'file.' + ext}"
    path = folder / name
    file_storage.save(path)
    return name, path.stat().st_size


@app.get("/api/audios")
@require_user
def api_audios():
    c = conn()
    rows = c.execute("SELECT * FROM audios ORDER BY id DESC").fetchall()
    c.close()
    return jsonify(audios=[{"id": r["id"], "title": r["title"], "grade": r["grade"], "topic": r["topic"],
                            "size": r["size"], "url": f"/media/audio/{r['filename']}"} for r in rows])


@app.get("/media/audio/<path:fn>")
def media_audio(fn):
    return send_from_directory(config.AUDIO_DIR, fn, conditional=True)


@app.get("/media/books/<path:fn>")
def media_books(fn):
    return send_from_directory(config.BOOKS_DIR, fn, conditional=True, as_attachment=False)


@app.post("/api/admin/audio")
@require_admin
def admin_audio_add():
    f = request.files.get("file")
    if not f:
        return jsonify(error="Audio fayl tanlanmadi."), 400
    try:
        name, size = _save_upload(f, config.AUDIO_DIR, AUDIO_EXT)
    except ValueError as e:
        return jsonify(error=str(e)), 400
    title = (request.form.get("title") or f.filename.rsplit(".", 1)[0]).strip()
    c = conn()
    c.execute("INSERT INTO audios (title, grade, topic, filename, size, created_at) VALUES (?,?,?,?,?,?)",
              (title, norm_name(request.form.get("grade", "")), norm_name(request.form.get("topic", "")), name, size, int(time.time())))
    c.commit()
    c.close()
    return jsonify(ok=True)


@app.delete("/api/admin/audio/<int:aid>")
@require_admin
def admin_audio_del(aid):
    c = conn()
    r = c.execute("SELECT filename FROM audios WHERE id=?", (aid,)).fetchone()
    if r:
        (config.AUDIO_DIR / r["filename"]).unlink(missing_ok=True)
        c.execute("DELETE FROM audios WHERE id=?", (aid,))
        c.commit()
    c.close()
    return jsonify(ok=True)


@app.get("/api/books")
@require_user
def api_books():
    c = conn()
    rows = c.execute("SELECT * FROM books ORDER BY id DESC").fetchall()
    c.close()
    return jsonify(books=[{"id": r["id"], "title": r["title"], "author": r["author"], "description": r["description"],
                           "size": r["size"], "ext": r["filename"].rsplit(".", 1)[-1].lower(),
                           "url": f"/media/books/{r['filename']}"} for r in rows])


@app.post("/api/admin/book")
@require_admin
def admin_book_add():
    f = request.files.get("file")
    title = (request.form.get("title") or "").strip()
    if not f or not title:
        return jsonify(error="Kitob nomi va faylini kiriting."), 400
    try:
        name, size = _save_upload(f, config.BOOKS_DIR, BOOK_EXT)
    except ValueError as e:
        return jsonify(error=str(e)), 400
    c = conn()
    c.execute("INSERT INTO books (title, author, description, filename, size, created_at) VALUES (?,?,?,?,?,?)",
              (title, (request.form.get("author") or "").strip(), (request.form.get("description") or "").strip(), name, size, int(time.time())))
    c.commit()
    c.close()
    return jsonify(ok=True)


@app.delete("/api/admin/book/<int:bid>")
@require_admin
def admin_book_del(bid):
    c = conn()
    r = c.execute("SELECT filename FROM books WHERE id=?", (bid,)).fetchone()
    if r:
        (config.BOOKS_DIR / r["filename"]).unlink(missing_ok=True)
        c.execute("DELETE FROM books WHERE id=?", (bid,))
        c.commit()
    c.close()
    return jsonify(ok=True)


# ---------------------------------------------------------------------------
# Admin: savollar
# ---------------------------------------------------------------------------
def _validate_question(d):
    question = (d.get("question") or "").strip()
    options = [(o or "").strip() for o in (d.get("options") or [])]
    try:
        idx = int(d.get("correct_index"))
    except (TypeError, ValueError):
        idx = -1
    if not question or len(options) != 4 or not all(options) or len(set(options)) != 4:
        raise ValueError("Savol va 4 ta turli variantni to'liq kiriting.")
    if not 0 <= idx < 4:
        raise ValueError("To'g'ri javobni belgilang.")
    return question, options, options[idx]


@app.get("/api/admin/questions")
@require_admin
def admin_questions():
    c = conn()
    rows = c.execute("SELECT * FROM questions WHERE grade=? AND subject=? AND topic=? ORDER BY id",
                     (request.args.get("grade"), request.args.get("subject"), request.args.get("topic"))).fetchall()
    c.close()
    return jsonify(questions=[{"id": r["id"], "question": r["question"], "options": json.loads(r["options"]), "answer": r["answer"]} for r in rows])


@app.get("/api/admin/question/<int:qid>")
@require_admin
def admin_question_get(qid):
    c = conn()
    r = c.execute("SELECT * FROM questions WHERE id=?", (qid,)).fetchone()
    c.close()
    if not r:
        return jsonify(error="Savol topilmadi."), 404
    return jsonify(id=r["id"], question=r["question"], options=json.loads(r["options"]), answer=r["answer"],
                   grade=r["grade"], subject=r["subject"], topic=r["topic"])


@app.post("/api/admin/question")
@require_admin
def admin_question_add():
    d = request.get_json(force=True)
    try:
        question, options, answer = _validate_question(d)
    except ValueError as e:
        return jsonify(error=str(e)), 400
    grade, subject, topic = (norm_name(d.get(k, "")) for k in ("grade", "subject", "topic"))
    if not (grade and subject and topic):
        return jsonify(error="Sinf, fan va mavzuni kiriting."), 400
    c = conn()
    c.execute("INSERT INTO questions (grade, subject, topic, question, options, answer, created_at) VALUES (?,?,?,?,?,?,?)",
              (grade, subject, topic, question, json.dumps(options, ensure_ascii=False), answer, int(time.time())))
    c.commit()
    c.close()
    return jsonify(ok=True)


@app.put("/api/admin/question/<int:qid>")
@require_admin
def admin_question_edit(qid):
    d = request.get_json(force=True)
    try:
        question, options, answer = _validate_question(d)
    except ValueError as e:
        return jsonify(error=str(e)), 400
    c = conn()
    c.execute("UPDATE questions SET question=?, options=?, answer=? WHERE id=?",
              (question, json.dumps(options, ensure_ascii=False), answer, qid))
    c.commit()
    c.close()
    return jsonify(ok=True, question=question, options=options, answer=answer)


@app.delete("/api/admin/question/<int:qid>")
@require_admin
def admin_question_del(qid):
    c = conn()
    c.execute("DELETE FROM questions WHERE id=?", (qid,))
    c.commit()
    c.close()
    return jsonify(ok=True)


@app.post("/api/admin/delete-grade")
@require_admin
def admin_delete_grade():
    d = request.get_json(force=True)
    c = conn()
    n = c.execute("DELETE FROM questions WHERE grade=?", (d.get("grade"),)).rowcount
    c.commit()
    c.close()
    return jsonify(ok=True, deleted=n)


@app.post("/api/admin/delete-topic")
@require_admin
def admin_delete_topic():
    d = request.get_json(force=True)
    c = conn()
    n = c.execute("DELETE FROM questions WHERE grade=? AND subject=? AND topic=?",
                  (d.get("grade"), d.get("subject"), d.get("topic"))).rowcount
    c.commit()
    c.close()
    return jsonify(ok=True, deleted=n)


# ---------------------------------------------------------------------------
# Admin: fayldan AI yordamida savollarni qo'shish (oldindan ko'rish -> tasdiqlash)
# ---------------------------------------------------------------------------
@app.post("/api/admin/import/preview")
@require_admin
def import_preview():
    f = request.files.get("file")
    if not f:
        return jsonify(error="Fayl tanlanmadi."), 400
    try:
        text = importer.extract_text(f.filename, f.read())
    except Exception as e:
        return jsonify(error=f"Faylni o'qib bo'lmadi: {e}"), 400
    if len(text.strip()) < 20:
        return jsonify(error="Faylda matn topilmadi."), 400

    used_ai = False
    items, skipped = importer.parse_local(text)
    grade, subject = importer.detect_meta(f.filename, text)
    if not items and importer.ai_enabled():
        items, used_ai = importer.ai_extract(text, f.filename), True
    elif items and importer.ai_enabled() and (not grade or not subject) and not all(i["grade"] and i["subject"] for i in items):
        ag, asub = importer.ai_classify(f.filename, text)
        grade, subject = grade or ag, subject or asub
        used_ai = True
    if not items:
        msg = "Savollar topilmadi. Format: savol, A) B) C) D) variantlar va 'Javob: B' qatori."
        if not importer.ai_enabled():
            msg += " (AI yoqilmagan — GEMINI_API_KEY kiritilsa, nostandart fayllar ham o'qiladi.)"
        return jsonify(error=msg), 422

    for it in items:
        it["grade"] = it["grade"] or grade
        it["subject"] = it["subject"] or subject
    if importer.ai_enabled() and any(not i.get("topic") for i in items):
        c = conn()
        existing = [r[0] for r in c.execute("SELECT DISTINCT topic FROM questions").fetchall()]
        c.close()
        importer.ai_assign_topics(items, existing)
        used_ai = True
    for it in items:
        it["topic"] = it.get("topic") or "Umumiy"

    token = secrets.token_hex(8)
    (config.IMPORT_DIR / f"{token}.json").write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    groups = {}
    for it in items:
        k = (it["grade"] or "—", it["subject"] or "—", it["topic"])
        groups[k] = groups.get(k, 0) + 1
    grades = {i["grade"] for i in items}
    subjects = {i["subject"] for i in items}
    return jsonify(
        token=token, filename=f.filename, total=len(items), skipped=skipped, used_ai=used_ai,
        grade=next(iter(grades)) if len(grades) == 1 else None,
        subject=next(iter(subjects)) if len(subjects) == 1 else None,
        mixed=len(grades) > 1 or len(subjects) > 1,
        groups=[{"grade": k[0], "subject": k[1], "topic": k[2], "count": n} for k, n in groups.items()],
    )


@app.post("/api/admin/import/commit")
@require_admin
def import_commit():
    d = request.get_json(force=True)
    token = re.sub(r"[^0-9a-f]", "", d.get("token", ""))
    path = config.IMPORT_DIR / f"{token}.json"
    if not token or not path.exists():
        return jsonify(error="Yuklangan fayl muddati o'tgan. Qaytadan yuklang."), 404
    items = json.loads(path.read_text(encoding="utf-8"))
    og, osub = norm_name(d.get("grade", "")), norm_name(d.get("subject", ""))
    for it in items:
        if og:
            it["grade"] = og
        if osub:
            it["subject"] = osub
    if any(not (i["grade"] and i["subject"]) for i in items):
        return jsonify(error="Sinf va fanni kiriting."), 400

    c = conn()
    removed = 0
    if d.get("replace"):
        for gr, su in {(i["grade"], i["subject"]) for i in items}:
            removed += c.execute("DELETE FROM questions WHERE grade=? AND subject=?", (gr, su)).rowcount
    existing = {(r["grade"], r["subject"], r["question"].lower()) for r in c.execute("SELECT grade, subject, question FROM questions")}
    now, added, dup = int(time.time()), 0, 0
    for it in items:
        key = (it["grade"], it["subject"], it["question"].lower())
        if key in existing:
            dup += 1
            continue
        existing.add(key)
        c.execute("INSERT INTO questions (grade, subject, topic, question, options, answer, created_at) VALUES (?,?,?,?,?,?,?)",
                  (it["grade"], it["subject"], it["topic"], it["question"], json.dumps(it["options"], ensure_ascii=False), it["answer"], now))
        added += 1
    c.commit()
    c.close()
    path.unlink(missing_ok=True)
    return jsonify(ok=True, added=added, duplicates=dup, removed=removed)


db.init()
