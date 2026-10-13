"""AstroBlox: Blox Fruits trading site. Flask + SQLite, username/password login."""
import json, os, re, secrets, sqlite3, time
from flask import Flask, g, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("ASTROBLOX_DB", os.path.join(BASE, "astroblox.db"))
KEY_PATH = os.path.join(BASE, "secret.key")

CATALOG = {
    "rarities": {
        "Common": ["Rocket", "Spin", "Chop", "Spring", "Bomb", "Smoke", "Spike"],
        "Uncommon": ["Flame", "Falcon", "Ice", "Sand", "Dark", "Diamond"],
        "Rare": ["Light", "Rubber", "Barrier", "Ghost", "Magma"],
        "Legendary": ["Quake", "Buddha", "Love", "Creation", "Spider", "Sound", "Phoenix",
                      "Portal", "Rumble", "Pain", "Blizzard"],
        "Mythical": ["Gravity", "Mammoth", "T-Rex", "Dough", "Shadow", "Venom", "Control", "Spirit",
                     "Gas", "Leopard", "Yeti", "Kitsune", "Dragon (East)", "Dragon (West)", "Magnet"],
    },
    "gamepasses": ["2x Money", "2x Mastery", "2x Boss Drops", "Fast Boats", "Fruit Notifier",
                   "Dark Blade", "Extra Fruit Storage"],
}
FRUITS = [f for v in CATALOG["rarities"].values() for f in v]
ALLOWED = set(FRUITS) | {f + " Perm" for f in FRUITS} | set(CATALOG["gamepasses"])


def get_secret():
    if os.environ.get("ASTROBLOX_SECRET"):
        return os.environ["ASTROBLOX_SECRET"]
    if not os.path.exists(KEY_PATH):
        with open(KEY_PATH, "w") as f:
            f.write(secrets.token_hex(32))
    with open(KEY_PATH) as f:
        return f.read().strip()


app = Flask(__name__, static_folder="static", static_url_path="")
app.secret_key = get_secret()
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("ASTROBLOX_HTTPS") == "1",
    PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 30,
    MAX_CONTENT_LENGTH=20_000,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE COLLATE NOCASE NOT NULL,
  roblox TEXT NOT NULL, pw TEXT NOT NULL, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS trades(id INTEGER PRIMARY KEY, owner INTEGER NOT NULL REFERENCES users(id),
  offer TEXT NOT NULL, want TEXT NOT NULL, note TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'open',
  req INTEGER REFERENCES users(id), created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, scope TEXT NOT NULL,
  sender INTEGER NOT NULL REFERENCES users(id), text TEXT NOT NULL, created REAL NOT NULL);
