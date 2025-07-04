# im라이프/판매중단페이지
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from seleniumwire import webdriver
from webdriver_manager.chrome import ChromeDriverManager

import os
import sys
from datetime import datetime
import shutil  # 기존 다운로드 폴더 삭제를 위한 shutil 임포트 (테스트용)

# 프로젝트 루트 경로 설정 (스크립트 위치에서 두 단계 위)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from neoali.pdf_link_scraper import PdfLinkExtractor
    from neoali.DB_save import DatabaseManager
except ImportError as e:
    PdfLinkExtractor = None
    DatabaseManager = None
    print(f"경고: 모듈 임포트 실패 ({e}). 일부 기능이 비활성화될 수 있습니다.")

# PDF 다운로드 디렉토리 (스크립트 파일 위치 기준)
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads", "imlifeins")

# 다운로드 디렉토리 생성 (기존에 있다면 삭제 후 재생성 - 테스트용)
if os.path.exists(DOWNLOAD_DIR):
    try:
        shutil.rmtree(DOWNLOAD_DIR)
        print(f"기존 다운로드 디렉토리 삭제: {DOWNLOAD_DIR}")
    except OSError as e:
        print(f"오류: 기존 다운로드 디렉토리 삭제 실패 ({DOWNLOAD_DIR}): {e}. 권한 문제를 확인하세요.")
        # 권한 문제 시 스크립트를 중지하거나 다른 조치를 취할 수 있습니다.
        # sys.exit(1) # 예시: 오류 시 스크립트 종료

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)
    print(f"다운로드 디렉토리 생성: {DOWNLOAD_DIR}")


