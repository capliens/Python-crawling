# 카디프생명
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

# 프로젝트 루트 경로 설정 (DB_save 모듈 임포트를 위함)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    # 데이터베이스 관리 모듈 임포트 시도
    from neoali.DB_save import DatabaseManager
except ImportError as e:
    DatabaseManager = None
    print(f"경고: DatabaseManager 모듈 임포트 실패 ({e}). 데이터베이스 저장 기능이 비활성화됩니다.")

# PDF 다운로드 기본 URL 정의
# 파일 ID는 <a> 태그의 id 속성에서 가져옵니다.
BASE_DOWNLOAD_URL = "https://www.cardif.co.kr/common/rest/fileDownloadFront.do?fileId={}&atchFileDiv=DIS&frontBackDiv=Front"


def save_to_database(data_list, company_name="BNP파리바 카디프생명"):
    """
    주어진 데이터 리스트를 데이터베이스에 저장합니다.
    각 상품 또는 특약의 문서 타입별로 별도의 레코드를 생성합니다.
    """
    if not DatabaseManager:
        print("DatabaseManager를 임포트할 수 없어 데이터베이스에 저장할 수 없습니다.")
        return

    if not data_list:
        print("데이터베이스에 저장할 데이터가 없습니다.")
        return

    structured_rows_for_db = []
    scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for item in data_list:
        product_name = item.get("상품명", "")  # 상품 또는 특약의 이름
        sales_period = item.get("판매기간", "")
        product_code = None  # 현재 스크랩된 정보에는 없으므로 None으로 처리

        # '상품요약서', '약관', '사업방법서' 필드가 존재하고 값이 비어있지 않은 경우에만 DB에 추가
        # 특약도 이제 이 필드들을 가질 수 있으므로 일반 상품과 동일하게 처리됩니다.
        if item.get("상품요약서"):
            structured_rows_for_db.append((
                company_name, product_name, product_code,
                "상품요약서", sales_period, scraped_at, item["상품요약서"]
            ))
        if item.get("약관"):
            structured_rows_for_db.append((
                company_name, product_name, product_code,
                "약관", sales_period, scraped_at, item["약관"]
            ))
        if item.get("사업방법서"):
            structured_rows_for_db.append((
                company_name, product_name, product_code,
                "사업방법서", sales_period, scraped_at, item["사업방법서"]
            ))

    if structured_rows_for_db:
        with DatabaseManager() as db_manager:
            db_manager.save_data(structured_rows_for_db)
        print(f"\n총 {len(structured_rows_for_db)}개의 데이터를 데이터베이스에 저장 완료.")
    else:
        print("데이터베이스에 저장할 데이터가 없습니다.")


def scrape_cardif_data():
    """
    BNP파리바 카디프생명 웹사이트에서 상품 및 특약 데이터를 스크랩하고 데이터베이스에 저장합니다.
    """
    driver = None
    all_scraped_data = []  # 스크래핑된 모든 데이터를 저장하여 최종적으로 반환할 리스트

    try:
        service = Service(ChromeDriverManager().install())
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        # PDF 다운로드 관련 설정은 완전히 제거되었습니다.

        driver = webdriver.Chrome(service=service, options=options)

        # --- 첫 번째 URL 데이터 스크랩 및 저장: papag101.do ---
        url_1 = "https://www.cardif.co.kr/disclosure/papag101.do"
        print(f"\n--- {url_1} 에서 데이터 스크랩 시작 ---")
        data_from_url1 = scrape_page(driver, url_1)
        all_scraped_data.extend(data_from_url1)  # 최종 반환 리스트에 추가
        print(f"\n--- {url_1} 데이터 데이터베이스에 저장 시작 ---")
        save_to_database(data_from_url1)  # 첫 번째 URL 데이터 저장
        print(f"--- {url_1} 데이터 저장 완료 ---")

        # --- 두 번째 URL 데이터 스크랩 및 저장: papag201.do ---
        url_2 = "https://www.cardif.co.kr/disclosure/papag201.do"
        print(f"\n--- {url_2} 에서 데이터 스크랩 시작 ---")
        data_from_url2 = scrape_page(driver, url_2)
        all_scraped_data.extend(data_from_url2)  # 최종 반환 리스트에 추가
        print(f"\n--- {url_2} 데이터 데이터베이스에 저장 시작 ---")
        save_to_database(data_from_url2)  # 두 번째 URL 데이터 저장
        print(f"--- {url_2} 데이터 저장 완료 ---")

        return all_scraped_data

    except Exception as e:
        print(f"오류 발생: {e}")
        return None
    finally:
        if driver:
            driver.quit()  # 작업 완료 후 드라이버 종료


