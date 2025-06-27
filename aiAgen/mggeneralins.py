# MG손해보험:
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from seleniumwire import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import time
import re


def setup_driver():
    """Selenium WebDriver 인스턴스를 설정하고 반환합니다."""
    chrome_options = Options()
    # GUI 없이 백그라운드에서 브라우저를 실행하려면 아래 주석을 해제하세요.
    # chrome_options.add_argument("--headless")
    # chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--allow-running-insecure-content")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def handle_modal_if_present(driver):
    """
    모달창이 나타나면 확인 버튼을 클릭하여 닫는 함수입니다.
    모달창이 없으면 바로 반환합니다.
    """
    try:
        # 모달창의 내용이 나타날 때까지 최대 3초 기다립니다.
        # 모달창이 없으면 TimeoutException이 발생합니다.
        modal_message = WebDriverWait(driver, 3).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "SAlert-message"))
        )
        print(f"      [모달 감지] 모달 메시지: '{modal_message.text.strip()}'")

        # 확인(OK) 버튼이 클릭 가능할 때까지 기다린 후 클릭합니다.
        ok_button = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".SAlert-button .SAlert-BtnConfirm"))
        )
        ok_button.click()
        print("      [모달 처리] 'OK' 버튼 클릭 완료.")

        # 모달창이 사라질 때까지 기다립니다.
        WebDriverWait(driver, 5).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, "SAlert-Contents"))
        )
        print("      [모달 처리] 모달창 사라짐 확인.")
        return True  # 모달창을 처리했음을 알림
    except TimeoutException:
        # 모달창이 나타나지 않았으므로 아무것도 하지 않습니다.
        return False  # 모달창이 없었음을 알림
    except Exception as e:
        print(f"      [모달 처리 오류] 모달 처리 중 예상치 못한 오류 발생: {e}")
        return False  # 오류 발생 시에도 모달창이 없었거나 처리 실패


