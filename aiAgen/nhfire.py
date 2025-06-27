# NH농협손해/기능연결
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
import os

# --- 상품 요약 정보 스크랩 함수 (변경 없음) ---


def scrape_product_announcement_list(driver, cat1, cat2, cat3, product_list_store):
    """
    div.productAnnounceList에서 상품 제목과 설명을 스크랩합니다.
    """
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.productAnnounceList"))
        )
        products_on_page = driver.find_elements(By.CSS_SELECTOR, "div.productAnnounceList ul.list-group li.list-group-item")

        if not products_on_page:
            print(f"  {cat1} > {cat2} > {cat3}에 대한 productAnnounceList에서 상품 항목을 찾을 수 없습니다.")
            return

        print(f"  {cat1} > {cat2} > {cat3}에 대한 productAnnounceList에서 {len(products_on_page)}개의 상품을 찾았습니다.")

        for k, item in enumerate(products_on_page):
            try:
                title_element = item.find_element(By.CSS_SELECTOR, "div.announce-title h5")
                title = title_element.text.strip() if title_element else "N/A"

                description_element = item.find_element(By.CSS_SELECTOR, "div.announce-content p")
                description = description_element.text.strip() if description_element else "N/A"

                product_list_store.append({
                    "data_source": "ProductAnnouncementList",
                    "category1_name": cat1,
                    "category2_name": cat2,
                    "category3_name": cat3,
                    "title": title,
                    "description": description
                })

            except NoSuchElementException:
                print(f"  {cat3} 아래 {k + 1}번째 항목의 제목 또는 설명을 찾을 수 없습니다. 건너뜁니다.")
                continue
            except Exception as e:
                print(f"  {cat3} 아래 {k + 1}번째 항목 처리 중 오류가 발생했습니다: {e}")
                continue

    except TimeoutException:
        print(f"  {cat1} > {cat2} > {cat3}에 대한 productAnnounceList 로드 대기 시간이 초과되었습니다. 요약이 없거나 로드 속도가 느린 경우 예상될 수 있습니다.")
    except Exception as e:
        print(f"  {cat1} > {cat2} > {cat3}에 대한 productAnnounceList에서 상품 스크래핑 중 오류가 발생했습니다: {e}")


def scrape_table_details_for_category(driver, cat1, cat2, cat3, table_data_store):
    """
    div.Toplineyes_table에서 상세 데이터를 스크랩하고,
    파일 타입 및 다운로드 링크를 추출하며, 추출 즉시 출력합니다.
    """
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.Toplineyes_table table"))
        )
        table_element = driver.find_element(By.CSS_SELECTOR, "div.Toplineyes_table table")
        print(f"  {cat1} > {cat2} > {cat3}에 대한 Toplineyes_table을 찾았습니다.")

        data_rows = table_element.find_elements(By.CSS_SELECTOR, "tbody tr.pdtInfo_Y")

        if not data_rows:
            print(f"  {cat1} > {cat2} > {cat3}에 대한 Toplineyes_table에서 데이터 행을 찾을 수 없습니다.")
            return

        base_download_url_path = "/imageView/downloadFile.ajax"
        full_base_download_url = "https://www.nhfire.co.kr" + base_download_url_path
        document_types = ["약관", "상품요약서", "상품안내장", "사업방법서"]

        for row_idx, row in enumerate(data_rows):
            cells = row.find_elements(By.TAG_NAME, "td")

            row_data = {
                "data_source": "ToplineyesTable",
                "category1_name": cat1,
                "category2_name": cat2,
                "category3_name": cat3,
                "판매개시일": "N/A",
                "판매종료일": "N/A",
                "다운로드_파일": []
            }

            if len(cells) > 0:
                row_data["판매개시일"] = cells[0].text.strip()

            if len(cells) > 1:
                row_data["판매종료일"] = cells[1].text.strip()

            for i in range(2, min(len(cells), len(document_types) + 2)):
                cell = cells[i]
                file_type_name = document_types[i - 2]

                file_link_elements = cell.find_elements(By.CSS_SELECTOR, "a.file_link")

                if file_link_elements:
                    link_element = file_link_elements[0]
                    file_title = link_element.get_attribute("title")
                    onclick_script = link_element.get_attribute("onclick")

                    constructed_download_url = "N/A"
                    if onclick_script and "fnFileDownload" in onclick_script:
                        match = re.search(r'fnFileDownload\s*\(\s*\"([^\"]*)\"\s*,\s*\"([^\"]*)\"\s*\)', onclick_script)
                        if match:
                            file_id = match.group(1)
                            file_type_param = match.group(2)
                            constructed_download_url = f"{full_base_download_url}?fileId={file_id}&fileType={file_type_param}"

                    row_data["다운로드_파일"].append({
                        "타입": file_type_name,
                        "제목": file_title,
                        "링크": constructed_download_url
                    })
                else:
                    cell_text = cell.text.strip()
                    if cell_text and cell_text != "-":
                        row_data["다운로드_파일"].append({
                            "타입": file_type_name,
                            "제목": "N/A",
                            "링크": "N/A - " + cell_text
                        })

            table_data_store.append(row_data)  # 데이터 저장

            # --- 데이터 추출 즉시 콘솔에 출력 ---
            print(f"\n  [테이블 데이터 추출 완료] C1: {row_data['category1_name']} > C2: {row_data['category2_name']} > C3: {row_data['category3_name']}")
            print(f"    판매개시일: {row_data.get('판매개시일', 'N/A')}")
            print(f"    판매종료일: {row_data.get('판매종료일', 'N/A')}")

            if row_data["다운로드_파일"]:
                for file_info in row_data["다운로드_파일"]:
                    print(f"      타입: {file_info['타입']}, 제목: {file_info['제목']}, 링크: {file_info['링크']}")
            else:
                print("      다운로드 가능한 파일이 없습니다.")
            print("---")  # 각 항목 구분을 위한 구분선

    except TimeoutException:
        print(f"  {cat1} > {cat2} > {cat3}에 대한 Toplineyes_table 로드 대기 시간이 초과되었습니다. 이 선택에 대해 없을 수 있습니다.")
    except Exception as e:
        print(f"  {cat1} > {cat2} > {cat3}에 대한 테이블 스크래핑 중 오류가 발생했습니다: {e}")


