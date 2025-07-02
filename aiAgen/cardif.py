# 카디프생명/판매중지페이지/수정확인
#  https://www.cardif.co.kr/common/rest/fileDownloadFront.do?fileId=351349&atchFileDiv=DIS&frontBackDiv=Front
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import selenium.webdriver.support.ui
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import sys
from datetime import datetime
import json

# 프로젝트 루트 경로 설정 (기존과 동일)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# neoali 모듈 임포트
try:
    from neoali.pdf_link_scraper import PdfLinkExtractor
    from neoali.DB_save import DatabaseManager
except ImportError as e:
    PdfLinkExtractor = None
    DatabaseManager = None
    print(f"경고: 모듈 임포트 실패 ({e}). 일부 기능이 비활성화될 수 있습니다.")


def get_pdf_link_robustly(pdf_extractor, element_td):
    """
    <td> 요소에서 PDF 링크를 추출하는 헬퍼 함수.
    pdf_extractor를 사용하고, 실패 시 href를 직접 반환합니다.
    href가 'javascript:void(0);'이면 빈 문자열을 반환하여 DB 저장에서 제외합니다.
    """
    a_tag = element_td.find_elements(By.TAG_NAME, "a")
    if a_tag:
        link_element = a_tag[0]
        link_id = link_element.get_attribute("id")

        extracted_link = ""
        if link_id:  # ID가 있다면 PdfLinkExtractor 시도
            xpath_for_extractor = f"//a[@id='{link_id}']"
            extracted_link = pdf_extractor.extract_pdf_link(None, xpath_for_extractor)

        # PdfLinkExtractor에서 링크를 얻지 못했거나, 처음부터 ID가 없었다면 href 속성을 사용
        if not extracted_link:
            raw_href = link_element.get_attribute("href")
            # "javascript:void(0);" 인 경우 빈 문자열로 처리하여 저장하지 않음
            if raw_href and raw_href.strip() != "javascript:void(0);":
                extracted_link = raw_href
            else:
                return ""  # javascript:void(0); 이거나 빈 href인 경우

        return extracted_link
    return ""


