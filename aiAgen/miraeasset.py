# 미래에셋생명 상품 /판매 중단/DB확인
from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import traceback
import os
import sys
from datetime import datetime  # datetime 모듈 추가
from selenium.common.exceptions import NoAlertPresentException  # NoAlertPresentException import 추가

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

DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads", "miraeasset")  # 다운로드 폴더명 구체화
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

request_url = "https://life.miraeasset.com/micro/cmmnFileDown.do"


def handle_alert(driver):
    try:
        alert = driver.switch_to.alert
        print(f"알림창 감지: {alert.text}")
        alert.accept()  # 알림창 확인 (OK)
        print("알림창 닫기 완료.")
        return True
    except NoAlertPresentException:
        return False


def get_miraeasset_product_info():
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless') # 헤드리스 모드 사용 시 주석 해제

    # 다운로드 디렉토리 설정 추가
    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,  # 다운로드 프롬프트 비활성화
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True  # PDF를 브라우저 내에서 열지 않고 바로 다운로드
    }
    options.add_experimental_option(
        "prefs", {
            **prefs,  # 기존 prefs 설정을 유지하면서
            "profile.content_settings.exceptions.automatic_downloads.*,*.": {
                "setting": 1  # 1은 허용 (Allow), 2는 차단 (Block)
            }
        }
    )
    options.add_experimental_option("prefs", prefs)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(60)

    url = "https://life.miraeasset.com/micro/disclosure/product/PC-HO-080301-000000.do"
    products_data = []

    try:
        driver.get(url)
        print(f"페이지 접속 완료: {url}")
        time.sleep(3)
        # handle_alert(driver)  # 페이지 로드 후 알림창 처리 (사용자 피드백에 따라 제거)

        # "더보기" 버튼 로직
        more_button_selector = "div#btn-div > button#selectAddList"
        more_button_container_selector = "div#btn-div"

        while True:
            try:
                more_button_container = driver.find_element(By.CSS_SELECTOR, more_button_container_selector)
                if "display: none" in more_button_container.get_attribute("style"):
                    print("'더보기' 버튼 컨테이너가 숨겨져 있어 로드를 완료합니다.")
                    break

                more_button = WebDriverWait(driver, 7).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, more_button_selector))
                )
                button_text = more_button.text.strip() if more_button.text else "더보기"  # 버튼 텍스트 없을 수 있음
                print(f"'{button_text}' 버튼 클릭 시도...")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", more_button)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", more_button)
                # handle_alert(driver)  # 버튼 클릭 후 알림창 처리 (사용자 피드백에 따라 제거)
                time.sleep(2.5)  # 데이터 로드 대기
            except Exception as e_click:
                print(f"'더보기' 버튼 처리 중 예외 발생 또는 더 이상 없음: {e_click}")
                break

        print("모든 정보 로드 시도 완료. 데이터 추출 시작...")
        time.sleep(3)

        table_body_selector = "table#tbl01 > tbody#tbl_contents"
        rows = driver.find_elements(By.CSS_SELECTOR, f"{table_body_selector} > tr")
        print(f"총 {len(rows)}개의 행을 찾았습니다.")

        current_product_name = "N/A"
        last_valid_sales_period = "N/A"  # 이전 행의 유효한 판매기간을 저장

        for i, row in enumerate(rows):
            th_cells = row.find_elements(By.TAG_NAME, "th")
            td_cells = row.find_elements(By.TAG_NAME, "td")

            # 상품명 추출 (th에 rowspan으로 존재)
            if th_cells and th_cells[0].get_attribute("rowspan"):
                current_product_name = th_cells[0].text.strip()

            sales_period = "N/A"
            summary_links_idx = -1
            terms_links_idx = -1
            bm_links_idx = -1

            if td_cells:
                first_td_text = td_cells[0].text.strip()

                # td_cells[0]이 '상태' 컬럼인지 판단
                is_status_td_first = False
                if "판매중" in first_td_text or "판매종료" in first_td_text:
                    is_status_td_first = True

                if is_status_td_first:
                    # td_cells[0]이 상태 컬럼인 경우, 판매기간은 td_cells[1]
                    if len(td_cells) > 1:
                        raw_sales_period = td_cells[1].text.strip()
                        if "판매중" in raw_sales_period or "판매종료" in raw_sales_period:
                            sales_period = ""  # 판매기간에 상태 텍스트가 또 있다면 빈 문자열
                        else:
                            sales_period = raw_sales_period
                    else:
                        sales_period = ""  # 판매기간 td가 없는 경우
                    summary_links_idx = 2  # 요약서는 td_cells[2]
                else:
                    # td_cells[0]이 판매기간 컬럼인 경우 (상태 컬럼이 rowspan으로 생략된 경우)
                    sales_period = first_td_text
                    summary_links_idx = 1  # 요약서는 td_cells[1]

                # 판매기간에 "판매중" 또는 "판매종료" 텍스트가 들어가지 않도록 최종 필터링
                if "판매중" in sales_period or "판매종료" in sales_period:
                    sales_period = ""

                # 현재 행에서 유효한 sales_period를 찾았다면 업데이트
                if sales_period != "":
                    last_valid_sales_period = sales_period
                else:
                    # 현재 행에서 sales_period를 찾지 못했다면, 이전 유효값 사용
                    sales_period = last_valid_sales_period

                # 나머지 링크 인덱스 설정
                terms_links_idx = summary_links_idx + 1
                bm_links_idx = terms_links_idx + 1

                # 상품요약서 (summary_links_idx)
                summary_link = "N/A"
                if len(td_cells) > summary_links_idx:
                    summary_links = td_cells[summary_links_idx].find_elements(By.TAG_NAME, "a")
                    summary_link = summary_links[0].get_attribute('href') if summary_links else "N/A"

                # 약관 (terms_links_idx)
                terms_link = "N/A"
                if len(td_cells) > terms_links_idx:
                    terms_links_elements = td_cells[terms_links_idx].find_elements(By.TAG_NAME, "a")
                    terms_link_list = [link.get_attribute('href') for link in terms_links_elements if link.is_displayed()]
                    terms_link = ", ".join(terms_link_list) if terms_link_list else "N/A"

                # 사업방법서 (bm_links_idx)
                business_manual_link = "N/A"
                if len(td_cells) > bm_links_idx:
                    bm_links = td_cells[bm_links_idx].find_elements(By.TAG_NAME, "a")
                    business_manual_link = bm_links[0].get_attribute('href') if bm_links else "N/A"

                # PDF 링크 추출 로직도 인덱스 조정 필요
                pdf_extractor = PdfLinkExtractor(driver, DOWNLOAD_DIR, verify_url_liveness=True,
                                                 url_filter_pattern="cmmnFileDown.do")
                extracted_summary_pdf_link = "N/A"
                if summary_link and summary_link != "N/A" and summary_links:
                    summary_xpath = f"//table[@id='tbl01']/tbody[@id='tbl_contents']/tr[{i + 1}]/td[{summary_links_idx + 1}]/a[1]"
                    summary_payload = pdf_extractor.get_pdf_download_payload(summary_xpath, 20)
                    if summary_payload:
                        extracted_summary_pdf_link = request_url + "?" + summary_payload
                    else:
                        print("페이로드가 없습니다")
                    handle_alert(driver)  # PDF 링크 클릭 후 알림창 처리

                extracted_terms_pdf_links = []
                if terms_link and terms_link != "N/A" and terms_links_elements:
                    for k, link_element in enumerate(terms_links_elements):
                        if link_element.is_displayed():
                            term_xpath = f"//table[@id='tbl01']/tbody[@id='tbl_contents']/tr[{i + 1}]/td[{terms_links_idx + 1}]/a[{k + 1}]"
                            terms_payload = pdf_extractor.get_pdf_download_payload(term_xpath, 20)
                            if terms_payload:
                                terms_payload_link = request_url + "?" + terms_payload
                            else:
                                print("페이로드가 없습니다")
                            extracted_terms_pdf_links.append(terms_payload_link)
                            handle_alert(driver)  # PDF 링크 클릭 후 알림창 처리
                extracted_terms_pdf_link = (
                    ", ".join([pdf_link for pdf_link in extracted_terms_pdf_links if pdf_link is not None and pdf_link != "N/A" and pdf_link.strip() != ""])
                    if extracted_terms_pdf_links else "N/A"
                )

                extracted_business_manual_pdf_link = "N/A"
                if business_manual_link and business_manual_link != "N/A" and bm_links:
                    bm_xpath = f"//table[@id='tbl01']/tbody[@id='tbl_contents']/tr[{i + 1}]/td[{bm_links_idx + 1}]/a[1]"
                    business_manual_payload = pdf_extractor.get_pdf_download_payload(bm_xpath, 20)
                    if business_manual_payload:
                        extracted_business_manual_pdf_link = request_url + "?" + business_manual_payload
                    else:
                        print("페이로드가 없습니다")
                    handle_alert(driver)  # PDF 링크 클릭 후 알림창 처리

                # 판매기간 정보가 있는 행만 유효한 데이터로 간주 (상품명만 있는 행 제외)
                # sales_period가 빈 문자열이거나 N/A가 아닌 경우에만 저장
                if sales_period != "N/A" and sales_period.strip() != "":
                    product_data_row = {
                        "product_name": current_product_name,
                        "sales_period": sales_period,
                        "summary_link": summary_link,
                        "terms_link": terms_link,
                        "business_manual_link": business_manual_link,
                        "extracted_summary_pdf_link": extracted_summary_pdf_link,
                        "extracted_terms_pdf_link": extracted_terms_pdf_link,
                        "extracted_business_manual_pdf_link": extracted_business_manual_pdf_link
                    }
                    # 추출된 PDF 링크가 유효한 경우에만 products_data에 추가
                    if (extracted_summary_pdf_link not in ["N/A", None, ""]
                        or extracted_terms_pdf_link not in ["N/A", None, ""]
                            or extracted_business_manual_pdf_link not in ["N/A", None, ""]):
                        products_data.append(product_data_row)
            else:
                # td_cells가 없는 행 (rowspan으로 인해 모든 td가 생략된 행) 처리
                # 이 경우, 이전 행의 current_product_name과 last_valid_sales_period를 사용하여 데이터 생성
                # 링크 정보는 N/A로 처리
                if current_product_name != "N/A" and last_valid_sales_period != "N/A":
                    # 이 경우 추출된 PDF 링크는 N/A이므로, DB에 저장하지 않음
                    pass  # 이 부분은 이미 링크가 N/A이므로 저장하지 않음
            print(product_data_row)

        if not products_data:
            print("데이터를 찾지 못했습니다. HTML 구조 및 선택자를 다시 확인해야 합니다.")

    except Exception as e_main:
        print(f"스크래핑 중 주요 오류 발생: {e_main}")
        traceback.print_exc()
    finally:
        print("스크래핑 시도 종료. 브라우저를 닫습니다.")
        if 'driver' in locals() and driver is not None:
            driver.quit()

    return products_data