def scrape_page(driver, url):
    """
    주어진 URL에서 상품 및 특약 데이터를 스크랩하여 리스트로 반환합니다.
    """
    driver.get(url)
    current_page_data = []  # 현재 페이지의 데이터를 저장할 리스트

    # 스크랩할 상품 카테고리 정의
    categories = [
        {"id": "case_save", "name": "저축성"},
        {"id": "case_cover", "name": "보장성"}
    ]

    for category in categories:
        category_id = category["id"]
        category_name = category["name"]
        print(f"\n--- {category_name} 보험 데이터 수집 시작 ({url}) ---")

        try:
            # 카테고리 라디오 버튼 클릭
            category_label = selenium.webdriver.support.ui.WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f"//label[@for='{category_id}']"))
            )
            category_label.click()
            print(f"'{category_name}' 라디오 버튼 클릭 완료.")
            time.sleep(2)  # UI 업데이트 대기

            # 상품 목록 드롭다운 로드 대기
            selenium.webdriver.support.ui.WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "productList"))
            )
            print("상품 코드 select 요소 로드 완료.")

            select_element = driver.find_element(By.ID, "productList")
            select = selenium.webdriver.support.ui.Select(select_element)
            print("Select 객체 생성 완료.")

            # 모든 상품 코드 추출 (빈 값 제외)
            product_codes = [option.get_attribute("value") for option in select.options if option.get_attribute("value") != ""]
            print(f"총 {len(product_codes)}개의 상품 코드 발견: {product_codes}")

            # 각 상품 코드별로 데이터 스크래핑
            for code in product_codes:
                print(f"\n상품 코드: {code} 데이터 수집 중...")
                # 드롭다운 요소가 새로고침될 수 있으므로 다시 찾아서 선택
                selenium.webdriver.support.ui.WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "productList"))
                )
                select_element_in_loop = driver.find_element(By.ID, "productList")
                select = selenium.webdriver.support.ui.Select(select_element_in_loop)
                select.select_by_value(code)
                print(f"상품 코드 {code} 선택 완료.")

                # 조회 버튼 클릭
                search_button = driver.find_element(By.ID, "select_file_btn")
                search_button.click()
                print("조회 버튼 클릭 완료.")

                # 상품 정보 테이블 로드 대기
                selenium.webdriver.support.ui.WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//div[@class="tableWrap type02 mt1"]/table'))
                )
                time.sleep(3)  # 데이터 로드 및 UI 안정화 추가 대기
                print("상품 정보 테이블 로드 완료.")

                # 현재 선택된 상품명 추출
                product_title_element = selenium.webdriver.support.ui.WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "product_title"))
                )
                current_product_name = product_title_element.text.strip()
                print(f"현재 상품명: {current_product_name}")

                # 상품 정보 테이블에서 행(row) 추출
                table = driver.find_element(By.XPATH, '//div[@class="tableWrap type02 mt1"]/table')
                rows = table.find_elements(By.TAG_NAME, "tr")

                # 각 상품 버전별 데이터 처리 (첫 번째 행은 헤더이므로 건너뜜)
                for row in rows[1:]:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) > 0:
                        sales_period = cols[0].text.strip()  # 판매기간
                        # 주 상품명은 current_product_name 변수 사용

                        product_summary_link = ""
                        terms_link = ""
                        business_method_link = ""

                        # 상품요약서 링크 추출 (id가 있는 경우에만)
                        if len(cols) > 1:
                            summary_a = cols[1].find_elements(By.TAG_NAME, "a")
                            if summary_a and summary_a[0].get_attribute("id"):
                                summary_id = summary_a[0].get_attribute("id")
                                product_summary_link = BASE_DOWNLOAD_URL.format(summary_id)

                        # 약관 링크 추출 (id가 있는 경우에만)
                        if len(cols) > 2:
                            terms_a = cols[2].find_elements(By.TAG_NAME, "a")
                            if terms_a and terms_a[0].get_attribute("id"):
                                terms_id = terms_a[0].get_attribute("id")
                                terms_link = BASE_DOWNLOAD_URL.format(terms_id)

                        # 사업방법서 링크 추출 (id가 있는 경우에만)
                        if len(cols) > 3:
                            business_a = cols[3].find_elements(By.TAG_NAME, "a")
                            if business_a and business_a[0].get_attribute("id"):
                                business_id = business_a[0].get_attribute("id")
                                business_method_link = BASE_DOWNLOAD_URL.format(business_id)

                        # 추출한 데이터를 딕셔너리 형태로 저장
                        product_data = {
                            "상품명": current_product_name,
                            "판매기간": sales_period,
                            "상품요약서": product_summary_link,
                            "약관": terms_link,
                            "사업방법서": business_method_link
                        }
                        current_page_data.append(product_data)
                        print(f"상품명: {current_product_name}, 판매기간: {sales_period}")

                # 특약 정보 수집 (특약확인 버튼 클릭)
                print(f"상품 '{current_product_name}'의 특약 정보 수집 중...")
                try:
                    spc_button = driver.find_element(By.ID, "spcbtn")
                    spc_button.click()
                    print("특약확인 버튼 클릭 완료.")

                    # 특약 모달창 로드 대기
                    selenium.webdriver.support.ui.WebDriverWait(driver, 10).until(
                        EC.visibility_of_element_located((By.ID, "layer_ty_save"))
                    )
                    time.sleep(1)  # 모달창 내용 로드 대기
                    print("특약 모달창 로드 완료.")

                    modal_content_div = driver.find_element(By.ID, "claus_tbl")

                    # 특약 그룹별 제목과 테이블 추출
                    spc_titles = modal_content_div.find_elements(By.ID, "spcProduct_title")
                    spc_tables = modal_content_div.find_elements(By.ID, "spc_tbl")

                    # 각 특약 그룹별 데이터 처리
                    for i in range(len(spc_titles)):
                        spc_title = spc_titles[i].text.strip()  # 특약 그룹의 제목 (예: '특약명')
                        spc_table = spc_tables[i]

                        spc_rows = spc_table.find_elements(By.TAG_NAME, "tr")
                        # 각 특약별 데이터 처리 (첫 번째 행은 헤더이므로 건너뜜)
                        for spc_row in spc_rows[1:]:
                            spc_cols = spc_row.find_elements(By.TAG_NAME, "td")
                            if len(spc_cols) > 0:
                                spc_sales_period = spc_cols[0].text.strip()  # 특약 판매기간
                                spc_terms_link = ""
                                spc_business_method_link = ""

                                # 특약 약관 링크 추출 (id가 있는 경우에만)
                                # 특약 테이블 구조에 따라 cols 인덱스가 다를 수 있으므로 확인 필요
                                if len(spc_cols) > 1:  # 약관 컬럼
                                    spc_terms_a = spc_cols[1].find_elements(By.TAG_NAME, "a")
                                    if spc_terms_a and spc_terms_a[0].get_attribute("id"):
                                        spc_terms_id = spc_terms_a[0].get_attribute("id")
                                        spc_terms_link = BASE_DOWNLOAD_URL.format(spc_terms_id)

                                # 특약 사업방법서 링크 추출 (id가 있는 경우에만)
                                if len(spc_cols) > 2:  # 사업방법서 컬럼
                                    spc_business_a = spc_cols[2].find_elements(By.TAG_NAME, "a")
                                    if spc_business_a and spc_business_a[0].get_attribute("id"):
                                        spc_business_id = spc_business_a[0].get_attribute("id")
                                        spc_business_method_link = BASE_DOWNLOAD_URL.format(spc_business_id)

                                # 추출한 특약 데이터를 딕셔너리 형태로 저장
                                spc_data = {
                                    "상품명": spc_title,  # 특약명만 저장
                                    "판매기간": spc_sales_period,
                                    "약관": spc_terms_link,          # 특약 약관 링크
                                    "사업방법서": spc_business_method_link  # 특약 사업방법서 링크
                                }
                                current_page_data.append(spc_data)
                                print(f"   특약 '{spc_title}' 데이터 추가: {spc_data}")

                    # 특약 모달창 닫기
                    close_button = driver.find_element(By.CLASS_NAME, "popClose")
                    close_button.click()
                    print("특약 모달창 닫기 완료.")
                    selenium.webdriver.support.ui.WebDriverWait(driver, 10).until(
                        EC.invisibility_of_element_located((By.ID, "layer_ty_save"))
                    )
                    print("특약 모달창 사라짐 확인.")

                except Exception as e:
                    print(f"특약 정보 수집 중 오류 발생: {e}")
                    # 오류 발생 시 모달창이 열려 있다면 닫기 시도
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
                        pass  # 추가적인 모달 닫기 오류는 무시

        except Exception as e:
            print(f"카테고리 '{category_name}' 처리 중 오류 발생: {e}")
            # 카테고리 처리 중 오류 발생 시, 페이지를 새로고침하여 다음 카테고리 시도
            driver.get(url)
            time.sleep(2)  # 페이지 로드 대기
    return current_page_data  # 현재 페이지에서 수집된 데이터를 반환


# 스크립트 직접 실행 부분
if __name__ == "__main__":
    data = scrape_cardif_data()
    if data:
        print("\n--- 스크랩된 모든 데이터 ---")
        for item in data:
            print(item)
    else:
        print("데이터를 가져오는 데 실패했습니다.")
