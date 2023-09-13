import time, pickle
import psycopg2
import os

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
from chromedriver_autoinstaller import install as install_chromedriver

install_chromedriver()
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


def createDriver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument("--disable-cache")
    driver = webdriver.Chrome(options=options)
    return driver

class WebDriverContext:
    def __enter__(self):
        self.driver = createDriver()
        return self.driver

    def __exit__(self, exc_type, exc_value, traceback):
        if self.driver:
            self.driver.quit()

with open('/home/ec2-user/flightBackend/Utilities/airportDict.pk1', 'rb') as fp:
# with open('./Utilities/airportDict.pk1', 'rb') as fp:
    portDict = pickle.load(fp)

with open('/home/ec2-user/flightBackend/Utilities/airportDF.pk1', 'rb') as fp:
# with open('./Utilities/airportDF.pk1', 'rb') as fp:
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
    def getURLS(username):
        try:
            conn = createDBConnection()
            cursor = conn.cursor(cursor_factory=DictCursor)
            cursor.execute('SELECT link_url FROM history WHERE user_username = %s;', (username, ))
            links = cursor.fetchall()
            linkList = [link[0] for link in links]
            return linkList

        except psycopg2.Error as e:
            print('ERROR: %s', (e,))

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    data = request.get_json()
    username = data.get('username')
    urls = getURLS(username)
    # for url in urls:
    #     print(f'URL: {url[0]}\n')
    return jsonify({'urls': urls}), 200
        

@app.route('/airlineAPI', methods=['POST'])
@cross_origin()
def airlineAPI():
    def addLinkData(username, dataIDs, url):
        try:
            conn = createDBConnection()
            cursor = conn.cursor(cursor_factory=DictCursor)
            if username:
                for data_id, price in dataIDs.items():
                    cursor.execute('SELECT COUNT(*) FROM flightprices WHERE data_id = %s;', (data_id,))
                    if cursor.fetchone()[0] == 0:
                        cursor.execute(
                            'INSERT INTO flightprices (data_id, price, url) VALUES (%s, %s, %s);',
                            (data_id, int(price), url)
                        )
            conn.commit()
        except psycopg2.Error as e:
            print('ERROR: %s', (e)) 
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def addLinkToUser(username, url):
        try:
            conn = createDBConnection()
            cursor = conn.cursor(cursor_factory=DictCursor)
            cursor.execute(f'SELECT * FROM history WHERE user_username = \'{username}\' AND link_url = \'{url}\';')
            if not cursor.fetchone():
                cursor.execute(f'INSERT INTO history (link_url, user_username, timestamp) VALUES(\'{url}\', \'{username}\', CURRENT_TIMESTAMP)')
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
    depPort = data.get('depPort')
    retDate = data.get('retDate')
    arrPort = data.get('arrPort')

    url = createURL(depPort, arrPort, depDate, retDate, 1)
    username = data.get('username') if data.get('username') else None
    if username:
        addLinkToUser(username, url)

    try:
        currData = {}
        with WebDriverContext() as driver:
            driver.get(url)
            print(url)
            loadedPage = WebDriverWait(driver, 30).until(EC.text_to_be_present_in_element((By.ID, 'hiddenAlertContainer'), 'Results ready.'))
            page = driver.page_source
            soup = bs(page, 'html.parser')
            cards = soup.find_all('div', {'class': 'nrc6'})

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
        # Handle exceptions as needed
        print(f"An exception occurred: {str(e)}")
        return jsonify({"error": "An error occurred while processing the request"})                     

if __name__ == '__main__':
    app.run('0.0.0.0', port=8080)
