import psycopg2
import os

from dotenv import load_dotenv
from bs4 import BeautifulSoup as bs
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from psycopg2.extras import DictCursor
# from chromedriver_autoinstaller import install as install_chromedriver


# install_chromedriver()
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

def getAllUrls():
    try:
        conn = createDBConnection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute("SELECT DISTINCT link_url FROM history")
        res = cursor.fetchall()
        historyRes = set([x[0] for x in res])

        # for i in res:
        #     print(i[0])

    except psycopg2.Error as e:
        cursor.close()
        conn.close()
        return {'message': f'Error: {e}'}
    
if __name__ == '__main__':
    getAllUrls()