from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException
import time

import sqlite3

options = Options()
driver = webdriver.Chrome(options=options)
driver.get("https://www.hwgeneralins.com/notice/ir/product-ing01.do")
wait = WebDriverWait(driver, 10)
all_data = []


def safe_click(element, retries=3, wait_sec=1):
    for _ in range(retries):
        try:
            driver.execute_script("arguments[0].click();", element)
            time.sleep(wait_sec)
            return True
        except StaleElementReferenceException:
            time.sleep(wait_sec)
    return False


def get_step1_items():
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "fieldset#uiFormField1  dl#step01")))
        container = driver.find_element(By.CSS_SELECTOR, "fieldset#uiFormField1  dl#step01")
        return container.find_elements(
            By.CSS_SELECTOR, 'dd > a')
    except TimeoutException:
        print("step1 항목 없음")
        return []


def get_step2_items():
    try:
        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "fieldset#uiFormField2  ul.list_type1")))
        container = driver.find_element(By.CSS_SELECTOR, "fieldset#uiFormField2  ul.list_type1")
        return container.find_elements(
            By.CSS_SELECTOR, "li > a")
    except TimeoutException:
        print("step2 항목 없음")
        return []


def get_step3_items():
    try:
        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "fieldset#uiFormField3  ul.list_type1")))
        container = driver.find_element(By.CSS_SELECTOR, "fieldset#uiFormField3  ul.list_type1")
        return container.find_elements(
            By.CSS_SELECTOR, "li > a")
    except TimeoutException:
        print("step3 항목 없음")
        return []


def extract_detail_data():
    wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, "div#uiFormField4  dl.info_data1")))
    container = driver.find_element(By.CSS_SELECTOR, "div#uiFormField4  dl.info_data1")

    data_list = []

    dd_elements = container.find_elements(
        By.TAG_NAME, "dd")
    for dd in dd_elements:

        cell = None

        try:

            cell = dd.find_element(By.TAG_NAME, "a")

        except NoSuchElementException:

            print(f"DEBUG: 'dd' 요소 (텍스트: '{dd.text.strip()}') 안에는 'a' 태그가 없습니다.")
            pass

        if cell is None:
            dd_text = dd.get_attribute("textContent").strip()
            data_list.append(dd_text)
            print(f"DEBUG: 'dd' 텍스트만 저장: '{dd_text}'")
        else:
            text = cell.text.strip()
            full_link = cell.get_attribute("href")
            data_list.append((text, full_link))
            print(f"DEBUG: 'a' 태그 텍스트와 링크 저장: ('{text}', '{full_link}')")

    return data_list


# 상태 기반 계층 탐색
step1_items = get_step1_items()
for i in range(len(step1_items)):
    step1_items = get_step1_items()  # 매번 재조회
    if i >= len(step1_items):
        continue
    if not safe_click(step1_items[i]):
        print(f"[1단계 실패] index={i}")
        continue

    step2_items = get_step2_items()
    if not step2_items:
        continue
    for j in range(len(step2_items)):
        step2_items = get_step2_items()
        if j >= len(step2_items):
            continue
        if not safe_click(step2_items[j]):
            print(f"[2단계 실패] index={j}")
            continue

        step3_items = get_step3_items()
        if not step3_items:
            continue
        for k in range(len(step3_items)):
            step3_items = get_step3_items()
            if k >= len(step3_items):
                continue
            if not safe_click(step3_items[k]):
                print(f"[3단계 실패] index={k}")
                continue

            try:
                data = extract_detail_data()
                all_data.append(data)
                print(f"[OK] {data[0]}")
            except Exception as e:
                print(f"[데이터 추출 실패] 3단계 index={k}, 오류: {e}")


driver.quit()
