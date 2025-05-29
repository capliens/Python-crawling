from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException, TimeoutException
import time
import sqlite3
from datetime import datetime

# 링크,판매 중단,sql 수정


def safe_click(driver, element, retries=3, wait_sec=1):
    for _ in range(retries):
        try:
            driver.execute_script("arguments[0].click();", element)
            time.sleep(wait_sec)
            return True
        except StaleElementReferenceException:
            time.sleep(wait_sec)
    return False


def get_division_items(driver, wait):
    try:
        wait.until(EC.presence_of_element_located(
            (By.XPATH, "//dt[contains(text(), '1. 구분선택')]/following-sibling::dd//ul[@class='select1']//a")))
        return driver.find_elements(
            By.XPATH, "//dt[contains(text(), '1. 구분선택')]/following-sibling::dd//ul[@class='select1']//a")
    except TimeoutException:
        print("구분선택 항목 없음")
        return []


def get_product_name_items(driver, wait):
    try:
        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "div#publicPrtDiv ul#productList li a")))
        return driver.find_elements(
            By.CSS_SELECTOR, "div#publicPrtDiv ul#productList li a")
    except TimeoutException:
        print("판매상품명 항목 없음")
        return []


def extract_detail_data(driver, wait, product_name):
    detail_info = {
        "보험명": product_name,
        "판매기간": "정보 없음",
        "상품코드": "정보 없음",
        "약관": "PDF 링크 제외됨",
        "사업방법서": "PDF 링크 제외됨",
        "상품요약서": "PDF 링크 제외됨"
    }
    try:
        wait.until(EC.visibility_of_element_located(
            (By.ID, "productVoTr")))

        product_detail_row = driver.find_element(
            By.CSS_SELECTOR, "#productVoTr tr")

        try:
            sale_period_element = product_detail_row.find_element(
                By.CSS_SELECTOR, "td:nth-child(1)")
            detail_info["판매기간"] = sale_period_element.text.strip()
        except NoSuchElementException:
            pass

        try:
            product_code_element = product_detail_row.find_element(
                By.CSS_SELECTOR, "td:nth-child(2)")
            detail_info["상품코드"] = product_code_element.text.strip()
        except NoSuchElementException:
            pass

    except TimeoutException as e:
        print(f"상세 정보 테이블 로드 실패: {e}")
    except Exception as e:
        print(f"상세 정보 추출 중 오류 발생: {e}")
    return detail_info


def get_heungkuklife_product_info():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 10)
    all_data = []

    url = "https://www.heungkuklife.co.kr/front/public/saleProduct.do?searchFlgSale=Y"
    driver.get(url)
    time.sleep(5)  # 페이지 로딩 대기

    try:
        # 1단계: 구분선택 순회
        division_items = get_division_items(driver, wait)
        for i in range(len(division_items)):
            division_items = get_division_items(driver, wait)  # 재조회
            if i >= len(division_items):
                continue
            if not safe_click(driver, division_items[i]):
                print(f"[1단계 실패] 구분선택 index={i}")
                continue
            division_name = division_items[i].text.strip()
            print(f"구분선택: {division_name} 클릭 성공")

            # 2단계: 보험유형선택은 "전체" 항목만 클릭되어 있도록 유지 (순회하지 않음)
            print("보험유형: 전체 항목 유지")

            # 3단계: 판매상품명 선택 순회
            product_name_items = get_product_name_items(driver, wait)
            if not product_name_items:
                print("판매상품명 항목 없음 (1단계 클릭 후)")
                continue
            for k in range(len(product_name_items)):
                product_name_items = get_product_name_items(
                    driver, wait)  # 재조회
                if k >= len(product_name_items):
                    continue

                product_element = product_name_items[k]
                product_name = product_element.text.strip()
                print(f"상품명: {product_name} 클릭 시도")

                if not safe_click(driver, product_element):
                    print(f"[3단계 실패] 상품명 index={k}")
                    continue

                # 4단계: 상세 데이터 추출
                try:
                    data = extract_detail_data(driver, wait, product_name)
                    all_data.append(data)
                    print(f"[OK] {data['보험명']}")
                except Exception as e:
                    print(f"[데이터 추출 실패] 상품명: {product_name}, 오류: {e}")

                # 이전 페이지로 돌아가지 않음 (사용자 요청)
                # driver.back()
                # WebDriverWait를 사용하여 상품 목록이 다시 로드될 때까지 기다리는 로직도 제거
                # try:
                #     WebDriverWait(driver, 10).until(
                #         EC.presence_of_element_located(
                #             (By.CSS_SELECTOR, "div#publicPrtDiv ul#productList li a"))
                #     )
                # except TimeoutException as e:
                #     print(f"이전 페이지로 돌아온 후 상품 목록 로드 실패: {e}")
                #     break  # 현재 구분선택에 대한 상품명 루프 종료

    except Exception as e:
        print(f"전체 스크래핑 중 오류 발생: {e}")

    finally:
        driver.quit()

    # ───── 4. 구조화 ─────
    structured_rows = []
    scraped_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for row in all_data:
        structured_rows.append([
            "흥국생명",          # company_name
            row["보험명"],      # product_name
            row["상품코드"],     # product_code
            row["약관"],        # document_type (여기서는 "PDF 링크 제외됨" 값)
            row["판매기간"],     # sales_period
            scraped_time,
            row["사업방법서"],   # link (여기서는 "PDF 링크 제외됨" 값)
            row["상품요약서"]    # link (여기서는 "PDF 링크 제외됨" 값)
        ])

    # ───── 5. DB 저장 ─────
    with sqlite3.connect("흥국생명_web_data.db") as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS insurance_docs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT,
                product_name TEXT,
                product_code TEXT,
                document_type TEXT,
                sales_period TEXT,
                scraped_at TIMESTAMP,
                link_yakgwan TEXT,
                link_saeop TEXT,
                link_yoyak TEXT,
                UNIQUE(company_name, product_name, product_code,
                       document_type, sales_period, link_yakgwan,
                       link_saeop, link_yoyak)
            );
        """)

        final_rows_to_insert = []
        for row_data in structured_rows:
            final_rows_to_insert.append((
                row_data[0], row_data[1], row_data[2],
                "약관", row_data[4], row_data[5], row_data[3], "", ""
            ))
            final_rows_to_insert.append((
                row_data[0], row_data[1], row_data[2],
                "사업방법서", row_data[4], row_data[5], "", row_data[6], ""
            ))
            final_rows_to_insert.append((
                row_data[0], row_data[1], row_data[2],
                "상품요약서", row_data[4], row_data[5], "", "", row_data[7]
            ))

        cursor.executemany("""
            INSERT OR IGNORE INTO insurance_docs (
                company_name, product_name, product_code,
                document_type, sales_period, scraped_at,
                link_yakgwan, link_saeop, link_yoyak
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, final_rows_to_insert)

        conn.commit()

    print(f"{len(final_rows_to_insert)}건 저장 완료")
    return all_data


if __name__ == "__main__":
    data = get_heungkuklife_product_info()
    # for item in data:
    #     print(item)
