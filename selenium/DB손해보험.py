# 버튼 구조 div id=mCSB_4_container >ul
# pdf 링크가 스타일온클릭과 같음
# div id= mCSB_1_container -> ul -> li class=dp1 -> ul ->li -> a 클릭
# div id=mCSB_2_container -> ul id=step2_list ->li -> a
# https://www.idbins.com/FWMAIV1534.do

from selenium import webdriver
from selenium.webdriver.common.by import By
# from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# import sqlite3
# from datetime import datetime

# -----가져오기----


class EpostScraper:
    def __init__(self, driver):
        self.driver = driver

    def get_all_data(self):
        data_list = []
        data_list = self._extract(data_list)
        return data_list

    def _extract(self, data_list):
        container4 = wait.until(
            EC.presence_of_element_located((By.ID, "mCSB_4_container")))
        sale_name = container4.find_element(By.CLASS_NAME, "step4_name")
        sale_date = container4.find_element(By.CLASS_NAME, "step4_date")

        li_list = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "#mCSB_4_container ul.btn_list")))
        li_elements = li_list.find_elements(By.TAG_NAME, "li")

        for link in li_elements:
            try:
                a_tag = link.find_element(By.TAG_NAME, "a")
                span_tag = a_tag.find_element(By.TAG_NAME, "span")

                href = a_tag.get_attribute("href")
                text = span_tag.text.strip()

                print(sale_date, sale_name, href, text)
            except Exception:
                print("요소 처리 중 오류 발생")

        return data_list


# ----- 본문 -------
options = Options()
driver = webdriver.Chrome(options=options)
driver.get("https://www.idbins.com/FWMAIV1534.do")
wait = WebDriverWait(driver, 10)
all_data = []

container = wait.until(
    EC.presence_of_element_located((By.ID, "mCSB_1_container")))
a_tags = container.find_elements(
    By.CSS_SELECTOR, "ul > li.dp1 > ul > li > a")

for a in a_tags:
    try:
        # 1단계 클릭
        wait.until(EC.element_to_be_clickable(a)).click()

        # 2단계 메뉴가 렌더링될 때까지 대기 (step2_list가 등장)
        wait.until(EC.presence_of_element_located((By.ID, "step2_list")))

        container2 = driver.find_element(By.ID, "mCSB_2_container")
        a_tag2s = container2.find_elements(
            By.CSS_SELECTOR, "ul#step2_list > li > a")

        for b in a_tag2s:
            try:
                wait.until(EC.element_to_be_clickable(b)).click()

                # 3단계 메뉴가 렌더링될 때까지 대기
                wait.until(EC.presence_of_element_located(
                    (By.ID, "step3_list")))

                container3 = driver.find_element(By.ID, "mCSB_3_container")
                a_tag3s = container3.find_elements(
                    By.CSS_SELECTOR, "ul#step3_list > li > a")
                scroll_value = 0
                for c in a_tag3s:
                    try:
                        wait.until(EC.element_to_be_clickable(c)).click()
                        # 데이터 추출
                        # scraper2 = EpostScraper(driver)
                        # all_data.extend(scraper2.get_all_data())
                        # print("끝내18")
                    except Exception as e:
                        print(f"3단계 클릭 오류: {e}")
                driver.execute_script("window.scrollTo(0, -100);")
            except Exception as e:
                print(f"2단계 클릭 오류: {e}")

    except Exception as e:
        print(f"1단계 클릭 오류: {e}")
