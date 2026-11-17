import sqlite3, datetime, os
from . import config

os.makedirs(os.path.dirname(config.DB_PATH) or ".", exist_ok=True)

def _conn():
    return sqlite3.connect(config.DB_PATH)

def init():
    with _conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT, session_id TEXT, role TEXT, content TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT, session_id TEXT, user_message TEXT, redacted_message TEXT,
            emotion TEXT, intent TEXT, confidence REAL, route TEXT,
            escalated INTEGER, response TEXT,
            prompt_tokens INTEGER DEFAULT 0, completion_tokens INTEGER DEFAULT 0,
            cost_usd REAL DEFAULT 0,
            feedback_rating TEXT, feedback_comment TEXT)""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_session ON messages(session_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_interactions_ts ON interactions(ts)")

# ---- history ----
def add_message(session_id, role, content):
    with _conn() as c:
        c.execute("INSERT INTO messages (ts,session_id,role,content) VALUES (?,?,?,?)",
                  (datetime.datetime.utcnow().isoformat(), session_id, role, content))

def get_history(session_id, limit=10):
    with _conn() as c:
        rows = c.execute(
            "SELECT role, content FROM messages WHERE session_id=? "
            "ORDER BY id DESC LIMIT ?", (session_id, limit)).fetchall()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

def clear_session(session_id):
    with _conn() as c:
        c.execute("DELETE FROM messages WHERE session_id=?", (session_id,))

# ---- interactions ----
def log_interaction(session_id, raw_msg, redacted_msg, analysis: dict, route: str,
                    response: str, prompt_tokens=0, completion_tokens=0, cost_usd=0.0) -> int:
    with _conn() as c:
        cur = c.execute("""INSERT INTO interactions
            (ts,session_id,user_message,redacted_message,emotion,intent,confidence,route,
             escalated,response,prompt_tokens,completion_tokens,cost_usd)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (datetime.datetime.utcnow().isoformat(), session_id, raw_msg, redacted_msg,
             analysis["emotion"], analysis["intent"], analysis["confidence"], route,
             int(route == "escalate"), response,
             prompt_tokens, completion_tokens, cost_usd))
        return cur.lastrowid

def add_feedback(interaction_id: int, rating: str, comment: str | None):
    with _conn() as c:
        c.execute("UPDATE interactions SET feedback_rating=?, feedback_comment=? WHERE id=?",
                  (rating, comment, interaction_id))

# ---- analytics ----
def analytics():
    with _conn() as c:
        by_emotion = c.execute(
            "SELECT emotion, COUNT(*), AVG(confidence), SUM(escalated) "
            "FROM interactions GROUP BY emotion").fetchall()
        by_intent = c.execute(
            "SELECT intent, COUNT(*) FROM interactions GROUP BY intent").fetchall()
        by_route = c.execute(
            "SELECT route, COUNT(*) FROM interactions GROUP BY route").fetchall()
        totals = c.execute(
            "SELECT COUNT(*), COALESCE(SUM(escalated),0), "
            "COALESCE(AVG(cost_usd),0), COALESCE(SUM(cost_usd),0) "
            "FROM interactions").fetchone()
        feedback = c.execute(
            "SELECT feedback_rating, COUNT(*) FROM interactions "
            "WHERE feedback_rating IS NOT NULL GROUP BY feedback_rating").fetchall()
        recent_feedback = c.execute(
            "SELECT emotion, route, feedback_rating, feedback_comment FROM interactions "
            "WHERE feedback_rating='down' ORDER BY id DESC LIMIT 5").fetchall()
    return {
        "by_emotion": [{"emotion":r[0],"count":r[1],"avg_confidence":r[2] or 0,
                        "escalated":r[3] or 0} for r in by_emotion],
        "by_intent": [{"intent":r[0],"count":r[1]} for r in by_intent],
        "by_route":  [{"route":r[0],"count":r[1]} for r in by_route],
        "total": totals[0],
        "escalation_rate": (totals[1]/totals[0]) if totals[0] else 0,
        "avg_cost_per_message": totals[2] or 0,
        "total_cost_usd": totals[3] or 0,
        "feedback": {r[0]: r[1] for r in feedback},
        "recent_negative_feedback": [
            {"emotion":r[0],"route":r[1],"rating":r[2],"comment":r[3]}
            for r in recent_feedback
        ],
    }