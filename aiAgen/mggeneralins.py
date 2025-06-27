# MG손해보험/판매중지페이지/db확인
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from seleniumwire import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import sys
from datetime import datetime

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from neoali.pdf_link_scraper import PdfLinkExtractor
    from neoali.DB_save import DatabaseManager  # DatabaseManager import 추가
except ImportError as e:
    PdfLinkExtractor = None
    DatabaseManager = None  # DatabaseManager 초기화 추가
    print(f"경고: 모듈 임포트 실패 ({e}). 일부 기능이 비활성화될 수 있습니다.")

DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads", "mggeneralins")
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)


def setup_driver():
    """Selenium WebDriver 인스턴스를 설정하고 반환합니다."""
    chrome_options = Options()
    # chrome_options.add_argument("--headless") # GUI 없이 백그라운드에서 실행하려면 주석 해제
    # chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--allow-running-insecure-content")
    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
        "profile.default_content_setting_values.automatic_downloads": 1
    }
    chrome_options.add_experimental_option("prefs", prefs)
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def handle_modal_if_present(driver):
    """
    모달창이 나타나면 확인 버튼을 클릭하여 닫는 함수입니다.
    모달창이 없으면 바로 반환합니다.
    """
    try:
        WebDriverWait(driver, 3).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "SAlert-message"))
        )
        ok_button = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".SAlert-button .SAlert-BtnConfirm"))
        )
        ok_button.click()
        WebDriverWait(driver, 5).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, "SAlert-Contents"))
        )
        return True
    except TimeoutException:
        return False
    except Exception as e:
        print(f"      [오류] 모달 처리 중 예상치 못한 오류 발생: {e}")
        return False


