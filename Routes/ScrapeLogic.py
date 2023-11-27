import pyodbc

from datetime import datetime
from flask import jsonify
from Utilities.drivers import WebDriverContext
from bs4 import BeautifulSoup as bs
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from Utilities.Queries.addLinkData import addLinkData

def addLinkToUser(username, depDate, retDate, depCity, arrCity, url, conn):
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM history WHERE username = ? AND url = ?;', (username, url))
        if not cursor.fetchone():
            cursor.execute('INSERT INTO history (url, username, timestamp, depCity, arrCity, depDate, retDate) VALUES(?, ?, ?, ?, ?, ?, ?);', (url, username, datetime.today().date().strftime('%Y-%m-%d'), depCity, arrCity, depDate, retDate))
            print('Link inserted successfully!')
            return
        print('User already has link present in DB')
        return

    except pyodbc.Error as e:
        print(f'Error inserting link to user profile:\n{e}')
        return

def createURL(depPort, arrPort, depDate, retDate, numAd):
    string = 'https://www.kayak.com/flights/'

    if isinstance(depPort, list):
        for index, port in enumerate(depPort):
            string += f'{depPort[index]}'
            if index < len(depPort) - 1:
                string += ','
    else:
        string += f'{depPort}'

    string += '-'

    if isinstance(arrPort, list):
        for index, port in enumerate(arrPort):
            string += f'{arrPort[index]}'
            if index < len(arrPort) - 1:
                string += ','
    else:
        string += f'{arrPort}'

    string += f'/{depDate}/{retDate}/{numAd}adults?sort=bestflight_a'
    return string

