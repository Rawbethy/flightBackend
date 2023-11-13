def GetHistoryModule(username, conn):
    try:
        entries = {}
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute('SELECT * FROM history WHERE username = %s;', (username, ))
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

    except pyodbc.Error as e:
        print('ERROR: %s', (e,))

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return jsonify({'entries': data}), 200
