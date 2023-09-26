from selenium import webdriver

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