def ScrapeAPI(username, depDate, depCity, depPort, arrPort, arrCity, retDate, conn):
    url = createURL(depPort, arrPort, depDate, retDate, 1)

    try:
        currData = {}
        with WebDriverContext() as driver:
            driver.get(url)
            loadedPage = WebDriverWait(driver, 40).until(EC.text_to_be_present_in_element((By.ID, 'hiddenAlertContainer'), 'Results ready.'))
            page = driver.page_source
            soup = bs(page, 'html.parser')
            cards = soup.find_all('div', {'class': 'nrc6'})

            if len(cards) == 0:
                return jsonify({'message': 'No data for chosen dates!'})
            
            else:
                if username:
                    addLinkToUser(username, depDate, retDate, depCity, arrCity, url, conn)

                airlinesAndPrices = dict()

                for i, c in enumerate(cards):
                    times = []
                    entry = {  # Create a new dictionary for each entry
                        'ports': {
                            'depTO': [],
                            'depL': [],
                            'retTO': [],
                            'retL': []
                        },
                        'depAirline': None,
                        'depTimes': [],
                        'depFlightLen': None,
                        'retAirline': None,
                        'retFlightLen': None,
                        'retTimes': [],
                        'layoversTo': {
                            'layoverCount': None,
                            'layoverPorts': [],
                            'layoverLengths': []
                        },
                        'layoversFrom': {
                            'layoverCount': None,
                            'layoverPorts': [],
                            'layoverLengths': []
                        },
                        'link': None,
                        'resultID': None,
                        'price': None
                    }
                    entry['resultID'] = c['data-resultid']
                    airlinesInfo = c.find_all('div', {'class': 'c_cgF c_cgF-mod-variant-default'})
                    timesContainer = c.find_all('div', {'class': 'vmXl vmXl-mod-variant-large'})
                    portsContainer = c.find_all('div', {'class': 'EFvI'})
                    layoverContainer = c.find_all('div', {'class': 'JWEO'})
                    lengthContainer = c.find_all('div', {'class': 'xdW8'})
                    link = c.find('div', {'class': 'dOAU-main-btn-wrap'}).find('a', {'role': 'link'})

                    if link:
                        entry['link'] = "kayak.com" + link.get('href')
                    else:
                        entry['link'] = "No link found"

                    for index, container in enumerate(lengthContainer):
                        currLen = container.find('div', {'class': 'vmXl vmXl-mod-variant-default'})
                        if index == 0:
                            entry['depFlightLen'] = currLen.text
                        else:
                            entry['retFlightLen'] = currLen.text

                    for index1, container in enumerate(portsContainer):
                        if container.find('div', {'class': 'c_cgF c_cgF-mod-variant-default c_cgF-badge-content'}):
                            regDiv = container.find('div', {'class': 'c_cgF c_cgF-mod-variant-default'})
                            highlightDiv = container.find('div', {'class': 'c_cgF c_cgF-mod-variant-default c_cgF-badge-content'})
                            regDivPortInfo = [regDiv.find('span', {'class': 'EFvI-ap-info'}).find('span').text, regDiv['title']]
                            highDivPortInfo = [highlightDiv.find('span', {'class': 'EFvI-ap-info'}).find('span').text, highlightDiv['title']]
                            if highDivPortInfo[0] in depPort:
                                if index1 == 0:
                                    entry['ports']['depTO'] += highDivPortInfo
                                    entry['ports']['depL'] += regDivPortInfo
                                else:
                                    entry['ports']['retTO'] += regDivPortInfo
                                    entry['ports']['retL'] += highDivPortInfo                    
                            else:
                                if index1 == 0:
                                    entry['ports']['depTO'] += regDivPortInfo
                                    entry['ports']['depL'] += highDivPortInfo
                                else:
                                    entry['ports']['retTO'] += highDivPortInfo
                                    entry['ports']['retL'] += regDivPortInfo 
                        else:
                            divs = container.find_all('div', {'class': 'c_cgF c_cgF-mod-variant-default'})
                            for index2, div in enumerate(divs):
                                currPortName = div['title']
                                portAbbrev = div.find('span', {'class': 'EFvI-ap-info'}).find('span').text
                                if index1 == 0:
                                    if index2 == 0:
                                        entry['ports']['depTO'] += [portAbbrev, currPortName]
                                    else:
                                        entry['ports']['depL'] += [portAbbrev, currPortName]
                                else:
                                    if index2 == 0:
                                        entry['ports']['retTO'] += [portAbbrev, currPortName]
                                    else:
                                        entry['ports']['retL'] += [portAbbrev, currPortName]

                    for container in timesContainer:
                        spans = container.find_all('span')
                        for span in spans:
                            times.append(span.text)

                    for index, container in enumerate(layoverContainer):
                        portsList = set()
                        lengthList = []
                        stops = container.find('div', {'class': 'vmXl vmXl-mod-variant-default'}).find('span')
                        portsContainer = container.find('div', {'class': 'c_cgF c_cgF-mod-variant-default'})
                        portSpans = portsContainer.find_all('span')
                        for spans in portSpans:
                            for span in spans.find_all('span'):
                                if span.text not in portsList:
                                    lengthList.append(span['title'])
                                    portsList.add(span.text)

                        if index == 0:
                            entry['layoversTo']['layoverCount'] = stops.text
                            for i1, span in enumerate(portsList):
                                splitLength = str(lengthList[i1]).split(' ')
                                fullLength = splitLength[0] + ' ' + splitLength[1]
                                entry['layoversTo']['layoverLengths'].append(fullLength)
                                entry['layoversTo']['layoverPorts'].append(span)
                        else:
                            entry['layoversFrom']['layoverCount'] = stops.text
                            for i1, span in enumerate(portsList):
                                splitLength = str(lengthList[i1]).split(' ')
                                fullLength = splitLength[0] + ' ' + splitLength[1]
                                entry['layoversFrom']['layoverLengths'].append(fullLength)
                                entry['layoversFrom']['layoverPorts'].append(span)
                
                    price = c.find('div', {'class': 'f8F1-price-text'}).text
                    if times[2][-2] == '+':
                        times[2] = times[2][:-2]
                    if times[5][-2] == '+':
                        times[5] = times[2][:-2]

                    entry['depAirline'] = airlinesInfo[0].text
                    entry['depTimes'] = [times[0], times[2]]
                    entry['retAirline'] = airlinesInfo[5].text
                    entry['retTimes'] = [times[3], times[5]]
                    entry['price'] = price
                    airlinesAndPrices[f'Entry{i}'] = entry
                    currData[entry['resultID']] = int(entry['price'][1:].replace(',', ''))

                if username:
                    addLinkData(username, currData, url, conn)
                
                return airlinesAndPrices
                
    except Exception as e:
        print("An exception occurred: %s" % e)
        return jsonify({"error": "An error occurred while processing the request"})

    finally:
        if conn:
            conn.close()