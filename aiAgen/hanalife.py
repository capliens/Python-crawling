# 하나생명/판매중단페이지/db 기능 추기및 확인
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from seleniumwire import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import time


def setup_driver():
    """Selenium WebDriver 인스턴스를 기본 옵션으로 설정하고 반환합니다."""
    chrome_options = Options()
    # 브라우저 GUI를 열지 않고 헤드리스 모드로 실행하려면 아래 주석을 해제하세요.
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def scrape_hanalife_products(url):
    driver = None
    all_product_data = []  # 추출된 모든 상품 딕셔너리를 저장할 리스트
    try:
        driver = setup_driver()
        driver.get(url)

        # 첫 번째 상품명 요소 로드를 기다립니다. (이 XPath는 변경 없음)
        print("첫 번째 상품명 요소 로드를 기다리는 중...")
        first_product_name_xpath = '//*[@id="contents"]/div[5]/table/tbody/tr[1]/td[3]'
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, first_product_name_xpath))
        )
        print("첫 번째 상품명 요소 로드를 확인했습니다. 데이터 추출 시작...")

        # **테이블 요소를 div.tbl-type3 > table CSS 셀렉터로 찾습니다.**
        # 이는 div 태그 중 tbl-type3 클래스를 가진 요소의 직계 자식인 table 태그를 의미합니다.
        print("정확한 테이블 요소를 찾는 중...")
        table_css_selector = "div.tbl-type3 > table"
        product_table = driver.find_element(By.CSS_SELECTOR, table_css_selector)
        print("테이블 요소를 성공적으로 찾았습니다.")

        # 테이블 헤더를 가져옵니다.
        headers = []
        header_elements = product_table.find_elements(By.XPATH, "./thead/tr/th")
        for header_elem in header_elements:
            headers.append(header_elem.text.strip())
        print(f"추출된 헤더: {headers}")

        rows = product_table.find_elements(By.XPATH, "./tbody/tr")
        print(f"찾은 테이블 행(row)의 개수: {len(rows)}")

        if not rows:
            print("경고: 테이블 본문에서 행(tr)을 찾을 수 없습니다. XPath './tbody/tr'을 확인하세요.")

        for i, row in enumerate(rows):
            product_info = {}
            cols = row.find_elements(By.XPATH, "./td")
            print(f"  행 {i + 1}의 컬럼(td) 개수: {len(cols)}")

            # 대상, 분류, 상품명, 판매기간
            if len(cols) > 0:
                product_info[headers[0]] = cols[0].text.strip() if len(cols) > 0 else ""
                product_info[headers[1]] = cols[1].text.strip() if len(cols) > 1 else ""
                product_info[headers[2]] = cols[2].text.strip() if len(cols) > 2 else ""
                product_info[headers[3]] = cols[3].text.strip() if len(cols) > 3 else ""

            if headers[2] in product_info:
                print(f"  행 {i + 1} - 상품명: '{product_info[headers[2]]}'")
            else:
                print(f"  행 {i + 1} - 상품명 컬럼을 찾을 수 없거나 비어있습니다.")

            # 문서 다운로드 링크 추출 (상품요약서, 사업방법서, 보험약관)
            document_cols_map = {
                "상품요약서": 4,
                "사업방법서": 5,
                "보험약관": 6
            }

            for doc_type, col_idx in document_cols_map.items():
                if len(cols) > col_idx:
                    doc_cell = cols[col_idx]
                    download_links = doc_cell.find_elements(By.TAG_NAME, 'a')

                    if download_links:
                        if len(download_links) == 1:
                            link = download_links[0]
                            product_info[doc_type] = {
                                "text": link.text.strip(),
                                "url": link.get_attribute('href')
                            }
                        else:
                            product_info[doc_type] = []
                            for link in download_links:
                                product_info[doc_type].append({
                                    "text": link.text.strip(),
                                    "url": link.get_attribute('href')
                                })
                    else:
                        product_info[doc_type] = None

            if product_info.get(headers[2]):
                all_product_data.append(product_info)
            else:
                print(f"  행 {i + 1}은(는 상품명이 없어) 데이터 목록에 추가되지 않았습니다.")

        print("\n추출된 상품 데이터:")
        if not all_product_data:
            print("데이터가 추출되지 않았습니다. 위 디버그 메시지를 확인하여 문제 원인을 파악하세요.")
        for product in all_product_data:
            print(product)

    except TimeoutException:
        print("페이지 로드 시간이 초과되었거나 첫 번째 상품명 요소를 찾을 수 없습니다. 네트워크 연결 또는 셀렉터를 확인하세요.")
    except NoSuchElementException as e:
        print(f"필요한 웹 요소를 찾을 수 없습니다: {e}")
    except Exception as e:
        print(f"예기치 않은 오류가 발생했습니다: {e}")
    finally:
        if driver:
            driver.quit()
            print("\n브라우저가 닫혔습니다.")


if __name__ == "__main__":
    target_url = "https://hanalife.co.kr/anm/product/allProduct.do?status=on"
    scrape_hanalife_products(target_url)
