# https://www.meritzfire.com/disclosure/product-announcement/product-list.do#!/
# div.prod_category > div.jspPane > ul > li
# div.prod_detail > div.jspPane > ul > li
# div.tbl_data01 > table > tbody >tr>td

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
# from datetime import datetime
import time
# import sqlite3

options = Options()
driver = webdriver.Chrome(options=options)
options.add_argument("--ignore-certificate-errors")
options.add_argument("--allow-running-insecure-content")
driver.get(
    "https://www.meritzfire.com/disclosure/product-announcement/product-list.do#!/")
wait = WebDriverWait(driver, 10)
action = ActionChains(driver)

all_data = []
container = wait.until(
    EC.presence_of_element_located((By.CLASS_NAME, "prod_category")))
click_list_1 = container.find_elements(
    By.CSS_SELECTOR, 'div.jspPane > ul > li > a')

for a in click_list_1:
    try:
        driver.execute_script("arguments[0].click();", a)
        time.sleep(0.2)

        # wait.until(EC.presence_of_element_located(
        #     (By.CSS_SELECTOR, "div.prod_detail > div.jspPane > ul > li")))

        container2 = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "prod_detail")))
        click_list_2 = container2.find_elements(
            By.CSS_SELECTOR, 'div.jspPane > ul > li > a')
        for b in click_list_2:
            driver.execute_script("arguments[0].click();", b)
            time.sleep(0.2)

            # wait.until(EC.presence_of_element_located(
            #     (By.CSS_SELECTOR, "div.tbl_data01 > talbe > tbody > tr > td")))

            container3 = driver.find_element(
                By.CSS_SELECTOR, ".tbl_data01.ng-scope")

            list_elements = container3.find_elements(
                By.CSS_SELECTOR, "table > tbody > tr > td")

            for c in list_elements:
                print(c)
                print(c)

    except Exception as e:
        print(f"1단계 클릭 오류: {e}")
