import time, pickle, os, multiprocessing, pyodbc, socket, sys

from datetime import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup as bs
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
from chromedriver_autoinstaller import install as install_chromedriver

from Utilities.drivers import WebDriverContext
from Utilities.getAllFlights import getAllFlightsAndPrices
from Utilities.authGen import tokenRequired

from Routes.Register import RegisterModule
from Routes.Login import LoginModule
from Routes.GetHistory import GetHistoryModule
from Routes.GetPrices import GetPricesModule
from Routes.ScrapeLogic import ScrapeAPI

install_chromedriver()
load_dotenv()
dbServer = os.getenv('dbServer')
dbUser = os.getenv('dbUser')
dbName = os.getenv('dbName')
dbPW = os.getenv('dbPW')

secretKey = os.getenv('SECRET')

connString = f'Driver={{ODBC Driver 18 for SQL Server}};SERVER={dbServer};DATABASE={dbName};UID={dbUser};PWD={dbPW};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'

def createDBConnection():
    return pyodbc.connect(connString)

def getFlightsProcess(url):
    getAllFlightsAndPrices(url)

# with open('/home/ec2-user/flightBackend/Utilities/PickleFiles/airportDict.pk1', 'rb') as fp:
with open('./Utilities/PickleFiles/airportDict.pk1', 'rb') as fp:
    portDict = pickle.load(fp)

# with open('/home/ec2-user/flightBackend/Utilities/PickleFiles/airportDF.pk1', 'rb') as fp:
with open('./Utilities/PickleFiles/airportDF.pk1', 'rb') as fp:
    airports = pickle.load(fp)
    
app = Flask(__name__)
CORS(app)

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
    conn = createDBConnection()

    return RegisterModule(username, email, password, conn)


@app.route('/login', methods=['POST'])
@cross_origin()
def login():
    data = request.get_json()
    username = data['username']
    password = data['password']
    conn = createDBConnection()

    return LoginModule(username, password, secretKey, conn)

@app.route('/getHistory', methods=['POST'])
@cross_origin()
@tokenRequired
def getHistory():
    data = request.get_json()
    username = data.get('username')
    conn = createDBConnection()

    return GetHistoryModule(username, conn)

@app.route('/getPrices', methods=['POST'])
@cross_origin()
@tokenRequired
def getPrices():
    data = request.get_json()
    urlID = data.get('urlID')
    conn = creatDBConnection()

    return GetPricesModule(urlID, conn)

@app.route('/airlineAPI', methods=['POST'])
@cross_origin()
def airlineAPI():    
    data = request.get_json()
    depDate = data.get('depDate')
    depCity = data.get('depCity')
    depPort = data.get('depPort')
    arrPort = data.get('arrPort')
    arrCity = data.get('arrCity')
    retDate = data.get('retDate')
    username = data.get('username') if data.get('username') else None

    try:
        conn = createDBConnection()
        return ScrapeAPI(username, depDate, depCity, depPort, arrPort, arrCity, retDate, conn)

    except Exception as e:
        print(f'Exception has occured: {e}')

if __name__ == '__main__':
    app.run('0.0.0.0', port=8080)
