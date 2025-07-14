#  NH농협손해/판매중지 페이지
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import sys
from datetime import datetime
import re

# 프로젝트 루트 경로 설정 (DB_save 모듈 임포트를 위함)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# DB_save 모듈 임포트 시도
try:
    from neoali.DB_save import DatabaseManager
except ImportError as e:
    DatabaseManager = None
    print(f"모듈 임포트 실패 ({e}). 일부 기능이 비활성화될 수 있습니다.")

# 다운로드 디렉토리 설정
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads", "nhfire")
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)


def scrape_product_announcement_list(driver, cat1, cat2, cat3, product_list_store):
    """
    div.productAnnounceList에서 상품 제목과 설명을 스크랩합니다.
    이 함수는 여전히 상품 요약 정보를 스크랩하지만, DB 저장 로직은 main 함수에서 제거됩니다.
    """
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.productAnnounceList"))
        )
        products_on_page = driver.find_elements(By.CSS_SELECTOR, "div.productAnnounceList ul.list-group li.list-group-item")

        if not products_on_page:
            print(f"  {cat1} > {cat2} > {cat3}에 대한 productAnnounceList에서 상품 항목을 찾을 수 없습니다.")
            return

        print(f"  {cat1} > {cat2} > {cat3}에 대한 productAnnounceList에서 {len(products_on_page)}개의 상품을 찾았습니다.")

        for k, item in enumerate(products_on_page):
            try:
                title_element = item.find_element(By.CSS_SELECTOR, "div.announce-title h5")
                title = title_element.text.strip() if title_element else "N/A"

                description_element = item.find_element(By.CSS_SELECTOR, "div.announce-content p")
                description = description_element.text.strip() if description_element else "N/A"

                # DB 저장은 하지 않지만, 이 리스트에 추가하여 추후 다른 용도로 활용 가능
                product_list_store.append({
                    "data_source": "ProductAnnouncementList",
                    "category1_name": cat1,
                    "category2_name": cat2,
                    "category3_name": cat3,
                    "title": title,
                    "description": description
                })

            except NoSuchElementException:
                print(f"  {cat3} 아래 {k + 1}번째 항목의 제목 또는 설명을 찾을 수 없습니다. 건너킵니다.")
                continue
            except Exception as e:
                print(f"  {cat3} 아래 {k + 1}번째 항목 처리 중 오류가 발생했습니다: {e}")
                continue

    except TimeoutException:
        print(f"  {cat1} > {cat2} > {cat3}에 대한 productAnnounceList 로드 대기 시간이 초과되었습니다. 요약이 없거나 로드 속도가 느린 경우 예상될 수 있습니다.")
    except Exception as e:
        print(f"  {cat1} > {cat2} > {cat3}에 대한 productAnnounceList에서 상품 스크래핑 중 오류가 발생했습니다: {e}")


