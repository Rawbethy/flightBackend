import pyodbc

def cleanSponsorString(dataID):
    if '-sponsored' in dataID:
        return dataID.replace('-sponsored', '').strip()
    else:
        return dataID

def addLinkData(username, currData, url, conn):
    try:
        cursor = conn.cursor()
        for data_id, price in currData.items():
            id = cleanSponsorString(data_id)
            cursor.execute('SELECT COUNT(*) FROM flightPrices WHERE dataID = ?;', (id))
            if cursor.fetchone()[0] == 0:
                cursor.execute('INSERT INTO flightPrices (dataID, price, url) VALUES (?, ?, ?);', (id, int(price), url))

        conn.commit()

    except pyodbc.Error as e:
        print(f'Error with adding card data to user profile: \n{e}')

    finally:
        if cursor:
            cursor.close()