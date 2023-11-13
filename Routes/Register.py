import pyodbc

from flask import jsonify
from Utilities.Queries.insertUser import insertUser

def RegisterModule(username, email, password, conn):
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(f'SELECT COUNT(*) FROM users WHERE username = \'{username}\'')
        count = cursor.fetchone()[0]

        if count > 0:
            return jsonify({'status': False, 'message': 'Username already exists!'})

        if insertUser(username, email, password, conn):
            return jsonify({'status': True, 'message': 'User registered successfully!'}), 200

        return jsonify({'status': False, 'message': 'Failed to register user!'}), 500

    except pyodbc.Error as e:
        print(f'Database Error: {e}')
        return jsonify({'status': False, 'message': 'Failed to register user!'}), 500
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()