def scrape_table_details_for_category(driver, cat1, cat2, cat3, table_data_store, product_name_for_table="N/A"):
    """
    div.Toplineyes_table을 감싸는 div#setPdtInfoArea1 또는 div#setPdtInfoArea2 내에서
    상세 데이터를 스크랩하고, 파일 타입 및 다운로드 링크를 추출하며, 추출 즉시 출력합니다.
    이때, `display: none` 속성으로 숨겨진 div는 건너뛰고 활성화된 div에서만 찾습니다.
    상품명을 파라미터로 받아 DB 저장 시 활용합니다.
    '상품안내장'을 제외하고 나머지 문서들을 DB 저장에 포함합니다.
    """
    table_element = None
    # 예상되는 상위 div ID 목록
    potential_parent_ids = ["setPdtInfoArea1", "setPdtInfoArea2"]

    for parent_id in potential_parent_ids:
        try:
            # 먼저 상위 div를 찾고
            parent_div = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, parent_id))
            )

            # 해당 div가 실제로 화면에 보이는지 (display: none이 아닌지) 확인
            if parent_div.is_displayed():
                # 보이는 div 안에서 div.Toplineyes_table table을 찾습니다.
                table_element = parent_div.find_element(By.CSS_SELECTOR, "div.Toplineyes_table table")
                print(f"  {cat1} > {cat2} > {cat3}에 대한 Toplineyes_table을 활성화된 div#{parent_id} 내에서 찾았습니다.")
                break  # 테이블을 찾았으면 루프를 종료합니다.
            else:
                print(f"  div#{parent_id}는 DOM에 존재하지만 `display: none`으로 숨겨져 있습니다. 다음 ID를 시도합니다.")
                continue  # 다음 상위 ID를 시도합니다.
        except (TimeoutException, NoSuchElementException):
            print(f"  {cat1} > {cat2} > {cat3}에 대한 Toplineyes_table을 div#{parent_id} 내에서 찾을 수 없습니다. 다음 ID를 시도합니다.")
            continue  # 다음 상위 ID를 시도합니다.
        except Exception as e:
            print(f"  div#{parent_id} 내에서 테이블 찾기 중 예기치 않은 오류 발생: {e}")
            continue

    if not table_element:
        print(f"  {cat1} > {cat2} > {cat3}에 대한 Toplineyes_table을 어떤 예상되는 부모 div에서도 찾을 수 없습니다. (활성 상태 확인 포함)")
        return  # 테이블을 찾지 못했으므로 함수 종료

    try:
        data_rows = table_element.find_elements(By.CSS_SELECTOR, "tbody tr.pdtInfo_Y")

        if not data_rows:
            print(f"  {cat1} > {cat2} > {cat3}에 대한 Toplineyes_table에서 데이터 행을 찾을 수 없습니다.")
            return

        all_document_types_in_order = ["약관", "상품요약서", "상품안내장", "사업방법서"]

        base_download_url = "https://www.nhfire.co.kr/imageView/downloadFile.ajax"

        for row_idx, row in enumerate(data_rows):
            cells = row.find_elements(By.TAG_NAME, "td")

            row_data = {
                "data_source": "ToplineyesTable",
                "category1_name": cat1,
                "category2_name": cat2,
                "category3_name": cat3,
                "product_name": product_name_for_table,
                "판매개시일": "N/A",
                "판매종료일": "N/A",
                "다운로드_파일": []
            }

            # --- 디버깅을 위한 판매 개시일/종료일 원본 텍스트 출력 ---
            raw_sales_start_date = cells[0].text.strip() if len(cells) > 0 else "N/A (No cell 0)"
            raw_sales_end_date = cells[1].text.strip() if len(cells) > 1 else "N/A (No cell 1)"
            print(f"    [디버깅] 원본 판매개시일 텍스트: '{raw_sales_start_date}'")
            print(f"    [디버깅] 원본 판매종료일 텍스트: '{raw_sales_end_date}'")
            # --- 디버깅 출력 끝 ---

            if len(cells) > 0:
                row_data["판매개시일"] = raw_sales_start_date

            if len(cells) > 1:
                row_data["판매종료일"] = raw_sales_end_date

            for i in range(2, min(len(cells), len(all_document_types_in_order) + 2)):
                file_type_name = all_document_types_in_order[i - 2]

                if file_type_name == "상품안내장":
                    print(f"    인덱스 {i} (상품안내장) 셀은 건너뜁니다.")
                    continue

                cell = cells[i]

                file_link_elements = cell.find_elements(By.CSS_SELECTOR, "a.file_link")

                if file_link_elements:
                    link_element = file_link_elements[0]
                    file_title = link_element.get_attribute("title")
                    onclick_script = link_element.get_attribute("onclick")

                    extracted_link = ""
                    if onclick_script:
                        match = re.search(r'fnFileDownload\("([^"]+)","([^"]+)"\)', onclick_script)
                        if match:
                            file_id = match.group(1)
                            afile_seqn = match.group(2)
                            extracted_link = f"{base_download_url}?fileId={file_id}&afileSeqn={afile_seqn}"
                        else:
                            print(f"      onclick 스크립트에서 fnFileDownload 인자를 찾을 수 없습니다: {onclick_script}")

                    row_data["다운로드_파일"].append({
                        "타입": file_type_name,
                        "제목": file_title,
                        "링크": extracted_link
                    })
                else:
                    cell_text = cell.text.strip()
                    if cell_text and cell_text != "-":
                        row_data["다운로드_파일"].append({
                            "타입": file_type_name,
                            "제목": "N/A",
                            "링크": "N/A - " + cell_text
                        })

            table_data_store.append(row_data)

            print(
                f"\n  [테이블 데이터 추출 완료] C1: {row_data['category1_name']} > C2: {row_data['category2_name']} > C3: {row_data['category3_name']}")
            print(f"    상품명: {row_data.get('product_name', 'N/A')}")
            print(f"    판매개시일: {row_data.get('판매개시일', 'N/A')}")
            print(f"    판매종료일: {row_data.get('판매종료일', 'N/A')}")

            if row_data["다운로드_파일"]:
                for file_info in row_data["다운로드_파일"]:
                    print(f"      타입: {file_info['타입']}, 제목: {file_info['제목']}, 링크: {file_info['링크']}")
            else:
                print("      다운로드 가능한 파일이 없습니다.")
            print("---")

    except Exception as e:
        print(f"  {cat1} > {cat2} > {cat3}에 대한 테이블 데이터 행 처리 중 오류가 발생했습니다: {e}")


