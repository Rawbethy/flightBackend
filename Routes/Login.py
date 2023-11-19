import pyodbc
from flask import jsonify
from werkzeug.security import check_password_hash

def LoginModule(username, password, conn):
    try:
        cursor = conn.cursor()
        cursor.execute(f'SELECT * FROM users WHERE username = \'{username}\'')
        row = cursor.fetchone()

        if not row:
            return jsonify({'message': 'Login credentials do not match! Please try again :)'})

        if(check_password_hash(row[2], password)):
            return jsonify({'message': 'Logged in successfully!', 'status': True})

        return jsonify({'message': 'User not found!', 'status': False})

    except pyodbc.Error as e:
        return jsonify({'message': f'Error with DB: {e}', 'status': False})
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()