import time, pickle, psycopg2, os, multiprocessing

from Utilities.drivers import WebDriverContext
from Utilities.getAllFlights import getAllFlightsAndPrices
from datetime import datetime
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from bs4 import BeautifulSoup as bs
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
from psycopg2.extras import DictCursor

load_dotenv()
dbEndpoint = os.getenv('dbEndpoint')
dbUser = os.getenv('dbUser')
dbName = os.getenv('dbName')
dbPW = os.getenv('dbPW')

def createDBConnection():
    return psycopg2.connect(
        host = dbEndpoint,
        user = dbUser,
        password = dbPW,
        database = dbName
    )

def insertUser(username, email, password):
    try:
        conn = createDBConnection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s);",
            (username, email, generate_password_hash(password))
        )
        conn.commit()
        return True

    except psycopg2.Error as e:
        print(f'Database Error: {e}')
        return False
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def getFlightsProcess(url):
    getAllFlightsAndPrices(url)

def cleanSponsorString(dataID):
    if '-sponsored' in dataID:
        return dataID.replace('-sponsored', '').strip()
    else:
        return dataID


# with open('/home/ec2-user/flightBackend/Utilities/airportDict.pk1', 'rb') as fp:
with open('./Utilities/airportDict.pk1', 'rb') as fp:
    portDict = pickle.load(fp)

# with open('/home/ec2-user/flightBackend/Utilities/airportDF.pk1', 'rb') as fp:
with open('./Utilities/airportDF.pk1', 'rb') as fp:
    airports = pickle.load(fp)

app = Flask(__name__)
cors = CORS(app)

@app.route('/')
@cross_origin()
def root():
    return ''

@app.route('/airlineCodes', methods=['GET'])
@cross_origin()
def codeAPI():
    return portDict

@app.route('/register', methods=['POST'])
@cross_origin()
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    try:
        conn = createDBConnection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute(f'SELECT COUNT(*) FROM users WHERE username = \'{username}\'')
        count = cursor.fetchone()[0]

        if count > 0:
            return jsonify({'status': False, 'message': 'Username already exists!'})

        if insertUser(username, email, password):
            return jsonify({'status': True, 'message': 'User registered successfully!'}), 200

        return jsonify({'status': False, 'message': 'Failed to register user!'}), 500

    except psycopg2.Error as e:
        print(f'Database Error: {e}')
        return jsonify({'status': False, 'message': 'Failed to register user!'}), 500
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/login', methods=['POST'])
@cross_origin()
def login():
    data = request.get_json()
    username = data['username']
    password = data['password']
    try:
        conn = createDBConnection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute(f'SELECT * FROM users WHERE username = \'{username}\'')
        row = cursor.fetchone()

        if not row:
            return jsonify({'message': 'Login credentials do not match! Please try again :)'})

        if(check_password_hash(row['password_hash'], password)):
            return jsonify({'message': 'Logged in successfully!', 'status': True})

        return jsonify({'message': 'User not found!', 'status': False})

    except psycopg2.Error as e:
        return jsonify({'message': f'Error with DB: {e}', 'status': False})
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/getHistory', methods=['POST'])
@cross_origin()
def getHistory():
    def getData(username):
        try:
            entries = {}
            conn = createDBConnection()
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
            return entries

        except psycopg2.Error as e:
            print('ERROR: %s', (e,))

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    data = request.get_json()
    username = data.get('username')
    data = getData(username)

    return jsonify({'entries': data}), 200

@app.route('/getPrices', methods=['POST'])
@cross_origin()
def getPrices():
    def getData(urlID):
        try:
            conn = createDBConnection()
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


        except psycopg2.Error as e:
            print(e)

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        
    def scrapePrices(entries, url):
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

    data = request.get_json()
    urlID = data.get('urlID')
    res, url = getData(urlID)
    newPrices = scrapePrices(res, url)
    return jsonify({'pricesAndInfo': newPrices, 'dbData': res}), 200   

@app.route('/airlineAPI', methods=['POST'])
@cross_origin()
def airlineAPI():
    def addLinkData(username, dataIDs, url):
        try:
            conn = createDBConnection()
            cursor = conn.cursor(cursor_factory=DictCursor)
            if username:
                for data_id, price in dataIDs.items():
                    id = cleanSponsorString(data_id)
                    cursor.execute('SELECT COUNT(*) FROM flightprices WHERE data_id = %s;', (id,))
                    if cursor.fetchone()[0] == 0:
                        cursor.execute(
                            'INSERT INTO flightprices (data_id, price, url) VALUES (%s, %s, %s);',
                            (id, int(price), url)
                        )
            conn.commit()
        except psycopg2.Error as e:
            print('ERROR: %s', (e)) 
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def addLinkToUser(username, depDate, retDate, depCity, arrCity, url):
        try:
            conn = createDBConnection()
            cursor = conn.cursor(cursor_factory=DictCursor)
            cursor.execute(f'SELECT * FROM history WHERE username = \'{username}\' AND url = \'{url}\';')
            if not cursor.fetchone():
                cursor.execute('INSERT INTO history (url, username, timestamp, dep_city, arr_city, dep_date, ret_date) VALUES(%s, %s, %s, %s, %s, %s, %s);', (url, username, datetime.today().date().strftime('%Y-%m-%d'), depCity, arrCity, depDate, retDate))
                conn.commit()
                print('Link inserted successfully!')
                return
            print('User already has link present in DB')
            return

        except psycopg2.Error as e:
            print('ERROR: %s', (e,))
            return

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        
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
        
    # This program will use web scraping techniques to extract data from Kayak.com to search for optimal price matching 
    # between multiple airline companies and compare the prices

    data = request.get_json()
    depDate = data.get('depDate')
    depCity = data.get('depCity')
    depPort = data.get('depPort')
    arrPort = data.get('arrPort')
    arrCity = data.get('arrCity')
    retDate = data.get('retDate')

    url = createURL(depPort, arrPort, depDate, retDate, 1)

    try:
        currData = {}
        with WebDriverContext() as driver:
            driver.get(url)
            print(f"From main: {url}")
            xpath_expression = '//*[@id="hiddenAlertContainer"]'
            loadedPage = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, xpath_expression)))
            page = driver.page_source
            soup = bs(page, 'html.parser')
            cards = soup.find_all('div', {'class': 'nrc6'})

            if len(cards) == 0:
                return jsonify({'message': 'No data for chosen dates!'})
            
            else:
                username = data.get('username') if data.get('username') else None
                if username:
                    addLinkToUser(username, depDate, retDate, depCity, arrCity, url)

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
                
                addLinkData(username, currData, url)
                return jsonify(airlinesAndPrices)
                
    except Exception as e:
        print("An exception occurred: %s" % e)
        return jsonify({"error": "An error occurred while processing the request"})

    finally:
        process = multiprocessing.Process(target=getFlightsProcess, args=(url,))
        process.start()


if __name__ == '__main__':
    app.run('0.0.0.0', port=8080)
