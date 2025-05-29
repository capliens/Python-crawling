from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import time

# db 등록


def scrape_axa_insurance_products():
    # Chrome 드라이버 설정
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # 브라우저를 띄우지 않고 실행
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    url = ("https://www.axa.co.kr/AsianPlatformInternet/html/axacms/common/"
           "intro/disclosure/insurance/index.html")
    driver.get(url)
    wait = WebDriverWait(driver, 10)

    extracted_data = []
    try:
        # "현재판매상품" 탭 클릭
        current_products_tab = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "div.tab.tap_price > ul > li > a.m2.bg")
            )
        )
        current_products_tab.click()
        time.sleep(2)  # 페이지 로드를 기다림

        table_container = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[contains(@class, 'tb_board') and "
                           "contains(@class, 'drop_tb') and "
                           "contains(@class, 'cmsTabWrap2')]"))
        )

        # 테이블의 모든 tr 요소를 찾습니다.
        rows = table_container.find_elements(By.TAG_NAME, "tr")

        if not rows:
            print("테이블 행을 찾을 수 없습니다.")
            driver.quit()
            exit()

        current_product_name = None  # 상품명은 CatIDsb로 시작하는 id를 가진 tr에서 추출

        for r_idx, row in enumerate(rows):
            row_id = row.get_attribute("id")
            if row_id and row_id.startswith("CatIDsb"):
                product_name_td = row.find_elements(By.TAG_NAME, "td")
                if product_name_td:
                    current_product_name = product_name_td[0].get_attribute(
                        'textContent').strip()
                continue  # CatIDsb 행은 상품명 추출 후 다음 행으로

            # 일반 데이터 행 처리
            cells_in_current_tr = row.find_elements(By.TAG_NAME, "td")

            # 각 셀에서 데이터 추출
            # 판매시기 (인덱스 0)
            sales_period = cells_in_current_tr[0].get_attribute(
                'textContent').strip() if len(cells_in_current_tr) > 0 else ""

            # 상품요약서 (인덱스 1)
            summary_link = None
            if len(cells_in_current_tr) > 1:
                try:
                    link_element = cells_in_current_tr[1].find_element(
                        By.TAG_NAME, "a")
                    summary_link = (
                        "상품요약서", link_element.get_attribute("href"))
                except NoSuchElementException:
                    summary_link = None

            # 약관 (인덱스 2)
            terms_link = None
            if len(cells_in_current_tr) > 2:
                try:
                    link_element = cells_in_current_tr[2].find_element(
                        By.TAG_NAME, "a")
                    terms_link = ("약관", link_element.get_attribute("href"))
                except NoSuchElementException:
                    terms_link = None

            # 사업방법서 (인덱스 3)
            business_method_link = None
            if len(cells_in_current_tr) > 3:
                try:
                    link_element = cells_in_current_tr[3].find_element(
                        By.TAG_NAME, "a")
                    business_method_link = (
                        "사업방법서", link_element.get_attribute("href"))
                except NoSuchElementException:
                    business_method_link = None

            # 추출된 데이터를 extracted_data에 추가
            extracted_data.append([
                current_product_name,
                sales_period,
                summary_link,
                terms_link,
                business_method_link
            ])

        print("--- Extracted Data ---")
        for row_data in extracted_data:
            print(row_data)

    except (TimeoutException, NoSuchElementException) as e:
        print(f"스크래핑 중 오류 발생: {e}")
    except Exception as e:  # 예상치 못한 다른 예외 처리
        print(f"예상치 못한 스크래핑 오류 발생: {e}")
    finally:
        driver.quit()

    return extracted_data


if __name__ == "__main__":
    data = scrape_axa_insurance_products()
    for product in data:
        print(product)
