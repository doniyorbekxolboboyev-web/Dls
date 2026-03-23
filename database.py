import sqlite3
import os
from datetime import datetime

DB_PATH = "game_bot.db"

class Database:
    def __init__(self):
        self.init_db()

    def get_conn(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        conn = self.get_conn()
        cur = conn.cursor()

        # Foydalanuvchilar jadvali
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT DEFAULT '',
                full_name TEXT DEFAULT '',
                logo_file_id TEXT DEFAULT NULL,
                invited_by INTEGER DEFAULT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Kutish ro'yxati
        cur.execute("""
            CREATE TABLE IF NOT EXISTS waiting (
                user_id INTEGER PRIMARY KEY,
                joined_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # O'yinlar jadvali
        cur.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player1_id INTEGER,
                player2_id INTEGER,
                match_code TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    # ===== FOYDALANUVCHI =====

    def add_user(self, user_id, username, full_name, ref_code=None):
        conn = self.get_conn()
        cur = conn.cursor()

        cur.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        exists = cur.fetchone()

        if not exists:
            invited_by = None
            if ref_code:
                try:
                    invited_by = int(ref_code)
                except:
                    pass

            cur.execute(
                "INSERT INTO users (user_id, username, full_name, invited_by) VALUES (?, ?, ?, ?)",
                (user_id, username, full_name, invited_by)
            )
        else:
            cur.execute(
                "UPDATE users SET username=?, full_name=? WHERE user_id=?",
                (username, full_name, user_id)
            )

        conn.commit()
        conn.close()

    def get_user(self, user_id):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def set_user_logo(self, user_id, file_id):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE users SET logo_file_id=? WHERE user_id=?", (file_id, user_id))
        conn.commit()
        conn.close()

    def get_user_logo(self, user_id):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT logo_file_id FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        conn.close()
        return row['logo_file_id'] if row else None

    def get_invited_count(self, user_id):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as cnt FROM users WHERE invited_by=?", (user_id,))
        row = cur.fetchone()
        conn.close()
        return row['cnt'] if row else 0

    # ===== KUTISH =====

    def add_to_waiting(self, user_id):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO waiting (user_id, joined_at) VALUES (?, ?)",
            (user_id, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

    def remove_from_waiting(self, user_id):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM waiting WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()

    def get_waiting_player(self):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM waiting ORDER BY joined_at ASC LIMIT 1")
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def is_waiting(self, user_id):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM waiting WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        conn.close()
        return row is not None

    # ===== O'YINLAR =====

    def create_match(self, player1_id, player2_id, match_code):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO matches (player1_id, player2_id, match_code) VALUES (?, ?, ?)",
            (player1_id, player2_id, match_code)
        )
        conn.commit()
        conn.close()

    def get_total_games(self, user_id):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) as cnt FROM matches WHERE player1_id=? OR player2_id=?",
            (user_id, user_id)
        )
        row = cur.fetchone()
        conn.close()
        return row['cnt'] if row else 0

    def get_user_matches(self, user_id):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM matches WHERE player1_id=? OR player2_id=? ORDER BY created_at DESC LIMIT 10",
            (user_id, user_id)
        )
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_top_players(self, limit=10):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT u.user_id, u.username, u.full_name,
                   COUNT(m.id) as total_games
            FROM users u
            LEFT JOIN matches m ON m.player1_id = u.user_id OR m.player2_id = u.user_id
            GROUP BY u.user_id
            ORDER BY total_games DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]


# Global instance
db = Database()
