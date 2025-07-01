# 미래에셋생명 상품 /판매 중단/DB확인
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import traceback
import os
import sys

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


def get_miraeasset_product_info():
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(60)

    url = "https://life.miraeasset.com/micro/disclosure/product/PC-HO-080301-000000.do"
    products_data = []

    try:
        driver.get(url)
        print(f"페이지 접속 완료: {url}")
        time.sleep(3)

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

        for i, row in enumerate(rows):
            th_cells = row.find_elements(By.TAG_NAME, "th")
            td_cells = row.find_elements(By.TAG_NAME, "td")

            # 상품명 추출 (th에 rowspan으로 존재)
            if th_cells and th_cells[0].get_attribute("rowspan"):
                current_product_name = th_cells[0].text.strip()

            # td_cells[0] = 판매기간
            # td_cells[1] = 상품요약서
            # td_cells[2] = 약관
            # td_cells[3] = 사업방법서
            # (사용자 설명: 테이블상 3번째부터 판매기간... -> th가 첫번째 열, td[0]이 두번째 열(판매기간)일 가능성)
            # td_cells의 실제 개수와 내용을 기준으로 인덱싱해야 함.
            # 제공된 HTML 예시에서는 th가 첫번째 열, 그 다음 td들이 데이터.
            # 따라서 td_cells[0]이 판매기간, td_cells[1]이 요약서...

            if td_cells:  # 데이터 td가 있는 경우에만 처리
                sales_period = "N/A"
                summary_link = "N/A"
                terms_link = "N/A"
                business_manual_link = "N/A"

                # 판매기간 (첫 번째 td)
                if len(td_cells) > 0:
                    sales_period = td_cells[0].text.strip()

                # 상품요약서 (두 번째 td)
                if len(td_cells) > 1:
                    summary_links = td_cells[1].find_elements(By.TAG_NAME, "a")
                    summary_link = summary_links[0].get_attribute('href') if summary_links else "N/A"

                # 약관 (세 번째 td)
                if len(td_cells) > 2:
                    terms_links_elements = td_cells[2].find_elements(By.TAG_NAME, "a")
                    terms_link_list = [link.get_attribute('href') for link in terms_links_elements if link.is_displayed()]
                    terms_link = ", ".join(terms_link_list) if terms_link_list else "N/A"

                # 사업방법서 (네 번째 td)
                if len(td_cells) > 3:
                    bm_links = td_cells[3].find_elements(By.TAG_NAME, "a")
                    business_manual_link = bm_links[0].get_attribute('href') if bm_links else "N/A"

                # 판매기간 정보가 있는 행만 유효한 데이터로 간주 (상품명만 있는 행 제외)
                if sales_period != "N/A" and sales_period.strip() != "":
                    # PDF 링크 추출
                    pdf_extractor = PdfLinkExtractor()
                    extracted_summary_pdf_link = pdf_extractor.extract_pdf_link(summary_link) if summary_link != "N/A" else "N/A"
                    extracted_terms_pdf_links = []
                    if terms_link != "N/A":
                        for link in terms_link.split(', '):
                            extracted_terms_pdf_links.append(pdf_extractor.extract_pdf_link(link.strip()))
                    extracted_terms_pdf_link = ", ".join(extracted_terms_pdf_links) if extracted_terms_pdf_links else "N/A"
                    extracted_business_manual_pdf_link = pdf_extractor.extract_pdf_link(
                        business_manual_link) if business_manual_link != "N/A" else "N/A"

                    products_data.append({
                        "product_name": current_product_name,
                        "sales_period": sales_period,
                        "summary_link": summary_link,
                        "terms_link": terms_link,
                        "business_manual_link": business_manual_link,
                        "extracted_summary_pdf_link": extracted_summary_pdf_link,
                        "extracted_terms_pdf_link": extracted_terms_pdf_link,
                        "extracted_business_manual_pdf_link": extracted_business_manual_pdf_link
                    })
            # else:
                # th만 있고 td가 없는 행 (예: 상품명만 있는 첫 행의 일부)은 이미 current_product_name만 업데이트하고 넘어감.
                # print(f"행 {i}: td 셀이 없습니다.")

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
        db_manager = None
        try:
            if DatabaseManager:
                db_manager = DatabaseManager('aig_ins_web_data.db')  # DB 파일명 확인 필요
                db_manager.create_table()
            else:
                print("DatabaseManager를 사용할 수 없습니다. DB 저장을 건너뜝니다.")

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

                if db_manager:
                    company_name = "미래에셋생명"
                    product_name = info.get('product_name', 'N/A')
                    sales_period = info.get('sales_period', 'N/A')
                    product_code = None  # product_code는 null

                    # 상품요약서 저장
                    summary_pdf_link = info.get('extracted_summary_pdf_link', 'N/A')
                    if summary_pdf_link != "N/A":
                        db_manager.save_data(company_name, product_name, product_code, "상품요약서", sales_period, summary_pdf_link)

                    # 약관 저장
                    terms_pdf_link = info.get('extracted_terms_pdf_link', 'N/A')
                    if terms_pdf_link != "N/A":
                        # 약관 링크가 여러 개일 수 있으므로 분리하여 저장
                        for link in terms_pdf_link.split(', '):
                            if link.strip():
                                db_manager.save_data(company_name, product_name, product_code, "약관", sales_period, link.strip())

                    # 사업방법서 저장
                    business_manual_pdf_link = info.get('extracted_business_manual_pdf_link', 'N/A')
                    if business_manual_pdf_link != "N/A":
                        db_manager.save_data(company_name, product_name, product_code, "사업방법서", sales_period, business_manual_pdf_link)
        except Exception as e:
            print(f"DB 저장 중 오류 발생: {e}")
            traceback.print_exc()
        finally:
            if db_manager:
                db_manager.close()
    else:
        print("최종 추출된 상품 정보가 없습니다.")