def extract_level3_data(driver, category_name_step1, category_name_step2, all_extracted_data):
    """
    3단계 정보를 추출하는 함수입니다.
    제품명, 판매기간, 그리고 각 다운로드 링크의 JavaScript 함수 인자 (ID, TYPE)를 추출합니다.
    추출된 데이터를 all_extracted_data 리스트에 추가합니다.
    """
    try:
        WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".pb_step03"))
        )

        product_ul_elements = driver.find_elements(By.CSS_SELECTOR, ".pb_step03 > ul")

        if not product_ul_elements:
            print(f"      [성공] 1단계: '{category_name_step1}', 2단계: '{category_name_step2}' -> 제품 데이터 없음.")
            return

        for i, product_ul in enumerate(product_ul_elements):
            try:
                product_name_element = WebDriverWait(product_ul, 5).until(
                    EC.presence_of_element_located((By.TAG_NAME, "h5"))
                )
                product_name = product_name_element.text.strip()

                table = WebDriverWait(product_ul, 5).until(
                    EC.presence_of_element_located((By.TAG_NAME, "table"))
                )

                try:
                    sales_period = table.find_element(By.XPATH, ".//tbody/tr/td[1]").text.strip()
                except NoSuchElementException:
                    sales_period = "판매기간 없음"

                item_downloads = {
                    "상품요약서": None,
                    "약관": None,
                    "사업방법서": None
                }

                pdf_extractor = PdfLinkExtractor(driver, download_directory=DOWNLOAD_DIR)

                # 상품요약서 링크 처리 (테이블의 2번째 td)
                try:
                    summary_link_element = table.find_element(By.XPATH, ".//tbody/tr/td[2]/a")
                    xpath_script = """
                    function getXPath(element) {
                        if (element.id !== '') return '//*[@id=\"' + element.id + '\"]';
                        if (element === document.body) return '/html/' + element.tagName.toLowerCase();
                        var ix = 0;
                        var siblings = element.parentNode.childNodes;
                        for (var i = 0; i < siblings.length; i++) {
                            var sibling = siblings[i];
                            if (sibling === element) return getXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                            if (sibling.nodeType === 1 && sibling.tagName === element.tagName) ix++;
                        }
                    }
                    return getXPath(arguments[0]);
                    """
                    summary_link_xpath = driver.execute_script(xpath_script, summary_link_element)
                    pdf_path = pdf_extractor.click_and_get_download_link(summary_link_xpath)
                    if pdf_path:
                        item_downloads["상품요약서"] = pdf_path
                except NoSuchElementException:
                    pass

                # 약관 링크 처리 (테이블의 3번째 td)
                try:
                    terms_link_element = table.find_element(By.XPATH, ".//tbody/tr/td[3]/a")
                    xpath_script = """
                    function getXPath(element) {
                        if (element.id !== '') return '//*[@id=\"' + element.id + '\"]';
                        if (element === document.body) return '/html/' + element.tagName.toLowerCase();
                        var ix = 0;
                        var siblings = element.parentNode.childNodes;
                        for (var i = 0; i < siblings.length; i++) {
                            var sibling = siblings[i];
                            if (sibling === element) return getXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                            if (sibling.nodeType === 1 && sibling.tagName === element.tagName) ix++;
                        }
                    }
                    return getXPath(arguments[0]);
                    """
                    terms_link_xpath = driver.execute_script(xpath_script, terms_link_element)
                    pdf_path = pdf_extractor.click_and_get_download_link(terms_link_xpath)
                    if pdf_path:
                        item_downloads["약관"] = pdf_path
                except NoSuchElementException:
                    pass

                # 사업방법서 링크 처리 (테이블의 4번째 td)
                try:
                    biz_link_element = table.find_element(By.XPATH, ".//tbody/tr/td[4]/a")
                    xpath_script = """
                    function getXPath(element) {
                        if (element.id !== '') return '//*[@id=\"' + element.id + '\"]';
                        if (element === document.body) return '/html/' + element.tagName.toLowerCase();
                        var ix = 0;
                        var siblings = element.parentNode.childNodes;
                        for (var i = 0; i < siblings.length; i++) {
                            var sibling = siblings[i];
                            if (sibling === element) return getXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                            if (sibling.nodeType === 1 && sibling.tagName === element.tagName) ix++;
                        }
                    }
                    return getXPath(arguments[0]);
                    """
                    biz_link_xpath = driver.execute_script(xpath_script, biz_link_element)
                    pdf_path = pdf_extractor.click_and_get_download_link(biz_link_xpath)
                    if pdf_path:
                        item_downloads["사업방법서"] = pdf_path
                except NoSuchElementException:
                    pass

                all_extracted_data.append({
                    "1단계 카테고리": category_name_step1,
                    "2단계 카테고리": category_name_step2,
                    "제품명": product_name,
                    "판매기간": sales_period,
                    "다운로드_링크": item_downloads
                })
                print(f"      [추출 성공] 제품: '{product_name}'")

            except TimeoutException as e:
                print(f"      [오류] 제품 항목 {i + 1} 로드 타임아웃: {e}")
            except NoSuchElementException as e:
                print(f"      [오류] 제품 항목 {i + 1} 필수 요소 찾을 수 없음: {e}")
            except Exception as e:
                print(f"      [오류] 제품 항목 {i + 1} 처리 중 예상치 못한 오류 발생: {e}")

    except TimeoutException:
        print(f"      [오류] 3단계 컨테이너 로드 타임아웃 (1단계: '{category_name_step1}', 2단계: '{category_name_step2}')")
    except Exception as e:
        print(f"      [오류] 3단계 처리 중 예상치 못한 오류 발생: {e}")


