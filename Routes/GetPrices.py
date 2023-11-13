def GetPricesModule(urlID, conn):

    def GetData(urlID):
        try:
            cursor = conn.cursor(cursor_factory=DictCursor)
            cursor.execute('SELECT url FROM history WHERE url_id = %s;', (urlID, ))
            url = cursor.fetchone()[0]
            cursor.execute('SELECT * FROM flightprices WHERE url = %s;', (url, ))
            res = cursor.fetchall()
            entries = {}
            for index, entry in enumerate(res):
                currEntry = {
                    'price': ''
                }
                currEntry['price'] = entry['price']
                entries[entry['data_id']] = currEntry

            return entries, url


        except pyodbc.Error as e:
            print(e)

    def ScrapePrices():
        try:    
            with WebDriverContext() as driver:
                driver.get(url)
                loadedPage = WebDriverWait(driver, 30).until(EC.text_to_be_present_in_element((By.ID, 'hiddenAlertContainer'), 'Results ready.'))
                page = driver.page_source
                soup = bs(page, 'html.parser')
                cards = soup.find_all('div', {'class': 'nrc6'})
                newPrices = {}

                for index, container in enumerate(cards):
                    times = []
                    entry = {
                        'price': None,
                        'depTimes': [],
                        'depFlightLen': None,
                        'depLayovers': None,
                        'retTimes': [],
                        'retFlightLen': None,
                        'retLayovers': None
                    }
                    dataID = cleanSponsorString(container['data-resultid'])
                    timesContainer = container.find_all('div', {'class': 'vmXl vmXl-mod-variant-large'})
                    layoverContainer = container.find_all('div', {'class': 'JWEO'})
                    lengthContainer = container.find_all('div', {'class': 'xdW8'})

                    for i, c in enumerate(timesContainer):
                        spans = c.find_all('span')
                        for span in spans:
                            times.append(span.text)

                    for i, c in enumerate(layoverContainer):
                        stops = c.find('div', {'class': 'vmXl vmXl-mod-variant-default'}).find('span').text
                        if i == 0:
                            entry['depLayovers'] = stops
                        else:
                            entry['retLayovers'] = stops
                    
                    for i, c in enumerate(lengthContainer):
                        currLen = c.find('div', {'class': 'vmXl vmXl-mod-variant-default'}).text
                        if i == 0:
                            entry['depFlightLen'] = currLen
                        else:
                            entry['retFlightLen'] = currLen
                    
                    if times[2][-2] == '+':
                        times[2] = times[2][:-2]
                    if times[5][-2] == '+':
                        times[5] = times[2][:-2]

                    entry['depTimes'] = [times[0], times[2]]
                    entry['retTimes'] = [times[3], times[5]]
                    entry['price'] = container.find('div', {'class': 'f8F1-price-text'}).text
                    newPrices[dataID] = entry
        
                return newPrices

        except Exception as e:
            print("An exception occurred: %s" % e)

    try:
        res, url = GetData(urlID)
        newPrices = ScrapePrices(res, url)

        return jsonify({'pricesAndInfo': newPrices, 'dbData': res}), 200

    except Exception as e:
        print(f'An exception has occured: {e}')

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
