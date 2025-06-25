# 카카오페이손해 /db기능
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager
from typing import List, Dict, Any
import time
import json  # json 모듈 추가


def get_kakaopay_insurance_details(headless: bool = True) -> List[Dict[str, str]]:
    url: str = "https://kakaopayinscorp.co.kr/disclosure/goods?code=goods_list"
    products_details: List[Dict[str, str]] = []
    driver: webdriver.Chrome = None

    try:
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--start-maximized")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)

        print("상품목록 및 기초서류' 버튼 클릭은 필요하지 않으므로 건너뜁니다.")

        # --- "더 보기" 버튼 클릭 루프 시작 ---
        initial_row_count = len(driver.find_elements(By.CSS_SELECTOR, "table.tbl_ins tbody tr"))
        print(f"초기 행 개수: {initial_row_count}")

        previous_row_count = initial_row_count
        max_clicks = 30  # 무한 루프 방지를 위한 최대 클릭 횟수

        for click_attempt in range(max_clicks):
            try:
                more_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.btn_more'))
                )

                driver.execute_script("arguments[0].click();", more_button)
                print(f"'더 보기' 버튼 클릭 (시도 {click_attempt + 1}).")

                try:
                    WebDriverWait(driver, 10).until(
                        lambda d: len(d.find_elements(By.CSS_SELECTOR, "table.tbl_ins tbody tr")) > previous_row_count
                    )
                    current_total_rows = len(driver.find_elements(By.CSS_SELECTOR, "table.tbl_ins tbody tr"))
                    print(f"  행 개수 증가: {previous_row_count} -> {current_total_rows}.")
                    previous_row_count = current_total_rows
                except TimeoutException:
                    current_total_rows = len(driver.find_elements(By.CSS_SELECTOR, "table.tbl_ins tbody tr"))
                    if current_total_rows == previous_row_count:
                        print("  클릭 후 행 개수가 증가하지 않았습니다. 모든 콘텐츠가 로드된 것으로 간주합니다.")
                        break
                    previous_row_count = current_total_rows

            except (TimeoutException, NoSuchElementException):
                print("'더 보기' 버튼을 더 이상 찾을 수 없거나 클릭할 수 없습니다. 모든 콘텐츠가 로드된 것으로 보입니다.")
                break
            except ElementClickInterceptedException:
                print("클릭이 가로막혔습니다. 스크롤 후 다시 시도합니다.")
                driver.execute_script("arguments[0].scrollIntoView(true);", more_button)
                time.sleep(0.5)
            except Exception as e:
                print(f"'더 보기' 버튼 클릭 중 예상치 못한 오류 발생: {e}")
                break
        # --- "더 보기" 버튼 클릭 루프 종료 ---

        final_total_rows = len(driver.find_elements(By.CSS_SELECTOR, "table.tbl_ins tbody tr"))
        print(f"'더 보기' 루프 후 발견된 총 행 개수: {final_total_rows}")
        if final_total_rows == 0:
            print("테이블에서 행을 찾을 수 없습니다. 빈 리스트를 반환합니다.")
            return products_details

        # --- 테이블 처리 시작 전에, 두 개의 테이블과 그 캡션이 모두 DOM에 나타날 때까지 대기 ---
        try:
            # 판매중인 상품 테이블의 캡션이 DOM에 존재할 때까지 대기
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//table[@class='tbl_ins']/caption[contains(text(), '판매중인 상품 안내')]"))
            )
            # 판매중지 상품 테이블의 캡션이 DOM에 존재할 때까지 대기
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//table[@class='tbl_ins']/caption[contains(text(), '판매중지중인 상품 안내')]"))
            )
            print("두 상품 테이블의 캡션이 모두 DOM에서 확인되었습니다. 테이블 처리를 시작합니다.")
        except TimeoutException as e:
            print(f"오류: 테이블 캡션 DOM 존재 확인 타임아웃 발생. 페이지 로드 문제일 수 있습니다: {e}")
            return products_details
        except Exception as e:
            print(f"오류: 테이블 캡션 대기 중 예상치 못한 오류 발생: {e}")
            return products_details
        # --- 테이블 대기 로직 종료 ---

        all_tables = driver.find_elements(By.CLASS_NAME, "tbl_ins")

        if not all_tables:
            print("콘텐츠 로드 후 'tbl_ins' 클래스를 가진 테이블을 찾을 수 없습니다.")
            return products_details

        for table_idx, table in enumerate(all_tables):
            try:
                # 각 테이블의 캡션 요소는 이미 위에서 기다렸으므로, 여기서는 바로 찾습니다.
                caption_element = table.find_element(By.TAG_NAME, "caption")
                caption_text = caption_element.get_attribute("textContent").strip()

                table_status = "알 수 없음"
                if "판매중인 상품 안내 테이블입니다." in caption_text:
                    table_status = "판매중"
                elif "판매중지중인 상품 안내 테이블입니다." in caption_text:
                    table_status = "판매중지"

                print(f"테이블 {table_idx + 1} 처리 중: '{caption_text}' (상태: {table_status})")

                # 각 테이블의 첫 번째 행의 첫 번째 셀이 나타날 때까지 대기하여 테이블 내부 데이터 로딩 확인
                WebDriverWait(table, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "tbody tr:first-child td:first-child"))
                )

                body_rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")

                if not body_rows:
                    print(f"테이블 {table_idx + 1} ({table_status})에 행이 없습니다. 다음 테이블로 이동합니다.")
                    continue

                for row_idx, row in enumerate(body_rows):
                    # 각 행의 모든 td 요소들이 로드될 때까지 대기
                    WebDriverWait(row, 5).until(
                        EC.presence_of_all_elements_located((By.TAG_NAME, "td"))
                    )
                    cells = row.find_elements(By.TAG_NAME, "td")

                    if len(cells) >= 5:  # 예상되는 최소 셀 개수
                        product_name = cells[2].text.strip()
                        sales_period = cells[3].text.strip()

                        download_links_container = cells[4]
                        product_data_entry: Dict[str, str] = {
                            "상품명": product_name,
                            "판매기간": sales_period,
                            "사업방법서": "N/A",
                            "상품요약서": "N/A",
                            "약관": "N/A",
                            "상태": table_status
                        }

                        links = download_links_container.find_elements(By.TAG_NAME, "a")
                        for link in links:
                            link_text = link.text.strip()
                            link_url = link.get_attribute("href") if "disabled" not in link.get_attribute("class") else "N/A (Disabled)"

                            if link_text == "사업방법서":
                                product_data_entry["사업방법서"] = link_url
                            elif link_text == "상품요약서":
                                product_data_entry["상품요약서"] = link_url
                            elif link_text == "보험약관":
                                product_data_entry["약관"] = link_url

                        products_details.append(product_data_entry)
                    else:
                        print(f"경고: 테이블 {table_idx + 1} ({table_status})의 {row_idx}번 행에 셀이 부족합니다 (예상 5개, 실제 {len(cells)}개). 이 행은 건너뜁니다.")
            except NoSuchElementException as e:
                print(f"오류: 테이블 {table_idx + 1} 처리 중 요소를 찾지 못했습니다: {e}. 이 테이블은 건너뜁니다.")
                continue
            except TimeoutException as e:
                print(f"오류: 테이블 {table_idx + 1} 처리 중 대기 시간 초과: {e}. 이 테이블은 건너뜁니다.")
                continue
            except Exception as e:
                print(f"오류: 테이블 {table_idx + 1} 처리 중 예상치 못한 오류 발생: {e}. 이 테이블은 건너뜁니다.")
                continue

    except Exception as e:
        print(f"전체 크롤링 과정 중 예상치 못한 오류 발생: {e}")
    finally:
        if driver:
            try:
                driver.quit()
                print("브라우저를 닫았습니다.")
            except Exception as e:
                print(f"브라우저 종료 중 오류 발생: {e}")

    return products_details


