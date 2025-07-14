# 카카오페이손해
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager
from typing import List, Dict, Optional
import time
import os
import sys
from datetime import datetime

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from neoali.DB_save import DatabaseManager  # DatabaseManager import 추가
except ImportError as e:
    DatabaseManager = None  # DatabaseManager 초기화 추가
    print(f"경고: 모듈 임포트 실패 ({e}). 일부 기능이 비활성화될 수 있습니다.")


def get_kakaopay_insurance_details(headless: bool = True) -> List[Dict[str, str]]:
    url: str = "https://kakaopayinscorp.co.kr/disclosure/goods?code=goods_list"
    products_details: List[Dict[str, str]] = []
    driver: webdriver.Chrome = None

    try:
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--start-maximized")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)

        # "더 보기" 버튼 클릭 루프 시작
        previous_row_count = len(driver.find_elements(By.CSS_SELECTOR, "table.tbl_ins tbody tr"))
        max_clicks = 30  # 무한 루프 방지를 위한 최대 클릭 횟수

        for click_attempt in range(max_clicks):
            try:
                more_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.btn_more'))
                )
                driver.execute_script("arguments[0].click();", more_button)

                try:
                    WebDriverWait(driver, 10).until(
                        lambda d: len(d.find_elements(By.CSS_SELECTOR, "table.tbl_ins tbody tr")) > previous_row_count
                    )
                    previous_row_count = len(driver.find_elements(By.CSS_SELECTOR, "table.tbl_ins tbody tr"))
                except TimeoutException:
                    current_total_rows = len(driver.find_elements(By.CSS_SELECTOR, "table.tbl_ins tbody tr"))
                    if current_total_rows == previous_row_count:
                        break  # 행 개수 변화 없으면 루프 종료
                    previous_row_count = current_total_rows

            except (TimeoutException, NoSuchElementException):
                break  # '더 보기' 버튼 없으면 루프 종료
            except ElementClickInterceptedException:
                driver.execute_script("arguments[0].scrollIntoView(true);", more_button)
                time.sleep(0.5)
            except Exception:
                break  # 다른 예외 발생 시 루프 종료

        final_total_rows = len(driver.find_elements(By.CSS_SELECTOR, "table.tbl_ins tbody tr"))
        if final_total_rows == 0:
            return products_details

        # 테이블 캡션이 모두 DOM에 나타날 때까지 대기
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//table[@class='tbl_ins']/caption[contains(text(), '판매중인 상품 안내')]"))
        )
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//table[@class='tbl_ins']/caption[contains(text(), '판매중지중인 상품 안내')]"))
        )

        all_tables = driver.find_elements(By.CLASS_NAME, "tbl_ins")

        if not all_tables:
            return products_details

        for table_idx, table in enumerate(all_tables):
            try:
                caption_element = table.find_element(By.TAG_NAME, "caption")
                caption_text = caption_element.get_attribute("textContent").strip()

                table_status = "알 수 없음"
                if "판매중인 상품 안내 테이블입니다." in caption_text:
                    table_status = "판매중"
                elif "판매중지중인 상품 안내 테이블입니다." in caption_text:
                    table_status = "판매중지"

                WebDriverWait(table, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "tbody tr:first-child td:first-child"))
                )

                body_rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")

                if not body_rows:
                    continue

                for row in body_rows:
                    WebDriverWait(row, 5).until(
                        EC.presence_of_all_elements_located((By.TAG_NAME, "td"))
                    )
                    cells = row.find_elements(By.TAG_NAME, "td")

                    if len(cells) >= 5:
                        product_name = cells[2].text.strip()
                        sales_period = cells[3].text.strip()

                        download_links_container = cells[4]

                        product_data_entry: Dict[str, Optional[str]] = {
                            "상품명": product_name,
                            "판매기간": sales_period,
                            "사업방법서": None,
                            "상품요약서": None,
                            "약관": None,
                            "상태": table_status
                        }

                        links = download_links_container.find_elements(By.TAG_NAME, "a")
                        for link in links:
                            link_text = link.text.strip()
                            link_url = link.get_attribute("href") if "disabled" not in link.get_attribute("class") else None

                            if link_text == "사업방법서":
                                product_data_entry["사업방법서"] = link_url
                            elif link_text == "상품요약서":
                                product_data_entry["상품요약서"] = link_url
                            elif link_text == "보험약관":
                                product_data_entry["약관"] = link_url

                        products_details.append(product_data_entry)
            except (NoSuchElementException, TimeoutException):
                continue  # 문제 발생 시 해당 테이블 건너뛰기
            except Exception:
                continue  # 다른 예외 발생 시 해당 테이블 건너뛰기

    except Exception as e:
        print(f"크롤링 실패: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass  # 브라우저 종료 실패는 무시

    return products_details


if __name__ == "__main__":
    print("카카오페이 보험 상품 데이터 크롤링 시작...")

    product_details_list = get_kakaopay_insurance_details(headless=True)

    if product_details_list:
        scraped_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            with DatabaseManager(db_name="kakaopay_web_data.db") as db_manager:
                structured_rows = []
                for product in product_details_list:
                    product_name = product.get("상품명", "N/A")
                    sales_period = product.get("판매기간", "N/A")

                    # 약관 저장
                    link = product.get("약관")
                    if link is not None:
                        structured_rows.append([
                            "카카오페이손해보험",
                            product_name,
                            None,
                            "약관",
                            sales_period,
                            scraped_time,
                            link
                        ])

                    # 사업방법서 저장
                    link = product.get("사업방법서")
                    if link is not None:
                        structured_rows.append([
                            "카카오페이손해보험",
                            product_name,
                            None,
                            "사업방법서",
                            sales_period,
                            scraped_time,
                            link
                        ])

                    # 상품요약서 저장
                    link = product.get("상품요약서")
                    if link is not None:
                        structured_rows.append([
                            "카카오페이손해보험",
                            product_name,
                            None,
                            "상품요약서",
                            sales_period,
                            scraped_time,
                            link
                        ])

                saved_count = db_manager.save_data(structured_rows)
                print(f"DB 저장 완료: {saved_count}개의 항목 저장됨")
        except Exception as e:
            print(f"DB 저장 실패: {e}")

    else:
        print("크롤링된 상품 데이터 없음.")

    print("카카오페이 보험 상품 데이터 크롤링 종료.")