if __name__ == '__main__':
    print("미래에셋생명 상품 정보 스크래핑 시작...")
    product_list = get_miraeasset_product_info()

    if product_list:
        try:
            if DatabaseManager:
                # with 문을 사용하여 DatabaseManager 인스턴스 생성 및 관리
                with DatabaseManager('miraeasset_web_data.db') as db_manager:  # DB 파일명 확인 필요
                    all_structured_rows = []  # 모든 데이터를 한 번에 저장하기 위한 리스트

                    for idx, info in enumerate(product_list):
                        print(f"\n--- 상품 {idx + 1} ---")
                        print(f"상품명: {info.get('product_name', 'N/A')}")
                        print(f"판매기간: {info.get('sales_period', 'N/A')}")
                        print(f"상품요약서 (원본): {info.get('summary_link', 'N/A')}")
                        print(f"상품요약서 (추출 PDF): {info.get('extracted_summary_pdf_link', 'N/A')}")
                        print(f"약관 (원본): {info.get('terms_link', 'N/A')}")
                        print(f"약관 (추출 PDF): {info.get('extracted_terms_pdf_link', 'N/A')}")
                        print(f"사업방법서 (원본): {info.get('business_manual_link', 'N/A')}")
                        print(f"사업방법서 (추출 PDF): {info.get('extracted_business_manual_pdf_link', 'N/A')}")

                        company_name = "미래에셋생명"
                        product_name = info.get('product_name', 'N/A')
                        sales_period = info.get('sales_period', 'N/A')
                        product_code = None  # product_code는 null
                        scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 현재 시간 추가

                        # 상품요약서 저장
                        summary_pdf_link = info.get('extracted_summary_pdf_link', 'N/A')
                        if summary_pdf_link != "N/A":
                            all_structured_rows.append((company_name, product_name, product_code, "상품요약서",
                                                       sales_period, scraped_at, summary_pdf_link))

                        # 약관 저장
                        terms_pdf_link = info.get('extracted_terms_pdf_link', 'N/A')
                        if terms_pdf_link != "N/A":
                            for link in terms_pdf_link.split(', '):
                                if link.strip():
                                    all_structured_rows.append((company_name, product_name, product_code,
                                                               "약관", sales_period, scraped_at, link.strip()))

                        # 사업방법서 저장
                        business_manual_pdf_link = info.get('extracted_business_manual_pdf_link', 'N/A')
                        if business_manual_pdf_link != "N/A":
                            all_structured_rows.append((company_name, product_name, product_code, "사업방법서",
                                                       sales_period, scraped_at, business_manual_pdf_link))

                    # 모든 데이터를 한 번에 저장
                    if all_structured_rows:
                        db_manager.save_data(all_structured_rows)
                    else:
                        print("저장할 데이터가 없습니다.")

            else:
                print("DatabaseManager를 사용할 수 없습니다. DB 저장을 건너뜝니다.")

        except Exception as e:
            print(f"DB 저장 중 오류 발생: {e}")
            traceback.print_exc()
        # finally 블록은 with 문 사용 시 필요 없음 (자동으로 커밋 및 종료)
    else:
        print("최종 추출된 상품 정보가 없습니다.")