def crawl_level2_and_extract_data(driver, parent_category_name, all_extracted_data):
    """
    2단계 탐색 및 3단계 정보 추출을 수행하는 함수입니다.
    """
    tab_wrap_map = {
        '장기보험': 'tab01_wrap',
        '자동차보험': 'tab02_wrap',
        '일반보험': 'tab03_wrap'
    }

    target_tab_wrap_class = tab_wrap_map.get(parent_category_name)

    if not target_tab_wrap_class:
        print(f"  [오류] 알 수 없는 1단계 카테고리 '{parent_category_name}'. 2단계 탭 래퍼를 찾을 수 없습니다.")
        return

    try:
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
            print(f"  [성공] 1단계: '{parent_category_name}' -> 2단계 항목 없음.")
            return

        for i, item_info in enumerate(level2_item_data):
            item_name = item_info['text']
            item_id = item_info['id']

            print(f"\n  [클릭] 1단계: '{parent_category_name}', 2단계: '{item_name}' 클릭 시도 중...")

            current_item_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f"//div[contains(@class, '{target_tab_wrap_class}')]//li[@id='{item_id}']/a"))
            )
            current_item_link.click()

            time.sleep(1)
            modal_handled = handle_modal_if_present(driver)

            if modal_handled:
                print(f"  [처리 완료] 1단계: '{parent_category_name}', 2단계: '{item_name}' -> 모달창 처리 완료. 제품 데이터 없음.")
                continue
            else:
                time.sleep(2)
                extract_level3_data(driver, parent_category_name, item_name, all_extracted_data)

    except TimeoutException as e:
        print(f"  [오류] 2단계 '{parent_category_name}' 탐색 타임아웃: {e}")
    except NoSuchElementException as e:
        print(f"  [오류] 2단계 '{parent_category_name}'에서 요소를 찾을 수 없음: {e}")
    except Exception as e:
        print(f"  [오류] 2단계 '{parent_category_name}' 처리 중 예상치 못한 오류 발생: {e}")


def crawl_website(url):
    driver = None
    all_extracted_data = []
    try:
        driver = setup_driver()
        driver.get(url)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".pb_step01"))
        )
        print(f"[성공] 페이지 로드 완료: {url}")

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
            print("[오류] 1단계 탭을 찾을 수 없습니다. 셀렉터를 확인해주세요.")
            return

        for i, tab_info in enumerate(step1_tab_data):
            tab_id = tab_info['id']
            tab_name = tab_info['name']

            print(f"\n[클릭] 1단계: '{tab_name}' 탭 클릭 시도 중...")

            current_tab_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f"//li[@id='{tab_id}']/a"))
            )
            current_tab_link.click()

            time.sleep(3)

            crawl_level2_and_extract_data(driver, tab_name, all_extracted_data)

        print("\n--- 전체 크롤링 완료 ---")
        if all_extracted_data:
            print(f"\n--- 최종 추출된 전체 데이터 ({len(all_extracted_data)}개 제품) ---")
            if DatabaseManager:
                db_name = "mggeneralins_web_data.db"
                structured_rows = []
                scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                company_name = "MG손해보험"

                for item in all_extracted_data:
                    product_name = item["제품명"]
                    sales_period = item["판매기간"]
                    product_code = None  # 사용자 요청에 따라 None으로 설정

                    for doc_type, link in item["다운로드_링크"].items():
                        if link:
                            structured_rows.append((
                                company_name,
                                product_name,
                                product_code,
                                doc_type,
                                sales_period,
                                scraped_at,
                                link
                            ))
                if structured_rows:
                    with DatabaseManager(db_name=db_name) as db_manager:
                        db_manager.save_data(structured_rows)
                else:
                    print("데이터베이스에 저장할 구조화된 데이터가 없습니다.")
            else:
                print("DatabaseManager를 임포트할 수 없어 DB 저장을 건너뜁니다.")
        else:
            print("\n추출된 제품 데이터가 없습니다.")

    except TimeoutException as e:
        print(f"[오류] 전체 크롤링 타임아웃 발생: {e}")
    except NoSuchElementException as e:
        print(f"[오류] 전체 크롤링 중 요소를 찾을 수 없음: {e}")
    except Exception as e:
        print(f"[오류] 예상치 못한 오류 발생: {e}")
    finally:
        if driver:
            driver.quit()
            print("브라우저가 닫혔습니다.")


if __name__ == "__main__":
    target_url = "https://www.mggeneralins.com/PB031210DM.scp?menuId=MN0803006"
    crawl_website(target_url)