if __name__ == "__main__":
    print("카카오페이 보험 상품 데이터 크롤링 시작...")
    # headless=True로 설정하여 브라우저 UI 없이 실행
    product_details_list = get_kakaopay_insurance_details(headless=True)

    if product_details_list:
        print(f"\n--- 추출된 상품 정보 {len(product_details_list)}개 ---")
        for product in product_details_list:
            print(f"상품명:{product.get('상품명', 'N/A')},"
                  f"판매기간:{product.get('판매기간', 'N/A')},"
                  f"사업방법서:{product.get('사업방법서', 'N/A')},"
                  f"상품요약서:{product.get('상품요약서', 'N/A')},"
                  f"약관:{product.get('약관', 'N/A')},"
                  f"상태:{product.get('상태', 'N/A')}")

        # --- 추출된 데이터를 JSON 파일로 저장 ---
        json_file_name = "kakaopay_insurance_products.json"
        try:
            with open(json_file_name, 'w', encoding='utf-8') as f:
                json.dump(product_details_list, f, ensure_ascii=False, indent=4)
            print(f"\n성공적으로 {len(product_details_list)}개의 상품 정보를 '{json_file_name}' 파일에 저장했습니다.")
        except Exception as e:
            print(f"\nJSON 파일 저장 중 오류 발생: {e}")
    else:
        print("\n추출된 상품 데이터가 없습니다.")