def scrape_nhfire_products_hierarchical(url):
    """
    주어진 NH농협화재 URL에서 3단계 계층 구조를 탐색하며
    상품 요약 및 상세 테이블 데이터를 웹 스크랩합니다.
    """
    chrome_options = Options()
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True
    })
    # chrome_options.add_argument("--headless") # 필요하다면 주석 해제
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    driver = None
    db_manager = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        if DatabaseManager:
            db_manager = DatabaseManager(db_name="nhfire_web_data.db")
        else:
            print("DatabaseManager를 사용할 수 없습니다. DB 저장 기능이 제한됩니다.")

    except Exception as e:
        print(f"WebDriver 설정 오류: {e}")
        return

    driver.get(url)

    all_scraped_product_summaries = []
    all_scraped_table_details = []

    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.areaone ul li a"))
        )
        print("페이지 로드 성공. 1단계 상품 그룹을 찾으려고 시도합니다.")

        first_level_links_initial = driver.find_elements(By.CSS_SELECTOR, "div.areaone ul li a")
        if not first_level_links_initial:
            print("1단계 상품 그룹 링크를 찾을 수 없습니다.")
            return

        first_level_categories_data = []
        for link in first_level_links_initial:
            try:
                first_level_categories_data.append({
                    "text": link.text.strip(),
                    "onclick_script": link.get_attribute("onclick")
                })
            except NoSuchElementException:
                continue

        for i, category1_data in enumerate(first_level_categories_data):
            category1_name = category1_data["text"]
            category1_onclick = category1_data["onclick_script"]
            print(f"\n--- 1단계 카테고리 처리 중: {category1_name} ({i + 1}/{len(first_level_categories_data)}) ---")

            try:
                driver.execute_script(category1_onclick)
                time.sleep(2)

                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "oAreaTwo"))
                )
                print("2단계 영역 (oAreaTwo)이 감지되었습니다.")

                try:
                    all_button_2nd_level = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//div[@id='oAreaTwo']//a[contains(text(), '전체')]"))
                    )
                    all_button_2nd_level.click()
                    print("2단계에서 '전체'를 클릭했습니다.")
                    time.sleep(2)
                except TimeoutException:
                    print(f"'{category1_name}'에 대한 2단계에서 '전체' 버튼 대기 시간이 초과되었습니다. 다음 1단계 카테고리로 건너갑니다.")
                    continue
                except NoSuchElementException:
                    print(f"'{category1_name}'에 대한 2단계에서 '전체' 버튼을 찾을 수 없습니다. 다음 1단계 카테고리로 건너갑니다.")
                    continue

                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "oAreaThree"))
                )
                print("3단계 영역 (oAreaThree)이 감지되었습니다.")

                third_level_links_initial = driver.find_elements(By.CSS_SELECTOR, "div#oAreaThree ul.pdtCd_Y li.liClickArea a.pdtNmList")

                if not third_level_links_initial:
                    print(f"'{category1_name}'에 대한 3단계에서 특정 상품 유형 링크를 찾을 수 없습니다. '전체' 클릭 후 직접 스크래핑을 시도합니다.")
                    scrape_product_announcement_list(driver, category1_name, "전체", "전체_no_3rd_filter", all_scraped_product_summaries)
                    scrape_table_details_for_category(driver, category1_name, "전체", "전체_no_3rd_filter",
                                                      all_scraped_table_details, product_name_for_table="N/A")
                    continue

                third_level_categories_data = []
                for link in third_level_links_initial:
                    try:
                        third_level_categories_data.append({
                            "text": link.text.strip(),
                            "onclick_script": link.get_attribute("onclick")
                        })
                    except NoSuchElementException:
                        continue

                print(f"3단계에서 {len(third_level_categories_data)}개의 특정 상품 유형을 찾았습니다.")

                for j, category3_data in enumerate(third_level_categories_data):
                    category3_name = category3_data["text"]
                    category3_onclick = category3_data["onclick_script"]
                    print(f"\n---- 3단계 상품 유형 처리 중: {category3_name} ({j + 1}/{len(third_level_categories_data)}) ----")

                    max_attempts = 3
                    for attempt in range(max_attempts):
                        try:
                            driver.execute_script(category3_onclick)
                            # productAnnounceList와 Toplineyes_table 중 하나가 로드될 때까지 기다립니다.
                            # 이 대기는 콘텐츠가 DOM에 추가되는 것을 보장하며, is_displayed()는 그 후에 사용됩니다.
                            WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "div.productAnnounceList, div.Toplineyes_table table"))
                            )
                            print(f"    '{category3_name}' 클릭 후 콘텐츠가 업데이트되었습니다.")
                            break
                        except TimeoutException:
                            print(f"    시도 {attempt + 1}/{max_attempts}: '{category3_name}' 클릭 후 콘텐츠 로드 대기 시간이 초과되었습니다. 재시도합니다...")
                            if attempt == max_attempts - 1:
                                print(f"    {max_attempts}번의 시도 후에도 '{category3_name}'에 대한 콘텐츠 로드에 실패했습니다. 건너킵니다.")
                                raise
                        except Exception as e_click:
                            print(f"    시도 {attempt + 1}/{max_attempts}: '{category3_name}' 클릭 중 오류 발생: {e_click}. 재시도합니다...")
                            if attempt == max_attempts - 1:
                                print(f"    {max_attempts}번의 시도 후에도 '{category3_name}' 클릭 또는 콘텐츠 로드에 실패했습니다. 건너킵니다.")
                                raise
                        time.sleep(1)

                    else:
                        pass

                    try:
                        scrape_product_announcement_list(driver, category1_name, "전체", category3_name, all_scraped_product_summaries)
                        scrape_table_details_for_category(driver, category1_name, "전체", category3_name,
                                                          all_scraped_table_details, product_name_for_table=category3_name)

                    except Exception as e:
                        print(f"'{category3_name}' 성공적인 클릭 후 스크래핑 중 오류가 발생했습니다: {e}")
                        continue

            except TimeoutException:
                print(f"'{category1_name}' 클릭 후 요소 대기 시간이 초과되었습니다. 페이지 구조가 변경되었거나 네트워크가 느릴 수 있습니다.")
            except NoSuchElementException:
                print(f"'{category1_name}' 클릭 후 예상되는 요소를 찾을 수 없습니다. 웹페이지 구조가 변경되었을 수 있습니다.")
            except Exception as e:
                print(f"1단계 카테고리 '{category1_name}' 처리 중 예기치 않은 오류가 발생했습니다: {e}")

    except TimeoutException:
        print("초기 페이지 로드 대기 시간이 초과되었습니다. URL이 잘못되었거나 초기 선택자가 잘못되었습니다.")
    except NoSuchElementException:
        print("초기 요소를 찾을 수 없습니다. 웹페이지 구조가 변경되었을 수 있습니다.")
    except Exception as e:
        print(f"전체 스크래핑 프로세스 중 예기치 않은 오류가 발생했습니다: {e}")
    finally:
        if driver:
            driver.quit()
            print("\n브라우저가 닫혔습니다.")

        print("\n--- 모든 스크래핑 작업 완료 ---")

        if db_manager:
            structured_table_details = []
            scraped_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for row_data in all_scraped_table_details:
                for file_info in row_data["다운로드_파일"]:
                    structured_table_details.append([
                        "NH농협손해보험",
                        row_data['product_name'],
                        None,
                        file_info['타입'],
                        f"{row_data['판매개시일']}~{row_data['판매종료일']}",
                        scraped_time,
                        file_info['링크']
                    ])
            if structured_table_details:
                with db_manager as db:
                    db.save_data(structured_table_details)
                    print(f"{len(structured_table_details)}개의 테이블 상세 데이터가 DB에 저장되었습니다.")
            else:
                print("DB에 저장할 테이블 상세 데이터가 없습니다.")
        else:
            print("DatabaseManager가 초기화되지 않아 DB 저장을 건너갑니다.")

        print("\n--- 스크랩된 모든 상품 요약 (콘솔 출력용, DB 저장 안됨) ---")
        if all_scraped_product_summaries:
            for product in all_scraped_product_summaries:
                print(f"  [요약] C1: {product['category1_name']} > C2: {product['category2_name']} > C3: {product['category3_name']}")
                print(f"    제목: {product['title']}")
                print(f"    설명: {product['description']}\n")
        else:
            print("스크랩된 상품 요약이 없습니다.")


if __name__ == "__main__":
    target_url = "https://www.nhfire.co.kr/announce/productAnnounce/retrieveInsuranceProductsAnnounce.nhfire"
    scrape_nhfire_products_hierarchical(target_url)
