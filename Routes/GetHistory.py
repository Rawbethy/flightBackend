import pyodbc
from flask import jsonify

def GetHistoryModule(username, conn):
    try:
        entries = {}
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM history WHERE username = ?;', (username, ))
        data = cursor.fetchall()
        for index, entry in enumerate(data):
            currEntry = {
                'urlID': '',
                'url': '',
                'depCity': '',
                'arrCity': '',
                'depDate': '',
                'retDate': ''
            }
            currEntry['urlID'] = entry['url_id']
            currEntry['url'] = entry['url']
            currEntry['depCity'] = entry['dep_city']
            currEntry['arrCity'] = entry['arr_city']
            currEntry['depDate'] = entry['dep_date']
            currEntry['retDate'] = entry['ret_date']
            entries["entry%s"%index] = currEntry
        return jsonify({'entries': data}), 200

    except pyodbc.Error as e:
        print(f'Database error for GetHistory module: \n{e}')

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