def scrape_cardif_data():
    driver = None
    try:
        # 다운로드 디렉토리 설정 및 생성 (함수 시작 시 한 번만)
        download_dir = os.path.join(os.getcwd(), "neoali", "aiAgen", "downloads", "cardif")
        os.makedirs(download_dir, exist_ok=True)
        print(f"다운로드 디렉토리: {download_dir}")

        service = Service(ChromeDriverManager().install())
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--start-maximized')  # 브라우저 최대화 추가

        # 다운로드 설정
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True
        }
        options.add_experimental_option("prefs", prefs)
        driver = webdriver.Chrome(service=service, options=options)

        url = "https://www.cardif.co.kr/disclosure/papag101.do"
        driver.get(url)

        # PdfLinkExtractor 초기화
        pdf_extractor = PdfLinkExtractor(driver, download_directory=download_dir)

        all_product_data = []

        categories = [
            {"id": "case_save", "name": "저축성"},
            {"id": "case_cover", "name": "보장성"}
        ]

        for category in categories:
            category_id = category["id"]
            category_name = category["name"]
            print(f"\n--- {category_name} 보험 데이터 수집 시작 ---")

            category_label = selenium.webdriver.support.ui.WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f"//label[@for='{category_id}']"))
            )
            category_label.click()
            print(f"'{category_name}' 라디오 버튼의 label 클릭 완료.")

            # 페이지 내용 업데이트 및 select 요소 로드 대기
            selenium.webdriver.support.ui.WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "productList"))
            )
            time.sleep(1)  # JavaScript 처리 대기 (필요 시 유지)
            print("상품 코드 select 요소 로드 완료.")

            select_element = driver.find_element(By.ID, "productList")
            select = selenium.webdriver.support.ui.Select(select_element)
            print("Select 객체 생성 완료.")

            product_codes = [option.get_attribute("value") for option in select.options if option.get_attribute("value") != ""]
            print(f"총 {len(product_codes)}개의 상품 코드 발견: {product_codes}")

            for code in product_codes:
                print(f"\n상품 코드: {code} 데이터 수집 중...")

                # select 요소를 재선택
                selenium.webdriver.support.ui.WebDriverWait(driver, 10).until(
                    EC.staleness_of(select_element)  # 이전 select 요소가 사라지기를 기다림 (카테고리 변경 시)
                    or EC.presence_of_element_located((By.ID, "productList"))  # 또는 현재 select 요소가 나타나기를 기다림
                )
                select_element = driver.find_element(By.ID, "productList")  # 안전을 위해 다시 찾기
                select = selenium.webdriver.support.ui.Select(select_element)
                select.select_by_value(code)
                print(f"상품 코드 {code} 선택 완료.")

                search_button = driver.find_element(By.ID, "select_file_btn")
                search_button.click()
                print("조회 버튼 클릭 완료.")

                selenium.webdriver.support.ui.WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//div[@class="tableWrap type02 mt1"]/table'))
                )
                time.sleep(2)  # 테이블 내용 로드에 충분한 시간 확보 (필요 시 조정)
                print("테이블 로드 완료.")

                product_title_element = selenium.webdriver.support.ui.WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "product_title"))
                )
                current_product_name = product_title_element.text.strip()
                print(f"현재 상품명: {current_product_name}")

                table = driver.find_element(By.XPATH, '//div[@class="tableWrap type02 mt1"]/table')
                rows = table.find_elements(By.TAG_NAME, "tr")

                for row in rows[1:]:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) > 0:
                        sales_period = cols[0].text.strip()
                        product_name = current_product_name  # 각 행의 상품명은 현재 조회된 상품명

                        # 헬퍼 함수를 사용하여 PDF 링크 추출
                        # get_pdf_link_robustly에서 "javascript:void(0);" 링크를 걸러냄
                        product_summary_link = get_pdf_link_robustly(pdf_extractor, cols[1]) if len(cols) > 1 else ""
                        terms_link = get_pdf_link_robustly(pdf_extractor, cols[2]) if len(cols) > 2 else ""
                        business_method_link = get_pdf_link_robustly(pdf_extractor, cols[3]) if len(cols) > 3 else ""

                        product_data = {
                            "상품명": product_name,
                            "판매기간": sales_period,
                            "상품요약서": product_summary_link,
                            "약관": terms_link,
                            "사업방법서": business_method_link
                        }
                        all_product_data.append(product_data)
                        print(f"상품명: {product_name}, 판매기간: {sales_period}")

                # 특약 정보 스크래핑 시작
                print(f"상품 '{product_name}'의 특약 정보 수집 중...")
                try:
                    spc_button = driver.find_element(By.ID, "spcbtn")
                    spc_button.click()
                    print("특약확인 버튼 클릭 완료.")

                    selenium.webdriver.support.ui.WebDriverWait(driver, 10).until(
                        EC.visibility_of_element_located((By.ID, "layer_ty_save"))
                    )
                    time.sleep(1)
                    print("특약 모달창 로드 완료.")

                    modal_content_div = driver.find_element(By.ID, "claus_tbl")
                    spc_titles = modal_content_div.find_elements(By.ID, "spcProduct_title")
                    spc_tables = modal_content_div.find_elements(By.ID, "spc_tbl")

                    for i in range(len(spc_titles)):
                        spc_title = spc_titles[i].text.strip()
                        spc_table = spc_tables[i]

                        spc_rows = spc_table.find_elements(By.TAG_NAME, "tr")
                        for spc_row in spc_rows[1:]:
                            spc_cols = spc_row.find_elements(By.TAG_NAME, "td")
                            if len(spc_cols) > 0:
                                spc_sales_period = spc_cols[0].text.strip()

                                # 헬퍼 함수를 사용하여 PDF 링크 추출
                                # get_pdf_link_robustly에서 "javascript:void(0);" 링크를 걸러냄
                                spc_terms_link = get_pdf_link_robustly(pdf_extractor, spc_cols[1]) if len(spc_cols) > 1 else ""
                                spc_business_method_link = get_pdf_link_robustly(pdf_extractor, spc_cols[2]) if len(spc_cols) > 2 else ""

                                spc_data = {
                                    "상품명": f"{product_name} - {spc_title}",
                                    "판매기간": spc_sales_period,
                                    "약관": spc_terms_link,
                                    "사업방법서": spc_business_method_link
                                }
                                all_product_data.append(spc_data)
                                print(f"  특약 '{spc_title}' 데이터 추가: {spc_data}")

                    close_button = driver.find_element(By.CLASS_NAME, "popClose")
                    close_button.click()
                    print("특약 모달창 닫기 완료.")
                    selenium.webdriver.support.ui.WebDriverWait(driver, 10).until(
                        EC.invisibility_of_element_located((By.ID, "layer_ty_save"))
                    )
                    print("특약 모달창 사라짐 확인.")

                except Exception as e:
                    print(f"특약 정보 수집 중 오류 발생: {e}")
                    try:
                        close_button = driver.find_element(By.CLASS_NAME, "popClose")
                        if close_button.is_displayed():
                            close_button.click()
                            selenium.webdriver.support.ui.WebDriverWait(driver, 10).until(
                                EC.invisibility_of_element_located((By.ID, "layer_ty_save"))
                            )
                            print("오류 후 특약 모달창 닫기 완료.")
                    except Exception as inner_e:
                        print(f"모달창 닫기 중 오류 발생: {inner_e}")
                        pass

        # 데이터베이스 저장 로직
        if DatabaseManager and all_product_data:
            structured_rows_for_db = []
            company_name = "BNP파리바 카디프생명"
            scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            for item in all_product_data:
                product_name = item.get("상품명", "")
                sales_period = item.get("판매기간", "")
                product_code = None

                # 각 문서 유형별로 데이터 추가 (링크가 빈 문자열이 아닌 경우에만 추가)
                if item.get("상품요약서"):  # get_pdf_link_robustly에서 이미 필터링되므로, 이 조건은 유효한 링크만 통과시킴
                    link = item["상품요약서"]
                    if link:  # 빈 문자열이 아닌지 최종 확인
                        structured_rows_for_db.append((
                            company_name, product_name, product_code,
                            "상품요약서", sales_period, scraped_at, link
                        ))
                if item.get("약관"):
                    link = item["약관"]
                    if link:
                        structured_rows_for_db.append((
                            company_name, product_name, product_code,
                            "약관", sales_period, scraped_at, link
                        ))
                if item.get("사업방법서"):
                    link = item["사업방법서"]
                    if link:
                        structured_rows_for_db.append((
                            company_name, product_name, product_code,
                            "사업방법서", sales_period, scraped_at, link
                        ))

            if structured_rows_for_db:
                with DatabaseManager() as db_manager:
                    db_manager.save_data(structured_rows_for_db)
                print(f"총 {len(structured_rows_for_db)}개의 데이터를 데이터베이스에 저장 완료.")
            else:
                print("데이터베이스에 저장할 데이터가 없습니다.")
        else:
            print("DatabaseManager를 임포트할 수 없거나 저장할 데이터가 없습니다.")

        return all_product_data

    except Exception as e:
        print(f"최상위 오류 발생: {e}")
        return None
    finally:
        if driver:
            print("WebDriver를 닫는 중입니다...")
            driver.quit()
            print("WebDriver가 닫혔습니다.")


if __name__ == "__main__":
    data = scrape_cardif_data()
    if data:
        print("\n--- 스크랩된 모든 데이터 ---")
        # JSON 파일로 저장 (한글 깨짐 방지)
        with open("cardif_product_data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print("\n데이터가 cardif_product_data.json 파일에 저장되었습니다.")
    else:
        print("데이터를 가져오는 데 실패했습니다.")
