# abl생명/db 확인/판매중지페이지
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from neoali.DB_save import DatabaseManager
from datetime import datetime


def scrape_abllife():
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless') # 브라우저를 백그라운드에서 실행 (선택 사항)
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')

    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1280, 800)

    base_url = "https://www.abllife.co.kr"
    initial_url = base_url + "/st/pban/prdtPban/whlPrdt/whlPrdt1/whlPrdt11?page=index"
    driver.get(initial_url)

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.fss_body"))
    )

    products_data = []

    # 모든 유형 탭 링크 가져오기
    type_elements = driver.find_elements(By.CSS_SELECTOR, "div.pd_wrap_tab2 .tab_wrap.sub .cnt_8.clearfix div a")

    type_links = []
    for type_element in type_elements:
        type_name = type_element.text.strip()
        type_href_raw = type_element.get_attribute("href")  # 먼저 href 속성 값을 가져옴

        if type_name and type_href_raw:
            if type_href_raw.startswith(base_url):
                type_href = type_href_raw
            elif type_href_raw.startswith('/'):
                type_href = base_url + type_href_raw
            else:
                type_href = base_url + '/' + type_href_raw
            type_links.append({
                "name": type_name,
                "href": type_href
            })

    for type_info in type_links:
        type_name = type_info["name"]
        type_url = type_info["href"]

        driver.get(type_url)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.fss_body"))
        )

        # 현재 유형 페이지의 상품 목록 가져오기
        product_elements = driver.find_elements(By.CSS_SELECTOR, "div.fss_body ul li a")

        product_links_in_type = []
        for product_element in product_elements:
            product_links_in_type.append({
                "name": product_element.text.strip(),
                "href": product_element.get_attribute("href")
            })

        for product_info in product_links_in_type:
            product_name = product_info["name"]
            if product_info["href"].startswith(base_url):
                product_url = product_info["href"]
            elif product_info["href"].startswith('/'):
                product_url = base_url + product_info["href"]
            else:
                product_url = base_url + '/' + product_info["href"]

            print(f"상품명: {product_name}")

            # 상품 상세 페이지로 이동
            driver.get(product_url)

            try:
                # 판매 기간별 정보 가져오기
                sales_period_rows = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.tablewrap tbody tr"))
                )

                for row in sales_period_rows:
                    sales_period = row.find_element(By.CSS_SELECTOR, "td:first-child").text.strip()
                    business_method_link = ""
                    summary_link = ""
                    agreement_link = ""

                    # '사업방법서' 링크 찾기
                    try:
                        business_method_element = row.find_element(By.CSS_SELECTOR, "td:nth-child(2) a")
                        business_method_link = business_method_element.get_attribute("href")
                    except Exception:
                        pass  # 사업방법서 링크가 없을 수도 있음

                    # '상품요약서' 링크 찾기
                    try:
                        summary_element = row.find_element(By.CSS_SELECTOR, "td:nth-child(3) a")
                        summary_link = summary_element.get_attribute("href")
                    except Exception:
                        pass  # 상품요약서 링크가 없을 수도 있음

                    # '약관' 링크 찾기
                    try:
                        agreement_element = row.find_element(By.CSS_SELECTOR, "td:nth-child(4) a")
                        agreement_link = agreement_element.get_attribute("href")
                    except Exception:
                        pass  # 약관 링크가 없을 수도 있음

                    products_data.append({
                        "유형": type_name,  # 유형 정보 추가
                        "상품명": product_name,
                        "판매기간": sales_period,
                        "약관": agreement_link,
                        "상품요약서": summary_link,
                        "사업방법서": business_method_link
                    })

            except Exception as e:
                print(f"상품 '{product_name}'의 상세 정보를 가져오는 중 오류 발생: {e}")

            # 이전 페이지로 돌아가기 (유형별 상품 목록 페이지)
            driver.back()
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.fss_body"))
            )
            time.sleep(1)  # 페이지 로딩 대기

    driver.quit()

    # 데이터를 DB에 저장
    structured_rows = []
    scraped_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    company_name = "ABL생명"  # 회사명 고정

    for product_item in products_data:
        product_name = product_item.get("상품명", "N/A")
        sales_period = product_item.get("판매기간", "N/A")
        product_code = "N/A"  # 현재 스크래핑 데이터에 없으므로 N/A로 설정

        if product_item.get("약관"):
            structured_rows.append([
                company_name, product_name, product_code,
                "약관", sales_period, scraped_time, product_item["약관"]
            ])
        if product_item.get("상품요약서"):
            structured_rows.append([
                company_name, product_name, product_code,
                "상품요약서", sales_period, scraped_time, product_item["상품요약서"]
            ])
        if product_item.get("사업방법서"):
            structured_rows.append([
                company_name, product_name, product_code,
                "사업방법서", sales_period, scraped_time, product_item["사업방법서"]
            ])

    total_products_scraped = len(products_data)

    if structured_rows:
        with DatabaseManager() as db_manager:
            saved_count = db_manager.save_data(structured_rows)
        print(f"해당 상품의 개수: {total_products_scraped}, 저장된 개수: {saved_count}")
    else:
        print("스크래핑된 데이터가 없습니다.")


if __name__ == "__main__":
    scrape_abllife()
