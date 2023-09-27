from selenium import webdriver
from fake_useragent import UserAgent
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service


def createDriver():
    ua = UserAgent()
    userAgent = ua.random
    service = Service(executable_path=ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument(f'--user-agent={userAgent}')
    options.add_argument("--disable-cache")
    driver = webdriver.Chrome(service=service, options=options)
    return driver

class WebDriverContext:
    def __enter__(self):
        self.driver = createDriver()
        return self.driver

    def __exit__(self, exc_type, exc_value, traceback):
        if self.driver:
            self.driver.quit()