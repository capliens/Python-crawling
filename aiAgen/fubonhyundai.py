import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException

DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# db/pdf링크


def get_product_info():
    chrome_options = webdriver.ChromeOptions()
    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        print(f"웹 드라이버 설정 중 오류 발생: {e}")
        if driver:
            driver.quit()
        return

    base_url = "https://www.fubonhyundai.com/#CUSI150102010101"
    driver.get(base_url)
    driver.implicitly_wait(5)

    all_products_data = []

    try:
        search_tab_selector = "div.c-tab__list > button#tab-list3-3"
        search_tab_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, search_tab_selector))
        )
        print(f"상품검색 탭 클릭 시도 (CSS Selector: {search_tab_selector})")
        driver.execute_script("arguments[0].click();", search_tab_button)
        print("상품검색 탭 클릭 완료 (JavaScript 실행)")

        # "상품검색" 탭 클릭 후 해당 패널(div#tab-panel3-3)이 활성화되고 보이는지 확인
        clicked_panel_selector = "div#tab-panel3-3"
        WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, clicked_panel_selector))
        )
        print(f"클릭 후: {clicked_panel_selector} (상품검색 패널) 확인 및 표시됨.")

        # 해당 패널 내의 div.c-table 확인
        # 사용자가 알려준 정확한 구조는 div.c-table > table > tbody#tab 이므로,
        # specific_table_container_selector는 div.c-table 까지만 지정하거나,
        # 혹은 바로 table 요소를 찾는 것이 더 명확할 수 있습니다.
        # 여기서는 div.c-table을 먼저 찾고, 그 다음에 table > tbody#tab을 찾겠습니다.
        specific_c_table_selector = f"{clicked_panel_selector} > div.c-table"
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, specific_c_table_selector))
        )
        print(f"클릭 후: {specific_c_table_selector} 요소 확인됨.")

        # 해당 테이블 내의 tbody#tab 요소가 나타나고 보이는지 확인 (사용자 제공 선택자 반영)
        specific_tbody_selector_after_click = f"{specific_c_table_selector} > table > tbody#tab"
        WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, specific_tbody_selector_after_click))
        )
        print(f"클릭 후: {specific_tbody_selector_after_click} 요소 확인 및 표시됨.")

        time.sleep(2)  # 명시적 대기 후 추가적인 안정성을 위한 짧은 sleep

        page_num = 1
        while True:
            print(f"\n--- {page_num} 페이지 데이터 수집 중 ---")
            product_rows_selector = f"{specific_tbody_selector_after_click} > tr"

            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, product_rows_selector))
                )
                product_rows = driver.find_elements(By.CSS_SELECTOR, product_rows_selector)
                if not product_rows or \
                   (len(product_rows) == 1 and "데이터가 없습니다" in product_rows[0].text.strip()):
                    print("현재 페이지에 상품 데이터가 없습니다.")
                    break
            except TimeoutException:
                print("상품 목록을 찾을 수 없습니다. (Timeout)")
                break

            print(f"{len(product_rows)}개의 상품을 찾았습니다.")

            for i, row in enumerate(product_rows):
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if not cells or len(cells) < 5:
                        if cells and "데이터가 없습니다" in cells[0].text.strip():
                            print("데이터가 없는 행입니다.")
                        else:
                            print(f"Skipping row {i + 1} due to insufficient cells or unexpected structure.")
                        continue

                    product_name = cells[0].text.strip()
                    sales_period = cells[1].text.strip()

                    def get_download_link_element(cell):
                        try:
                            link_el = cell.find_element(By.TAG_NAME, "a")
                            return link_el
                        except NoSuchElementException:
                            return None

                    summary_link_element = get_download_link_element(cells[2])
                    terms_link_element = get_download_link_element(cells[3])
                    biz_method_link_element = get_download_link_element(cells[4])

                    product_data = {
                        "상품명": product_name,
                        "판매기간": sales_period,
                        "상품요약서_element": summary_link_element,
                        "약관_element": terms_link_element,
                        "사업방법서_element": biz_method_link_element,
                        "상품요약서_파일명": "N/A",
                        "약관_파일명": "N/A",
                        "사업방법서_파일명": "N/A"
                    }
                    print(f"  - 상품명: {product_name}, 판매기간: {sales_period}")
                    all_products_data.append(product_data)

                except NoSuchElementException as e_nse:
                    print(f"  상품 정보 중 일부를 찾을 수 없습니다 (행 {i + 1}): {e_nse}")
                except Exception as e_general:
                    print(f"  상품 정보 추출 중 오류 (행 {i + 1}): {e_general}")

            next_page_button_selector = "nav#pagenation > a.paging__anchor--next"
            next_page_buttons = driver.find_elements(By.CSS_SELECTOR, next_page_button_selector)

            if not next_page_buttons:
                print("다음 페이지 버튼을 찾을 수 없습니다. 마지막 페이지입니다.")
                break

            try:
                next_page_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, next_page_button_selector))
                )
                print("다음 페이지로 이동합니다.")
                driver.execute_script("arguments[0].click();", next_page_button)
                WebDriverWait(driver, 10).until(
                    EC.staleness_of(product_rows[0])
                )
                time.sleep(1)
                page_num += 1
            except TimeoutException:
                print("다음 페이지 버튼 클릭 후 페이지 로드 확인 시간 초과. 마지막 페이지일 수 있습니다.")
                break
            except ElementClickInterceptedException:
                print("다음 페이지 버튼 클릭이 가로막혔습니다.")
                break
            except Exception as e:
                print(f"페이지 이동 중 오류 발생: {e}")
                break

    except TimeoutException as e_timeout:
        print(f"페이지 로드 시간 초과 또는 특정 요소를 찾을 수 없습니다: {e_timeout}")
    except Exception as e_script:
        print(f"스크립트 실행 중 오류 발생: {e_script}")
    finally:
        if driver:
            driver.quit()
        print("\n--- 전체 상품 데이터 (요소 정보 포함) ---")
        print(f"총 {len(all_products_data)}개의 상품 정보를 수집했습니다 (다운로드 제외).")
        print(f"다운로드된 파일은 '{DOWNLOAD_DIR}' 폴더를 확인 (실제 다운로드 로직 구현 시).")


if __name__ == "__main__":
    get_product_info()
