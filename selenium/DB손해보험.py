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
from selenium.webdriver import ActionChains
import time
# import sqlite3
# from datetime import datetime

# ----- 본문 -------
options = Options()
driver = webdriver.Chrome(options=options)
driver.get("https://www.idbins.com/FWMAIV1534.do")
wait = WebDriverWait(driver, 10)
action = ActionChains(driver)
all_data = []

container = wait.until(
    EC.presence_of_element_located((By.ID, "mCSB_1_container")))
a_tags = container.find_elements(
    By.CSS_SELECTOR, 'ul > li.dp1 a[onclick^="getStep2"]')

for a in a_tags:
    try:
        # 1단계 클릭
        driver.execute_script("arguments[0].click();", a)
        time.sleep(0.3)
        # 2단계 메뉴가 렌더링될 때까지 대기 (step2_list가 등장)
        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "ul#step2_list > li")))

        container2 = driver.find_element(By.ID, "mCSB_2_container")
        a_tag2s = container2.find_elements(
            By.CSS_SELECTOR, "ul#step2_list > li > a")

        for b in a_tag2s:
            try:
                driver.execute_script("arguments[0].click();", b)
                time.sleep(0.3)
                # 3단계 메뉴가 렌더링될 때까지 대기
                wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "ul#step3_list > li")))

                container3 = driver.find_element(By.ID, "mCSB_3_container")
                a_tag3s = container3.find_elements(
                    By.CSS_SELECTOR, "ul#step3_list > li > a")

                for c in a_tag3s:
                    # 클릭 실행
                    driver.execute_script("arguments[0].click();", c)
                    time.sleep(0.3)

                    wait.until(EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "ul.result > li")))
                    container4 = driver.find_element(By.ID, "mCSB_4_container")
                    name = container4.find_element(
                        By.ID, "step4_name").text
                    date = container4.find_element(
                        By.ID, "step4_date").text
                    all_data.append(name)
                    all_data.append(date)
                    link_elements = container4.find_elements(
                        By.CSS_SELECTOR, "ul.btn_list > li")
                    for x in link_elements[:3]:
                        cell = x.find_element(By.TAG_NAME, "a")
                        link = cell.get_attribute("onclick").split(
                            ",")[1].strip().strip('"').strip(")")
                        text = cell.find_element(By.TAG_NAME, "span").text
                        http_link = "https://www.idbins.com/cYakgwanDown.do?FilePath=InsProduct/"
                        full_link = http_link+link
                        value = (text, full_link)
                        all_data.append(value)
            except Exception as e:
                print(f"2단계 클릭 오류: {e}")

    except Exception as e:
        print(f"1단계 클릭 오류: {e}")