def extract_level3_data(driver, category_name_step1, category_name_step2):
    """
    3단계 정보를 추출하는 함수입니다.
    제품명, 판매기간, 그리고 각 다운로드 링크의 JavaScript 함수 인자를 추출합니다.
    """
    print(f"\n      --- 3단계 정보 추출 시작 ---")
    print(f"      현재 경로: 1단계: '{category_name_step1}', 2단계: '{category_name_step2}'")

    try:
        # 3단계 컨테이너 div (.pb_step03)가 화면에 나타날 때까지 기다립니다.
        # 모달창이 뜨지 않고 바로 3단계가 로드되는 경우를 대비합니다.
        WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".pb_step03"))
        )
        print("      3단계 컨테이너 (.pb_step03) 로드 완료.")

        product_ul_elements = driver.find_elements(By.CSS_SELECTOR, ".pb_step03 > ul")

        if not product_ul_elements:
            print("      3단계에서 제품 정보를 찾을 수 없습니다. (제품 목록이 비어있을 수 있음)")
            return

        print(f"      총 {len(product_ul_elements)}개의 제품 항목을 찾았습니다.")

        extracted_data = []

        for i, product_ul in enumerate(product_ul_elements):
            try:
                product_name_element = WebDriverWait(product_ul, 5).until(
                    EC.presence_of_element_located((By.TAG_NAME, "h5"))
                )
                product_name = product_name_element.text.strip()
                print(f"      - 제품명: {product_name}")

                table = WebDriverWait(product_ul, 5).until(
                    EC.presence_of_element_located((By.TAG_NAME, "table"))
                )

                try:
                    sales_period = table.find_element(By.XPATH, ".//tbody/tr/td[1]").text.strip()
                except NoSuchElementException:
                    sales_period = "판매기간 없음"
                print(f"        판매기간: {sales_period}")

                download_links = table.find_elements(By.CSS_SELECTOR, "tbody td a")

                js_pattern = re.compile(r"pdfDownload\('([^']+)',\s*'([^']+)'\)")

                item_downloads = {
                    "상품요약서": None,
                    "약관": None,
                    "사업방법서": None
                }

                if len(download_links) >= 3:
                    link_sum_href = download_links[0].get_attribute("href")
                    match_sum = js_pattern.search(link_sum_href)
                    if match_sum:
                        item_downloads["상품요약서"] = {'id': match_sum.group(1), 'type': match_sum.group(2)}
                        # print(f"        상품요약서: ID={match_sum.group(1)}, Type={match_sum.group(2)}")

                    link_terms_href = download_links[1].get_attribute("href")
                    match_terms = js_pattern.search(link_terms_href)
                    if match_terms:
                        item_downloads["약관"] = {'id': match_terms.group(1), 'type': match_terms.group(2)}
                        # print(f"        약관: ID={match_terms.group(1)}, Type={match_terms.group(2)}")

                    link_biz_href = download_links[2].get_attribute("href")
                    match_biz = js_pattern.search(link_biz_href)
                    if match_biz:
                        item_downloads["사업방법서"] = {'id': match_biz.group(1), 'type': match_biz.group(2)}
                        # print(f"        사업방법서: ID={match_biz.group(1)}, Type={match_biz.group(2)}")
                else:
                    print("        다운로드 링크 개수가 예상과 다릅니다. (3개 미만)")

                extracted_data.append({
                    "1단계 카테고리": category_name_step1,
                    "2단계 카테고리": category_name_step2,
                    "제품명": product_name,
                    "판매기간": sales_period,
                    "다운로드_정보": item_downloads
                })

            except TimeoutException as e:
                print(f"      제품 항목 {i + 1}에서 요소 로드 타임아웃 발생 (일부 정보 누락될 수 있음): {e}")
            except NoSuchElementException as e:
                print(f"      제품 항목 {i + 1}에서 필수 요소를 찾을 수 없음 (일부 정보 누락될 수 있음): {e}")
            except Exception as e:
                print(f"      제품 항목 {i + 1} 처리 중 예상치 못한 오류 발생: {e}")

        print("\n      --- 최종 추출된 3단계 데이터 요약 ---")
        if extracted_data:
            for data in extracted_data:
                print(f"      경로: {data['1단계 카테고리']} > {data['2단계 카테고리']}")
                print(f"      제품: {data['제품명']}, 판매기간: {data['판매기간']}")
                print(f"      다운로드: {data['다운로드_정보']}")
                print("-" * 20)
        else:
            print("      추출된 3단계 제품 데이터가 없습니다.")

    except TimeoutException:
        # 3단계 컨테이너가 나타나지 않은 경우 (예: 모달창만 뜨고 제품이 없는 경우)
        print("      3단계 컨테이너 (.pb_step03) 로드 타임아웃. 제품이 없거나 다른 콘텐츠가 로드되었을 수 있습니다.")
    except Exception as e:
        print(f"      3단계 처리 중 예상치 못한 오류 발생: {e}")

    print(f"      --- 3단계 정보 추출 완료 ---")


