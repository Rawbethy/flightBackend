from bs4 import BeautifulSoup as bs
from html.parser import HTMLParser
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
import time, pickle
import pandas as pd
import os

from chromedriver_autoinstaller import install as install_chromedriver
install_chromedriver()

def createDriver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument("--disable-cache")
    return webdriver.Chrome(options=options)

class WebDriverContext:
    def __enter__(self):
        self.driver = createDriver()
        return self.driver

    def __exit__(self, exc_type, exc_value, traceback):
        if self.driver:
            self.driver.quit()

with open('/home/ec2-user/flightBackend/Utilities/airportDict.pk1', 'rb') as fp:
    portDict = pickle.load(fp)

with open('/home/ec2-user/flightBackend/Utilities/airportDF.pk1', 'rb') as fp:
    airports = pickle.load(fp)

app = Flask(__name__)
cors = CORS(app)

@app.route('/airlineCodes', methods=['GET'])
@cross_origin()
def codeAPI():
    return portDict

@app.route('/airlineAPI', methods=['POST'])
@cross_origin()
def airlineAPI():
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

    try:
        with WebDriverContext() as driver:
            driver.get(url)
            print(url)
            time.sleep(5)
            page = driver.page_source
            soup = bs(page, 'html.parser')
            cards = soup.find_all('div', {'class': 'nrc6-wrapper'})

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
                    'price': None
                }
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
                print(entry['ports'])

            return jsonify(airlinesAndPrices)    
    except Exception as e:
        # Handle exceptions as needed
        print(f"An exception occurred: {str(e)}")
        return jsonify({"error": "An error occurred while processing the request"})                     

if __name__ == '__main__':
    app.run('0.0.0.0', port=8080)
