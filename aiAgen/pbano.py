from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import time

# 판매중단 페이지/링크/db저장


def scrape_pbano_products():
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless') # 브라우저가 보이는 모드로 실행되도록 주석 처리
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    url = "https://pbano.myangel.co.kr/paging/WE_AC_WEPAAP020100L"
    driver.get(url)
    wait = WebDriverWait(driver, 10)

    all_products_data = []
    page_num = 1

    try:  # try-finally 블록으로 전체 스크래핑 로직을 감싸서 드라이버가 항상 종료되도록 함
        while True:
            print(f"스크래핑 중... 페이지: {page_num}")
            try:
                # 테이블 본문 찾기
                table_body = wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "table.tableStyle > tbody"))
                )
                rows = table_body.find_elements(By.TAG_NAME, "tr")

                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) == 0:  # 헤더 행이나 빈 행 건너뛰기
                        continue

                    # 컬럼 순서: 번호, 판매채널, 구분, 상품명, 판매기간, 상품요약서, 사업방법서, 보험약관
                    # 인덱스: 0, 1, 2, 3, 4, 5, 6, 7

                    product_name = cells[3].text.strip() if len(
                        cells) > 3 else ""
                    sales_period = cells[4].text.strip() if len(
                        cells) > 4 else ""

                    summary_link = None
                    if len(cells) > 5:
                        try:
                            link_element = cells[5].find_element(
                                By.TAG_NAME, "a")
                            summary_link = (
                                "상품요약서", link_element.get_attribute("href"))
                        except NoSuchElementException:
                            pass

                    business_method_link = None
                    if len(cells) > 6:
                        try:
                            link_element = cells[6].find_element(
                                By.TAG_NAME, "a")
                            business_method_link = (
                                "사업방법서", link_element.get_attribute("href"))
                        except NoSuchElementException:
                            pass

                    insurance_terms_link = None
                    if len(cells) > 7:
                        try:
                            link_element = cells[7].find_element(
                                By.TAG_NAME, "a")
                            insurance_terms_link = (
                                "보험약관", link_element.get_attribute("href"))
                        except NoSuchElementException:
                            pass

                    all_products_data.append({
                        "상품명": product_name,
                        "판매기간": sales_period,
                        "상품요약서": summary_link,
                        "사업방법서": business_method_link,
                        "보험약관": insurance_terms_link
                    })

                # 페이지네이션 처리
                # 현재 활성화된 페이지 번호 찾기
                current_page_element = wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.paging strong"))
                )
                current_page_number = int(current_page_element.text)

                next_page_link_found = False
                # 모든 페이지 번호 링크 찾기
                page_links = driver.find_elements(
                    By.CSS_SELECTOR, "div.paging a")
                for link in page_links:
                    try:
                        link_text = link.text.strip()
                        if link_text.isdigit():  # 페이지 번호인 경우
                            page_number = int(link_text)
                            if page_number == current_page_number + 1:
                                link.click()
                                page_num += 1
                                time.sleep(2)  # 페이지 로드 대기
                                next_page_link_found = True
                                break
                    except ValueError:
                        continue  # 숫자가 아닌 링크 (예: <, >, <<, >>)는 건너뛰기

                if not next_page_link_found:
                    break  # 다음 페이지 링크를 찾지 못하면 루프 종료

            except TimeoutException:
                print("테이블 또는 페이지네이션 요소를 찾을 수 없습니다. 스크래핑을 종료합니다.")
                break
            except Exception as e:
                print(f"스크래핑 중 오류 발생: {e}")
                break
    finally:
        driver.quit()  # 모든 스크래핑 작업이 완료된 후에 드라이버 종료

    return all_products_data


if __name__ == "__main__":
    data = scrape_pbano_products()
    for product in data:
        print(product)
    print(f"총 스크래핑된 데이터 개수: {len(data)}개")