def crawl_level2_and_extract_data(driver, parent_category_name):
    """
    2단계 탐색 및 3단계 정보 추출을 수행하는 함수입니다.
    """
    print(f"\n--- 2단계 탐색 시작: {parent_category_name} ---")

    tab_wrap_map = {
        '장기보험': 'tab01_wrap',
        '자동차보험': 'tab02_wrap',
        '일반보험': 'tab03_wrap'
    }

    target_tab_wrap_class = tab_wrap_map.get(parent_category_name)

    if not target_tab_wrap_class:
        print(f"경고: 알 수 없는 1단계 카테고리 '{parent_category_name}'. 2단계 탭 래퍼를 찾을 수 없습니다.")
        return

    try:
        print(f"  2단계 '{target_tab_wrap_class}' 로드를 기다리는 중...")
        active_tab_wrap = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, f".pb_step02 .{target_tab_wrap_class}"))
        )

        level2_item_data = []
        level2_links = WebDriverWait(active_tab_wrap, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ul.bul_list li a"))
        )

        for link in level2_links:
            item_text = link.text.strip()
            item_id = link.find_element(By.XPATH, "./..").get_attribute("id")
            level2_item_data.append({'text': item_text, 'id': item_id})

        if not level2_item_data:
            print(f"  2단계 '{parent_category_name}' 카테고리에서 항목을 찾을 수 없습니다.")
            return

        print(f"  2단계에서 {len(level2_item_data)}개의 항목을 찾았습니다.")

        for i, item_info in enumerate(level2_item_data):
            item_name = item_info['text']
            item_id = item_info['id']

            print(f"  [2단계] '{item_name}' 항목 클릭 시도 (ID: {item_id}, {i + 1}/{len(level2_item_data)})")

            current_item_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f"//div[contains(@class, '{target_tab_wrap_class}')]//li[@id='{item_id}']/a"))
            )
            current_item_link.click()

            # 클릭 후 모달창이 나타날 수 있으므로 먼저 모달창 처리 시도
            time.sleep(1)  # 모달창이 뜰 시간을 잠시 기다림
            modal_handled = handle_modal_if_present(driver)

            if modal_handled:
                print(f"  [2단계] '{item_name}' 클릭 후 모달창이 처리되었습니다. 3단계 정보 추출을 건너뜝니다.")
                # 모달창이 떴다는 것은 해당 상품에 대한 정보가 없다는 의미이므로 3단계 추출 건너뜀
                continue  # 다음 2단계 항목으로 넘어감
            else:
                # 모달창이 뜨지 않았다면 3단계 정보 로드를 기다림
                time.sleep(2)  # 3단계 정보가 로드될 시간을 줍니다. (필요시 EC로 변경)
                # 3단계 정보 추출 함수 호출
                extract_level3_data(driver, parent_category_name, item_name)

    except TimeoutException as e:
        print(f"  2단계에서 타임아웃 발생: {e}")
    except NoSuchElementException as e:
        print(f"  2단계에서 요소를 찾을 수 없음: {e}")
    except Exception as e:
        print(f"  2단계 처리 중 예상치 못한 오류 발생: {e}")

    print(f"--- 2단계 탐색 완료: {parent_category_name} ---")


def crawl_website(url):
    driver = None
    try:
        driver = setup_driver()
        driver.get(url)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".pb_step01"))
        )
        print(f"성공적으로 페이지 로드: {url}")

        print("\n--- 1단계: 구분 선택 순회 시작 ---")
        step1_tab_data = []
        step1_tabs = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".pb_step01 .pb_tab ul li a"))
        )
        for tab in step1_tabs:
            tab_id = tab.find_element(By.XPATH, "./..").get_attribute("id")
            tab_name = tab.find_element(By.TAG_NAME, "span").text.strip()
            step1_tab_data.append({'id': tab_id, 'name': tab_name})

        if not step1_tab_data:
            print("1단계 탭을 찾을 수 없습니다. 셀렉터를 확인해주세요.")
            return

        print(f"1단계에서 {len(step1_tab_data)}개의 탭을 찾았습니다.")

        for i, tab_info in enumerate(step1_tab_data):
            tab_id = tab_info['id']
            tab_name = tab_info['name']

            print(f"\n[1단계] '{tab_name}' 탭 클릭 시도 (ID: {tab_id}, {i + 1}/{len(step1_tab_data)})")

            current_tab_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f"//li[@id='{tab_id}']/a"))
            )
            current_tab_link.click()

            time.sleep(3)  # 클릭 후 2단계 내용 업데이트 대기

            crawl_level2_and_extract_data(driver, tab_name)

        print("\n--- 1단계: 구분 선택 순회 완료 ---")

    except TimeoutException as e:
        print(f"타임아웃 발생: {e}")
    except NoSuchElementException as e:
        print(f"요소를 찾을 수 없음: {e}")
    except Exception as e:
        print(f"예상치 못한 오류 발생: {e}")
    finally:
        if driver:
            driver.quit()
            print("브라우저가 닫혔습니다.")


if __name__ == "__main__":
    target_url = "https://www.mggeneralins.com/PB031210DM.scp?menuId=MN0803006"
    crawl_website(target_url)
