import pyodbc

def cleanSponsorString(dataID):
    if '-sponsored' in dataID:
        return dataID.replace('-sponsored', '').strip()
    else:
        return dataID

def addLinkData(username, currData, url, conn):
    try:
        cursor = conn.cursor()
        if username:
            for data_id, price in currData.items():
                id = cleanSponsorString(data_id)
                cursor.execute('SELECT COUNT(*) FROM flightprices WHERE data_id = %s;', (id,))
                if cursor.fetchone()[0] == 0:
                    cursor.execute(
                        'INSERT INTO flightprices (data_id, price, url) VALUES (%s, %s, %s);',
                        (id, int(price), url)
                    )
        conn.commit()

    except pyodbc.Error as e:
        print('ERROR: %s', (e))

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()