CREATE INDEX IF NOT EXISTS m_scope ON messages(scope, id);
"""
with sqlite3.connect(DB_PATH) as _c:
    _c.executescript(SCHEMA)


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d:
        d.close()


@app.after_request
def headers(r):
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["X-Frame-Options"] = "DENY"
    r.headers["Referrer-Policy"] = "same-origin"
    r.headers["Content-Security-Policy"] = ("default-src 'self'; style-src 'self' 'unsafe-inline'; "
                                            "frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
    if request.path.startswith("/api/"):
        r.headers["Cache-Control"] = "no-store"
    return r


def err(msg, code=400):
    return jsonify(error=msg), code


def me():
    uid = session.get("uid")
    if not uid:
        return None
    return db().execute("SELECT id, username, roblox FROM users WHERE id=?", (uid,)).fetchone()


def user_json(u):
    return {"id": u["id"], "username": u["username"], "roblox": u["roblox"]}


_attempts, _last_msg = {}, {}
DUMMY = generate_password_hash("not-a-real-password")
NAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")


def client_ip():
    # Behind a Cloudflare Tunnel every request comes from 127.0.0.1, so read the real IP header.
    if os.environ.get("ASTROBLOX_BEHIND_CLOUDFLARE") == "1":
        return request.headers.get("CF-Connecting-IP") or request.remote_addr
    return request.remote_addr


def too_many(ip):
    now = time.time()
    n, start = _attempts.get(ip, (0, now))
    if now - start > 600:
        n, start = 0, now
    _attempts[ip] = (n + 1, start)
    return n + 1 > 15


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/api/me")
def api_me():
    u = me()
    return jsonify(user=user_json(u) if u else None, catalog=CATALOG)


@app.post("/api/register")
def register():
    if too_many(client_ip()):
        return err("Too many attempts. Try again later.", 429)
    d = request.get_json(silent=True) or {}
    name, pw = str(d.get("username", "")).strip(), str(d.get("password", ""))
    rb = str(d.get("roblox", "")).strip() or name
    if not NAME_RE.match(name):
        return err("Username must be 3-20 letters, numbers or underscores.")
    if not NAME_RE.match(rb):
        return err("Roblox username must be 3-20 letters, numbers or underscores.")
    if not 8 <= len(pw) <= 72:
        return err("Password must be 8-72 characters.")
    try:
        cur = db().execute("INSERT INTO users(username, roblox, pw, created) VALUES(?,?,?,?)",
                           (name, rb, generate_password_hash(pw), time.time()))
        db().commit()
    except sqlite3.IntegrityError:
        return err("That username is taken.", 409)
    session.clear()
    session.permanent = True
    session["uid"] = cur.lastrowid
    return jsonify(user=user_json(me()))


@app.post("/api/login")
def login():
    if too_many(client_ip()):
        return err("Too many attempts. Try again later.", 429)
    d = request.get_json(silent=True) or {}
    u = db().execute("SELECT * FROM users WHERE username=?", (str(d.get("username", "")).strip(),)).fetchone()
    ok = check_password_hash(u["pw"] if u else DUMMY, str(d.get("password", "")))
    if not (u and ok):
        return err("Wrong username or password.", 401)
    session.clear()
    session.permanent = True
    session["uid"] = u["id"]
    return jsonify(user=user_json(u))


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


SEL = ("SELECT t.*, o.username oname, o.roblox orb, q.username rname, q.roblox rrb FROM trades t "
       "JOIN users o ON o.id=t.owner LEFT JOIN users q ON q.id=t.req ")


def trade_json(r):
    return {"id": r["id"], "offer": json.loads(r["offer"]), "want": json.loads(r["want"]), "note": r["note"],
            "status": r["status"], "created": r["created"], "owner": r["owner"], "ownerName": r["oname"],
            "ownerRb": r["orb"], "req": r["req"], "reqName": r["rname"], "reqRb": r["rrb"]}


@app.get("/api/trades")
def trades():
    u = me()
    if not u:
        return err("Please log in.", 401)
    market = db().execute(SEL + "WHERE t.status='open' ORDER BY t.id DESC LIMIT 200").fetchall()
    mine = db().execute(SEL + "WHERE t.owner=? OR t.req=? ORDER BY t.id DESC LIMIT 100", (u["id"], u["id"])).fetchall()
    return jsonify(market=[trade_json(r) for r in market], mine=[trade_json(r) for r in mine])


@app.post("/api/trades")
def post_trade():
    u = me()
    if not u:
        return err("Please log in.", 401)
    d = request.get_json(silent=True) or {}
    offer, want = d.get("offer"), d.get("want")
    for lst in (offer, want):
        if not (isinstance(lst, list) and 1 <= len(lst) <= 3 and all(isinstance(x, str) and x in ALLOWED for x in lst)):
            return err("Pick 1 to 3 items on each side.")
        if len(set(lst)) != len(lst):
            return err("Duplicate items.")
    if set(offer) & set(want):
        return err("The same item is on both sides.")
    if db().execute("SELECT COUNT(*) FROM trades WHERE owner=? AND status='open'", (u["id"],)).fetchone()[0] >= 10:
        return err("You can have at most 10 open trades.")
    db().execute("INSERT INTO trades(owner, offer, want, note, created) VALUES(?,?,?,?,?)",
                 (u["id"], json.dumps(offer), json.dumps(want), str(d.get("note", ""))[:80], time.time()))
    db().commit()
    return jsonify(ok=True)


@app.post("/api/trades/<int:tid>/<action>")
def trade_action(tid, action):
    u = me()
    if not u:
        return err("Please log in.", 401)
    uid = u["id"]
    q = {
        "request": ("UPDATE trades SET status='requested', req=? WHERE id=? AND status='open' AND owner!=?", (uid, tid, uid)),
        "accept": ("UPDATE trades SET status='agreed' WHERE id=? AND status='requested' AND owner=?", (tid, uid)),
        "decline": ("UPDATE trades SET status='open', req=NULL WHERE id=? AND status='requested' AND owner=?", (tid, uid)),
        "withdraw": ("UPDATE trades SET status='open', req=NULL WHERE id=? AND status='requested' AND req=?", (tid, uid)),
        "done": ("UPDATE trades SET status='done' WHERE id=? AND status='agreed' AND (owner=? OR req=?)", (tid, uid, uid)),
        "cancel": ("DELETE FROM trades WHERE id=? AND status='open' AND owner=?", (tid, uid)),
    }.get(action)
    if not q:
        return err("Unknown action.", 404)
    n = db().execute(*q).rowcount
    db().commit()
    return jsonify(ok=True) if n else err("That is no longer possible.", 409)


def can_scope(uid, scope):
    if scope == "global":
        return True
    m = re.fullmatch(r"trade:(\d+)", scope)
    if m:
        t = db().execute("SELECT owner, req FROM trades WHERE id=?", (int(m[1]),)).fetchone()
        return bool(t and uid in (t["owner"], t["req"]))
    m = re.fullmatch(r"dm:(\d+)_(\d+)", scope)
    if m:
        a, b = int(m[1]), int(m[2])
        if a < b and uid in (a, b):
            return db().execute("SELECT COUNT(*) FROM users WHERE id IN (?,?)", (a, b)).fetchone()[0] == 2
    return False


@app.get("/api/messages")
def get_messages():
    u = me()
    if not u:
        return err("Please log in.", 401)
    scope = request.args.get("scope", "")
    if not can_scope(u["id"], scope):
        return err("Not allowed.", 403)
    after = request.args.get("after", "0")
    after = int(after) if after.isdigit() else 0
    sql = ("SELECT m.id, m.sender, m.text, u.username FROM messages m JOIN users u ON u.id=m.sender "
           "WHERE m.scope=? AND m.id>? ")
    if after:
        rows = db().execute(sql + "ORDER BY m.id LIMIT 200", (scope, after)).fetchall()
    else:
        rows = list(reversed(db().execute(sql + "ORDER BY m.id DESC LIMIT 100", (scope, after)).fetchall()))
    return jsonify(messages=[{"id": r["id"], "name": r["username"], "text": r["text"], "mine": r["sender"] == u["id"]} for r in rows])


@app.post("/api/messages")
def post_message():
    u = me()
    if not u:
        return err("Please log in.", 401)
    d = request.get_json(silent=True) or {}
    scope, text = str(d.get("scope", "")), str(d.get("text", "")).strip()[:300]
    if not text:
        return err("Empty message.")
    if not can_scope(u["id"], scope):
        return err("Not allowed.", 403)
    now = time.time()
    if now - _last_msg.get(u["id"], 0) < 0.7:
        return err("Slow down a little.", 429)
    _last_msg[u["id"]] = now
    db().execute("INSERT INTO messages(scope, sender, text, created) VALUES(?,?,?,?)", (scope, u["id"], text, now))
    db().commit()
    return jsonify(ok=True)


@app.get("/api/dms")
def dms():
    u = me()
    if not u:
        return err("Please log in.", 401)
    uid = u["id"]
    rows = db().execute(
        "SELECT scope, MAX(id) mid FROM messages WHERE scope GLOB ? OR scope GLOB ? GROUP BY scope ORDER BY mid DESC LIMIT 50",
        (f"dm:{uid}_*", f"dm:*_{uid}")).fetchall()
    out = []
    for r in rows:
        a, b = map(int, r["scope"][3:].split("_"))
        oid = b if a == uid else a
        o = db().execute("SELECT username FROM users WHERE id=?", (oid,)).fetchone()
        last = db().execute("SELECT text FROM messages WHERE id=?", (r["mid"],)).fetchone()
        out.append({"scope": r["scope"], "name": o["username"] if o else "?", "last": last["text"][:40]})
    return jsonify(dms=out)


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "5000")))