def get_product_info(url):
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev_shm_usage")

    # Chrome이 PDF를 자동으로 다운로드하도록 설정
    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True
    }
    options.add_experimental_option("prefs", prefs)

    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        pdf_extractor = None
        if PdfLinkExtractor:
            pdf_extractor = PdfLinkExtractor(driver, download_directory=DOWNLOAD_DIR, verify_url_liveness=False)

        product_list = []
        tables = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "table.colTbl tbody"))
        )

        for table_idx, table in enumerate(tables):
            last_product_name = ""
            rows = table.find_elements(By.TAG_NAME, "tr")
            for row_idx, row in enumerate(rows):
                cols = row.find_elements(By.TAG_NAME, "td")

                if not cols:
                    continue

                current_product_name = ""
                sales_start_date = ""
                sales_end_date = ""
                summary_link = ""
                business_method_link = ""
                terms_link = ""

                product_name_element_found = False
                for col in cols:
                    if "al" in col.get_attribute("class"):
                        current_product_name = col.text.strip()
                        last_product_name = current_product_name
                        product_name_element_found = True
                        break

                if not product_name_element_found:
                    current_product_name = last_product_name

                start_index_for_data = 0
                if product_name_element_found:
                    for i, col in enumerate(cols):
                        if "al" in col.get_attribute("class"):
                            start_index_for_data = i + 1
                            break

                if start_index_for_data < len(cols):
                    sales_start_date = cols[start_index_for_data].text.strip()

                if start_index_for_data + 1 < len(cols):
                    sales_end_date = cols[start_index_for_data + 1].text.strip()

                sales_period = f"{sales_start_date} ~ {sales_end_date}"

                if pdf_extractor:
                    # 상품요약서 링크
                    if start_index_for_data + 2 < len(cols):
                        try:
                            summary_a_tag = cols[start_index_for_data + 2].find_element(By.TAG_NAME, "a")
                            summary_link_href = summary_a_tag.get_attribute("href")
                            if summary_link_href and "javascript" not in summary_link_href:
                                summary_link = summary_link_href
                            else:
                                # WebElement의 XPath를 동적으로 가져오는 JavaScript 함수
                                get_xpath_script = """
                                function getXPath(element) {
                                    if (element.id !== '') {
                                        return '//*[@id="' + element.id + '"]';
                                    }
                                    if (element === document.body) {
                                        return '/html/body';
                                    }
                                    var ix = 0;
                                    var siblings = element.parentNode.childNodes;
                                    for (var i = 0; i < siblings.length; i++) {
                                        var sibling = siblings[i];
                                        if (sibling === element) {
                                            return getXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                                        }
                                        if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
                                            ix++;
                                        }
                                    }
                                }
                                return getXPath(arguments[0]);
                                """
                                summary_xpath = driver.execute_script(get_xpath_script, summary_a_tag)
                                extracted_link = pdf_extractor.click_and_get_download_link(summary_xpath)
                                if extracted_link:
                                    summary_link = extracted_link
                        except NoSuchElementException:
                            pass

                    # 사업방법서 링크
                    if start_index_for_data + 3 < len(cols):
                        try:
                            business_method_a_tag = cols[start_index_for_data + 3].find_element(By.TAG_NAME, "a")
                            business_method_link_href = business_method_a_tag.get_attribute("href")
                            if business_method_link_href and "javascript" not in business_method_link_href:
                                business_method_link = business_method_link_href
                            else:
                                get_xpath_script = """
                                function getXPath(element) {
                                    if (element.id !== '') {
                                        return '//*[@id="' + element.id + '"]';
                                    }
                                    if (element === document.body) {
                                        return '/html/body';
                                    }
                                    var ix = 0;
                                    var siblings = element.parentNode.childNodes;
                                    for (var i = 0; i < siblings.length; i++) {
                                        var sibling = siblings[i];
                                        if (sibling === element) {
                                            return getXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                                        }
                                        if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
                                            ix++;
                                        }
                                    }
                                }
                                return getXPath(arguments[0]);
                                """
                                business_method_xpath = driver.execute_script(get_xpath_script, business_method_a_tag)
                                extracted_link = pdf_extractor.click_and_get_download_link(business_method_xpath)
                                if extracted_link:
                                    business_method_link = extracted_link
                        except NoSuchElementException:
                            pass

                    # 보험약관 링크
                    if start_index_for_data + 4 < len(cols):
                        try:
                            terms_a_tag = cols[start_index_for_data + 4].find_element(By.TAG_NAME, "a")
                            terms_link_href = terms_a_tag.get_attribute("href")
                            if terms_link_href and "javascript" not in terms_link_href:
                                terms_link = terms_link_href
                            else:
                                get_xpath_script = """
                                function getXPath(element) {
                                    if (element.id !== '') {
                                        return '//*[@id="' + element.id + '"]';
                                    }
                                    if (element === document.body) {
                                        return '/html/body';
                                    }
                                    var ix = 0;
                                    var siblings = element.parentNode.childNodes;
                                    for (var i = 0; i < siblings.length; i++) {
                                        var sibling = siblings[i];
                                        if (sibling === element) {
                                            return getXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                                        }
                                        if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
                                            ix++;
                                        }
                                    }
                                }
                                return getXPath(arguments[0]);
                                """
                                terms_xpath = driver.execute_script(get_xpath_script, terms_a_tag)
                                extracted_link = pdf_extractor.click_and_get_download_link(terms_xpath)
                                if extracted_link:
                                    terms_link = extracted_link
                        except NoSuchElementException:
                            pass

                product_list.append({
                    "상품명": current_product_name,
                    "판매기간": sales_period,
                    "상품요약서": summary_link,
                    "사업방법서": business_method_link,
                    "약관": terms_link
                })

        # DB에 저장
        if DatabaseManager:
            # DB 파일 경로를 project_root로 지정
            db_name = os.path.join(project_root, "imlifeins_web_data.db")
            print(f"DB 파일 저장 경로: {db_name}")  # DB 저장 경로 확인용 출력

            with DatabaseManager(db_name=db_name) as db_manager:
                structured_rows = []
                scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                company_name = "IM라이프"

                for product in product_list:
                    product_name = product["상품명"]
                    sales_period = product["판매기간"]

                    # 링크가 있는 경우에만 DB에 저장
                    if product["상품요약서"]:
                        structured_rows.append((
                            company_name, product_name, None,
                            "상품요약서", sales_period, scraped_at, product["상품요약서"]
                        ))

                    if product["사업방법서"]:
                        structured_rows.append((
                            company_name, product_name, None,
                            "사업방법서", sales_period, scraped_at, product["사업방법서"]
                        ))

                    if product["약관"]:
                        structured_rows.append((
                            company_name, product_name, None,
                            "약관", sales_period, scraped_at, product["약관"]
                        ))

                if structured_rows:
                    db_manager.save_data(structured_rows)
                    print(f"총 {len(structured_rows)}개의 데이터가 DB에 저장되었습니다.")
                else:
                    print("DB에 저장할 데이터가 없습니다.")

        return product_list

    except TimeoutException:
        print("페이지 로드 시간 초과 오류가 발생했습니다.")
        return None
    except Exception as e:
        print(f"스크래핑 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if driver:
            driver.quit()
            print("WebDriver가 종료되었습니다.")


if __name__ == "__main__":
    url = "https://www.imlifeins.co.kr/BA/BA_A020.do"
    print(f"IM라이프 상품 정보 스크래핑 시작: {url}")
    product_data = get_product_info(url)
    if product_data:
        print("\n--- 스크래핑된 상품 요약 정보 ---")
        for product in product_data:
            print(f"  상품명: {product['상품명']}")
            print(f"  판매기간: {product['판매기간']}")
            if product['상품요약서']:
                print(f"    상품요약서 링크 확인: {product['상품요약서']}")
            if product['사업방법서']:
                print(f"    사업방법서 링크 확인: {product['사업방법서']}")
            if product['약관']:
                print(f"    약관 링크 확인: {product['약관']}")
            print("-----------------")
    else:
        print("상품 정보를 가져오지 못했습니다. 오류 메시지를 확인하세요.")
