"""Reset a user's password (there is no email reset): python reset_password.py USERNAME NEWPASSWORD"""
import sqlite3, sys
from werkzeug.security import generate_password_hash
from app import DB_PATH
if len(sys.argv) != 3 or not 8 <= len(sys.argv[2]) <= 72:
    sys.exit("Usage: python reset_password.py USERNAME NEWPASSWORD (8-72 characters)")
with sqlite3.connect(DB_PATH) as c:
    n = c.execute("UPDATE users SET pw=? WHERE username=?", (generate_password_hash(sys.argv[2]), sys.argv[1])).rowcount
print("Password updated." if n else "No such user.")