def scrape_nhfire_products_hierarchical(url):
    """
    주어진 NH농협화재 URL에서 3단계 계층 구조를 탐색하며
    상품 요약 및 상세 테이블 데이터를 웹 스크랩합니다.
    """
    chrome_options = Options()
    # chrome_options.add_argument("--headless") # 필요하다면 주석 해제
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    driver = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    except Exception as e:
        print(f"WebDriver 설정 오류: {e}")
        return

    driver.get(url)

    all_scraped_product_summaries = []
    all_scraped_table_details = []  # 이 리스트에는 계속 데이터를 추가하지만, 출력은 즉시 이루어집니다.

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
                    print(f"'{category1_name}'에 대한 2단계에서 '전체' 버튼 대기 시간이 초과되었습니다. 다음 1단계 카테고리로 건너뜁니다.")
                    continue
                except NoSuchElementException:
                    print(f"'{category1_name}'에 대한 2단계에서 '전체' 버튼을 찾을 수 없습니다. 다음 1단계 카테고리로 건너뜁니다.")
                    continue

                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "oAreaThree"))
                )
                print("3단계 영역 (oAreaThree)이 감지되었습니다.")

                third_level_links_initial = driver.find_elements(By.CSS_SELECTOR, "div#oAreaThree ul.pdtCd_Y li.liClickArea a.pdtNmList")

                if not third_level_links_initial:
                    print(f"'{category1_name}'에 대한 3단계에서 특정 상품 유형 링크를 찾을 수 없습니다. '전체' 클릭 후 직접 스크래핑을 시도합니다.")
                    scrape_product_announcement_list(driver, category1_name, "전체", "전체_no_3rd_filter", all_scraped_product_summaries)
                    scrape_table_details_for_category(driver, category1_name, "전체", "전체_no_3rd_filter", all_scraped_table_details)
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
                            WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "div.productAnnounceList, div.Toplineyes_table table"))
                            )
                            print(f"    '{category3_name}' 클릭 후 콘텐츠가 업데이트되었습니다.")
                            break
                        except TimeoutException:
                            print(f"    시도 {attempt + 1}/{max_attempts}: '{category3_name}' 클릭 후 콘텐츠 로드 대기 시간이 초과되었습니다. 재시도합니다...")
                            if attempt == max_attempts - 1:
                                print(f"    {max_attempts}번의 시도 후에도 '{category3_name}'에 대한 콘텐츠 로드에 실패했습니다. 건너뜁니다.")
                                raise
                        except Exception as e_click:
                            print(f"    시도 {attempt + 1}/{max_attempts}: '{category3_name}' 클릭 중 오류 발생: {e_click}. 재시도합니다...")
                            if attempt == max_attempts - 1:
                                print(f"    {max_attempts}번의 시도 후에도 '{category3_name}' 클릭 또는 콘텐츠 로드에 실패했습니다. 건너뜁니다.")
                                raise
                        time.sleep(1)

                    else:
                        pass

                    try:
                        # ProductAnnounceList 요약 정보는 여전히 나중에 한꺼번에 출력됩니다.
                        scrape_product_announcement_list(driver, category1_name, "전체", category3_name, all_scraped_product_summaries)

                        # 테이블 상세 정보는 이제 이 함수 내에서 즉시 출력됩니다.
                        scrape_table_details_for_category(driver, category1_name, "전체", category3_name, all_scraped_table_details)

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
        print("\n--- 스크랩된 모든 상품 요약 (ProductAnnounceList에서) ---")
        if all_scraped_product_summaries:
            for product in all_scraped_product_summaries:
                print(f"  [요약] C1: {product['category1_name']} > C2: {product['category2_name']} > C3: {product['category3_name']}")
                print(f"    제목: {product['title']}")
                print(f"    설명: {product['description']}\n")
        else:
            print("스크랩된 상품 요약이 없습니다.")

        # 테이블 상세 정보는 이미 각 항목 스크래핑 시점에 출력되었으므로, 최종 요약에서는 출력하지 않습니다.
        # 필요하다면 all_scraped_table_details 리스트를 나중에 다른 목적으로 사용할 수 있습니다.


if __name__ == "__main__":
    target_url = "https://www.nhfire.co.kr/announce/productAnnounce/retrieveInsuranceProductsAnnounce.nhfire"
    scrape_nhfire_products_hierarchical(target_url)
