# 카디프생명/db확인/판매중지페이지/왜 가로채기가 되는거지?
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import selenium.webdriver.support.ui
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import sys
import datetime

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

MG_DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads", "cardif")
if not os.path.exists(MG_DOWNLOAD_DIR):
    os.makedirs(MG_DOWNLOAD_DIR)


def scrape_cardif_data():
    driver = None
    try:
        # 다운로드 디렉토리 설정 및 생성 (가장 먼저 정의)
        download_dir = os.path.join(os.getcwd(), "neoali", "aiAgen", "downloads", "cardif")
        os.makedirs(download_dir, exist_ok=True)
        print(f"다운로드 디렉토리: {download_dir}")

        # Chrome WebDriver 설정 (크롬 드라이버 경로를 지정해야 할 수 있습니다)
        # driver = webdriver.Chrome(executable_path='경로/chromedriver')
        service = Service(ChromeDriverManager().install())
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')  # 샌드박스 비활성화 (Docker 환경 등에서 유용)
        options.add_argument('--disable-dev-shm-usage')  # /dev/shm 사용 비활성화 (일부 Linux 환경에서 유용)

        # 다운로드 설정 추가
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,  # 다운로드 프롬프트 비활성화
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True  # PDF를 외부 뷰어로 열도록 설정 (다운로드 유도)
        }
        options.add_experimental_option("prefs", prefs)
        driver = webdriver.Chrome(service=service, options=options)

        url = "https://www.cardif.co.kr/disclosure/papag101.do"
        driver.get(url)

        # PdfLinkExtractor 초기화
        pdf_extractor = PdfLinkExtractor(driver, download_directory=download_dir)

        all_product_data = []

        # 상품 카테고리 (저축성, 보장성) 순회
        categories = [
            {"id": "case_save", "name": "저축성"},
            {"id": "case_cover", "name": "보장성"}
        ]

        for category in categories:
            category_id = category["id"]
            category_name = category["name"]
            print(f"\n--- {category_name} 보험 데이터 수집 시작 ---")

            # 해당 카테고리 라디오 버튼의 label 클릭
            category_label = selenium.webdriver.support.ui.WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f"//label[@for='{category_id}']"))
            )
            category_label.click()
            print(f"'{category_name}' 라디오 버튼의 label 클릭 완료.")
            time.sleep(2)  # 페이지 내용 업데이트 대기

            # 상품 코드 select 요소 로드 기다립니다.
            selenium.webdriver.support.ui.WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "productList"))
            )
            print("상품 코드 select 요소 로드 완료.")

            # 상품 코드 select 요소 찾기
            select_element = driver.find_element(By.ID, "productList")
            select = selenium.webdriver.support.ui.Select(select_element)
            print("Select 객체 생성 완료.")

            # 모든 옵션 값 가져오기 (첫 번째 "선택" 옵션 제외)
            product_codes = [option.get_attribute("value") for option in select.options if option.get_attribute("value") != ""]
            print(f"총 {len(product_codes)}개의 상품 코드 발견: {product_codes}")

            for code in product_codes:
                print(f"\n상품 코드: {code} 데이터 수집 중...")
                # select 요소가 다시 나타날 때까지 기다립니다.
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

                # 테이블 로드를 기다립니다.
                selenium.webdriver.support.ui.WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//div[@class="tableWrap type02 mt1"]/table'))
                )
                time.sleep(3)  # 페이지 로드 후 추가 대기 (충분한 시간 확보)
                print("테이블 로드 완료.")

                # 상품명 추출 (테이블 밖에서) - 각 상품 조회 후 업데이트
                product_title_element = selenium.webdriver.support.ui.WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "product_title"))
                )
                current_product_name = product_title_element.text.strip()
                print(f"현재 상품명: {current_product_name}")

                # 테이블에서 데이터 추출
                table = driver.find_element(By.XPATH, '//div[@class="tableWrap type02 mt1"]/table')
                rows = table.find_elements(By.TAG_NAME, "tr")

                # 첫 번째 행은 헤더이므로 건너뜁니다.
                for row in rows[1:]:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) > 0:
                        sales_period = cols[0].text.strip()  # 판매기간은 첫 번째 td

                        # 상품명은 루프 밖에서 가져온 current_product_name 사용
                        product_name = current_product_name

                        product_summary_link = ""
                        terms_link = ""
                        business_method_link = ""

                        # 링크 추출 (상품요약서, 약관, 사업방법서)
                        # 각 링크는 <td> 안에 <a> 태그로 존재합니다.
                        # 정확한 인덱스를 확인해야 합니다.
                        # 웹사이트 구조에 따라 인덱스가 달라질 수 있습니다.
                        # 현재 웹사이트 구조를 보면, 판매기간(0), 요약서(1), 약관(2), 사업방법서(3)
                        if len(cols) > 1:  # 요약서
                            summary_a = cols[1].find_elements(By.TAG_NAME, "a")
                            if summary_a and summary_a[0].get_attribute("id"):
                                summary_id = summary_a[0].get_attribute("id")
                                summary_xpath = f"//a[@id='{summary_id}']"
                                product_summary_link = pdf_extractor.extract_pdf_link(None, summary_xpath)  # target_url은 None으로 설정
                                if not product_summary_link:
                                    product_summary_link = summary_a[0].get_attribute("href")  # 실패 시 기존 href 사용
                            else:
                                product_summary_link = summary_a[0].get_attribute("href") if summary_a else ""

                        if len(cols) > 2:  # 약관
                            terms_a = cols[2].find_elements(By.TAG_NAME, "a")
                            if terms_a and terms_a[0].get_attribute("id"):
                                terms_id = terms_a[0].get_attribute("id")
                                terms_xpath = f"//a[@id='{terms_id}']"
                                terms_link = pdf_extractor.extract_pdf_link(None, terms_xpath)
                                if not terms_link:
                                    terms_link = terms_a[0].get_attribute("href")  # 실패 시 기존 href 사용
                            else:
                                terms_link = terms_a[0].get_attribute("href") if terms_a else ""

                        if len(cols) > 3:  # 사업방법서
                            business_a = cols[3].find_elements(By.TAG_NAME, "a")
                            if business_a and business_a[0].get_attribute("id"):
                                business_id = business_a[0].get_attribute("id")
                                business_xpath = f"//a[@id='{business_id}']"
                                business_method_link = pdf_extractor.extract_pdf_link(None, business_xpath)
                                if not business_method_link:
                                    business_method_link = business_a[0].get_attribute("href")  # 실패 시 기존 href 사용
                            else:
                                business_method_link = business_a[0].get_attribute("href") if business_a else ""

                        product_data = {
                            "상품명": product_name,
                            "판매기간": sales_period,
                            "상품요약서": product_summary_link,
                            "약관": terms_link,
                            "사업방법서": business_method_link
                        }
                        all_product_data.append(product_data)
                    print("상품명:" + product_name)
                    print("판매기간:" + sales_period)

                # 특약 정보 스크래핑 시작
                print(f"상품 '{product_name}'의 특약 정보 수집 중...")
                try:
                    # "특약확인" 버튼 클릭
                    spc_button = driver.find_element(By.ID, "spcbtn")
                    spc_button.click()
                    print("특약확인 버튼 클릭 완료.")

                    # 모달창 로드를 기다립니다.
                    selenium.webdriver.support.ui.WebDriverWait(driver, 10).until(
                        EC.visibility_of_element_located((By.ID, "layer_ty_save"))
                    )
                    time.sleep(1)  # 모달창 내용 로드 대기
                    print("특약 모달창 로드 완료.")

                    # 모달창 내 특약 정보 추출
                    modal_content_div = driver.find_element(By.ID, "claus_tbl")  # 모달창의 스크롤 가능한 내용 영역

                    # 모든 특약 제목과 테이블을 찾습니다.
                    spc_titles = modal_content_div.find_elements(By.ID, "spcProduct_title")
                    spc_tables = modal_content_div.find_elements(By.ID, "spc_tbl")

                    for i in range(len(spc_titles)):
                        spc_title = spc_titles[i].text.strip()
                        spc_table = spc_tables[i]

                        spc_rows = spc_table.find_elements(By.TAG_NAME, "tr")
                        for spc_row in spc_rows[1:]:  # 헤더 제외
                            spc_cols = spc_row.find_elements(By.TAG_NAME, "td")
                            if len(spc_cols) > 0:
                                spc_sales_period = spc_cols[0].text.strip()
                                spc_terms_link = ""
                                spc_business_method_link = ""

                                if len(spc_cols) > 1:  # 약관
                                    spc_terms_a = spc_cols[1].find_elements(By.TAG_NAME, "a")
                                    if spc_terms_a and spc_terms_a[0].get_attribute("id"):
                                        spc_terms_id = spc_terms_a[0].get_attribute("id")
                                        spc_terms_xpath = f"//a[@id='{spc_terms_id}']"
                                        spc_terms_link = pdf_extractor.extract_pdf_link(None, spc_terms_xpath)
                                        if not spc_terms_link:
                                            spc_terms_link = spc_terms_a[0].get_attribute("href")
                                    else:
                                        spc_terms_link = spc_terms_a[0].get_attribute("href") if spc_terms_a else ""

                                if len(spc_cols) > 2:  # 사업방법서
                                    spc_business_a = spc_cols[2].find_elements(By.TAG_NAME, "a")
                                    if spc_business_a and spc_business_a[0].get_attribute("id"):
                                        spc_business_id = spc_business_a[0].get_attribute("id")
                                        spc_business_xpath = f"//a[@id='{spc_business_id}']"
                                        spc_business_method_link = pdf_extractor.extract_pdf_link(None, spc_business_xpath)
                                        if not spc_business_method_link:
                                            spc_business_method_link = spc_business_a[0].get_attribute("href")
                                    else:
                                        spc_business_method_link = spc_business_a[0].get_attribute("href") if spc_business_a else ""

                                spc_data = {
                                    "상품명": f"{product_name} - {spc_title}",  # 주 상품명과 특약명 합치기
                                    "판매기간": spc_sales_period,
                                    "약관": spc_terms_link,
                                    "사업방법서": spc_business_method_link
                                }
                                all_product_data.append(spc_data)  # 전체 데이터 리스트에 추가
                                print(f"  특약 '{spc_title}' 데이터 추가: {spc_data}")

                    # 모달창 닫기
                    close_button = driver.find_element(By.CLASS_NAME, "popClose")
                    close_button.click()
                    print("특약 모달창 닫기 완료.")
                    # 모달창이 사라질 때까지 기다립니다.
                    selenium.webdriver.support.ui.WebDriverWait(driver, 10).until(
                        EC.invisibility_of_element_located((By.ID, "layer_ty_save"))
                    )
                    print("특약 모달창 사라짐 확인.")

                except Exception as e:
                    print(f"특약 정보 수집 중 오류 발생: {e}")
                    # 오류 발생 시에도 모달창이 열려 있다면 닫으려고 시도
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
                        pass  # 닫기 버튼을 찾을 수 없거나 이미 닫혀 있는 경우
        # 데이터베이스 저장 로직 추가
        if DatabaseManager and all_product_data:
            structured_rows_for_db = []
            company_name = "BNP파리바 카디프생명"
            scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            for item in all_product_data:
                product_name = item.get("상품명", "")
                sales_period = item.get("판매기간", "")
                product_code = None  # 현재 스크랩되는 정보에 없으므로 빈 문자열로 처리

                # 각 문서 유형별로 데이터 추가
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
            else:
                print("데이터베이스에 저장할 데이터가 없습니다.")
        else:
            print("DatabaseManager를 임포트할 수 없거나 저장할 데이터가 없습니다.")

        return all_product_data

    except Exception as e:
        print(f"오류 발생: {e}")
        return None
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    data = scrape_cardif_data()
    if data:
        print("\n--- 스크랩된 모든 데이터 ---")
        for item in data:
            print(item)
    else:
        print("데이터를 가져오는 데 실패했습니다.")
