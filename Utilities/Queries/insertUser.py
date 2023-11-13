import pyodbc
from werkzeug.security import generate_password_hash, check_password_hash

def insertUser(username, email, password, conn):
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, email, pwHash) VALUES (?, ?, ?);",
            (username, email, generate_password_hash(password))
        )
        conn.commit()
        return True

    except pyodbc.Error as e:
        print(f'Error in insertUser: {e}')
        return False