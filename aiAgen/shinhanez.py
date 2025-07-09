# 신한EZ손해보험/판매중지
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
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
import re  # re 모듈 추가
import urllib.parse  # urllib.parse 모듈 추가

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

DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads", "shinhanez")
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# --- Chrome 다운로드 옵션 설정 함수 ---


def set_chrome_download_options(options, download_dir):
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True
    }
    options.add_experimental_option("prefs", prefs)
    print(f"Chrome 다운로드 경로 설정 완료: {download_dir}")
    return options

# --- NEW HELPER FUNCTIONS FOR SHINHANEZ.PY (페이로드 파싱 및 URL 구성 로직) ---


def _parse_shinhanez_multipart_formdata(payload: str):
    """
    multipart/form-data 페이로드 문자열을 파싱하여 딕셔너리로 반환합니다.
    신한EZ손해보험 사이트의 페이로드 형식에 특화되어 있습니다.
    """
    data = {}
    lines = payload.split('\r\n')
    if not lines:
        return data

    boundary_match = re.match(r'--([a-zA-Z0-9.+_-]+)', lines[0])
    if not boundary_match:
        # print("경고: multipart/form-data 페이로드에서 boundary를 찾을 수 없습니다.") # 디버깅 시 필요하다면 주석 해제
        return data

    boundary = "--" + boundary_match.group(1)

    parts = payload.split(boundary)

    for part in parts:
        if 'Content-Disposition' in part:
            name_match = re.search(r'name="([^"]+)"', part)
            if name_match:
                name = name_match.group(1)
                value_match = re.search(r'\r\n\r\n(.*)', part, re.DOTALL)
                if value_match:
                    value = value_match.group(1).strip()
                    if value.endswith('--'):
                        value = value[:-2]
                    data[name] = value
    return data


def _get_shinhanez_pdf_url_from_payload(payload: str, base_url: str):
    """
    주어진 페이로드와 기본 URL을 사용하여 신한EZ손해보험 PDF 다운로드 URL을 구성합니다.
    """
    if not payload:
        print("오류: PDF 링크 생성을 위한 페이로드(payload)가 비어 있습니다.")
        return None

    parsed_data = _parse_shinhanez_multipart_formdata(payload)

    if not parsed_data:
        print("경고: 페이로드에서 PDF 다운로드 링크 생성에 필요한 파라미터를 찾을 수 없습니다. 페이로드 파싱 실패.")
        return None

    file_no = parsed_data.get('fileNo')
    file_seq = parsed_data.get('fileSeq')

    if file_no and file_seq:
        encoded_file_no = urllib.parse.quote(file_no)
        encoded_file_seq = urllib.parse.quote(file_seq)

        download_url = f"{base_url}?fileNo={encoded_file_no}&fileSeq={encoded_file_seq}"

        # print(f"  [Shinhanez Parser] 구성된 PDF 다운로드 URL: {download_url}") # 디버깅 시 필요하다면 주석 해제
        return download_url
    else:
        print(f"경고: 페이로드에서 fileNo ({file_no}) 또는 fileSeq ({file_seq}) 파라미터를 찾을 수 없습니다.")
        return None
# --- END NEW HELPER FUNCTIONS ---


def scrape_complex_insurance_products_final_with_logs(url):
    options = Options()
    # options.add_argument("--headless") # 브라우저를 백그라운드에서 실행 (GUI 없음). 테스트 시에는 주석 처리하는 것이 좋습니다.
    # options.add_argument("--disable-gpu")
    # options.add_argument("--no-sandbox")

    options = set_chrome_download_options(options, DOWNLOAD_DIR)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    pdf_extractor = None
    if PdfLinkExtractor:
        pdf_extractor = PdfLinkExtractor(driver, download_directory=DOWNLOAD_DIR, url_filter_pattern="fileDown")
    else:
        print("경고: PdfLinkExtractor를 사용할 수 없습니다. PDF 다운로드 기능이 비활성화됩니다.")

    all_scraped_data = []

    try:
        driver.get(url)
        print(f"URL에 접속 중: {url}")

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@data-eid='prdBox'][@class='data-body salePrd-list']"))
        )
        print("페이지 로드 완료 및 최소 하나의 상품 박스(div) 확인.")

        product_box_containers_initial = driver.find_elements(By.XPATH, "//div[@data-eid='prdBox'][@class='data-body salePrd-list']")
        container_infos = []
        for i, container in enumerate(product_box_containers_initial):
            container_infos.append({
                "index": i,
                "xpath": f"//div[@data-eid='prdBox'][@class='data-body salePrd-list'][{i + 1}]"
            })

        for container_info in container_infos:
            container_idx = container_info["index"]
            container_xpath = container_info["xpath"]

            print(f"\n--- {container_idx + 1}번째 상품 테이블 컨테이너 처리 중 ---")

            try:
                current_container_div = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, container_xpath))
                )

                tbody_element = current_container_div.find_element(By.XPATH, "./table/tbody[@data-eid='prdList']")
                print(f"  {container_idx + 1}번째 컨테이너 내에서 table/tbody[@data-eid='prdList']를 찾았습니다.")

                product_name_elements_initial = tbody_element.find_elements(By.XPATH, "./tr/td[@class='align-left']/a[@data-bind='salePrdNmDepth1']")

                row_identifiers = []
                for i, elem in enumerate(product_name_elements_initial):
                    row_identifiers.append({
                        "product_name_text": elem.text.strip(),
                        "product_data_value": elem.get_attribute("data-value"),
                        "product_row_index": i
                    })

                for prod_id_info in row_identifiers:
                    product_name = prod_id_info["product_name_text"]
                    product_data_value = prod_id_info["product_data_value"]
                    actual_product_row_index = prod_id_info["product_row_index"]

                    print(f"\n  --- 상품명 클릭 시도 (JS): {product_name} (실제 tr: {actual_product_row_index + 1}) ---")

                    try:
                        product_name_xpath_to_click = (
                            f"{container_xpath}/table/tbody[@data-eid='prdList']/tr[{actual_product_row_index + 1}]/"
                            f"td[@class='align-left']/a[@data-bind='salePrdNmDepth1'][@data-value='{product_data_value}']"
                        )
                        current_product_name_element = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, product_name_xpath_to_click))
                        )

                        parent_td = current_product_name_element.find_element(By.XPATH, '..')
                        if 'is-active' not in parent_td.get_attribute('class'):
                            driver.execute_script("arguments[0].click();", current_product_name_element)
                            time.sleep(1)

                        sales_period_info_list = []
                        current_tbody_element = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, f"{container_xpath}/table/tbody[@data-eid='prdList']"))
                        )

                        sales_period_elements = current_tbody_element.find_elements(By.XPATH, "./tr/td[2]/a[@data-bind='salePrdNmDepth2']")

                        for sp_elem in sales_period_elements:
                            if sp_elem.text.strip():
                                sales_period_info_list.append({
                                    "text": sp_elem.text.strip(),
                                    "data_value": sp_elem.get_attribute("data-value"),
                                    "data_index_number": sp_elem.get_attribute("data-index-number"),
                                    "element": sp_elem
                                })

                        if not sales_period_info_list:
                            print(f"  상품 '{product_name}'에 대한 유효한 판매 기간을 여러 TR에서 찾을 수 없습니다.")
                            all_scraped_data.append({
                                "상품명": product_name,
                                "판매기간": "N/A (판매기간 없음)",
                                "다운로드_상품요약_가능": False,
                                "다운로드_약관_가능": False,
                                "다운로드_사업방법서_가능": False,
                                "상품요약_PDF_경로": None,
                                "약관_PDF_경로": None,
                                "사업방법서_PDF_경로": None,
                                "컨테이너_인덱스": container_idx + 1
                            })
                            continue

                        for sp_info in sales_period_info_list:
                            sales_period_text = sp_info["text"]
                            sp_data_value = sp_info["data_value"]
                            current_sales_period_element = sp_info["element"]

                            print(f"    --- 판매 기간 클릭 시도 (JS): {sales_period_text} (상품: {product_name}) ---")

                            download_links_status = {
                                "상품요약": False,
                                "약관": False,
                                "사업방법서": False
                            }
                            downloaded_pdf_paths = {
                                "상품요약": None,
                                "약관": None,
                                "사업방법서": None
                            }

                            try:
                                parent_td_sp = current_sales_period_element.find_element(By.XPATH, '..')
                                if 'is-active' not in parent_td_sp.get_attribute('class'):
                                    driver.execute_script("arguments[0].click();", current_sales_period_element)
                                time.sleep(1.5)

                                download_button_xpath_prefix = (
                                    f"{container_xpath}/table/tbody[@data-eid='prdList']/"
                                    f"tr[1]/"
                                    f"td[@class='btn-col']/div[@data-bind='salePrdNmDepth3']/"
                                )

                                # 신한EZ손해보험의 PDF 다운로드 요청 URL
                                SHINHANEZ_FILE_DOWN_URL = "https://www.shinhanez.co.kr/cmn/fileDown"

                                if pdf_extractor:
                                    # 상품요약 버튼 확인 및 클릭 시도
                                    summary_button_xpath = download_button_xpath_prefix + "button[@title='상품요약']"
                                    print("      '상품요약' 버튼 XPath:", summary_button_xpath)
                                    try:
                                        WebDriverWait(driver, 2).until(
                                            EC.element_to_be_clickable((By.XPATH, summary_button_xpath))
                                        )
                                        summary_payload = pdf_extractor.get_pdf_download_payload(summary_button_xpath)
                                        summary_pdf_path = None
                                        if summary_payload:
                                            print("        '상품요약' 페이로드 추출 성공, PDF 링크 생성 시도...")
                                            # _get_shinhanez_pdf_url_from_payload 함수 사용
                                            summary_pdf_path = _get_shinhanez_pdf_url_from_payload(summary_payload, SHINHANEZ_FILE_DOWN_URL)
                                            if not summary_pdf_path:
                                                print("        경고: '상품요약' 페이로드로부터 PDF 다운로드 링크 생성에 실패했습니다.")
                                        else:
                                            print("        경고: '상품요약' 페이로드를 찾을 수 없습니다.")

                                        if summary_pdf_path:
                                            download_links_status["상품요약"] = True
                                            downloaded_pdf_paths["상품요약"] = summary_pdf_path
                                            print("        '상품요약' PDF 다운로드/링크 성공: {}".format(summary_pdf_path))
                                    except TimeoutException:
                                        print("        '상품요약' 버튼을 찾을 수 없거나 클릭할 수 없음. (존재하지 않을 수 있음)")
                                    time.sleep(0.5)

                                    # 약관 버튼 확인 및 클릭 시도
                                    terms_button_xpath = download_button_xpath_prefix + "button[@title='약관']"
                                    print("      '약관' 버튼 XPath:", terms_button_xpath)
                                    try:
                                        WebDriverWait(driver, 2).until(
                                            EC.element_to_be_clickable((By.XPATH, terms_button_xpath))
                                        )
                                        terms_payload = pdf_extractor.get_pdf_download_payload(terms_button_xpath)
                                        terms_pdf_path = None
                                        if terms_payload:
                                            print("        '약관' 페이로드 추출 성공, PDF 링크 생성 시도...")
                                            # _get_shinhanez_pdf_url_from_payload 함수 사용
                                            terms_pdf_path = _get_shinhanez_pdf_url_from_payload(terms_payload, SHINHANEZ_FILE_DOWN_URL)
                                            if not terms_pdf_path:
                                                print("        경고: '약관' 페이로드로부터 PDF 다운로드 링크 생성에 실패했습니다.")
                                        else:
                                            print("        경고: '약관' 페이로드를 찾을 수 없습니다.")

                                        if terms_pdf_path:
                                            download_links_status["약관"] = True
                                            downloaded_pdf_paths["약관"] = terms_pdf_path
                                            print("        '약관' PDF 다운로드/링크 성공: {}".format(terms_pdf_path))
                                    except TimeoutException:
                                        print("        '약관' 버튼을 찾을 수 없거나 클릭할 수 없음. (존재하지 않을 수 있음)")
                                    time.sleep(0.5)

                                    # 사업방법서 버튼 확인 및 클릭 시도
                                    business_method_button_xpath = download_button_xpath_prefix + "button[@title='사업방법서']"
                                    print("      '사업방법서' 버튼 XPath:", business_method_button_xpath)
                                    try:
                                        WebDriverWait(driver, 2).until(
                                            EC.element_to_be_clickable((By.XPATH, business_method_button_xpath))
                                        )
                                        business_method_payload = pdf_extractor.get_pdf_download_payload(business_method_button_xpath)
                                        business_method_pdf_path = None
                                        if business_method_payload:
                                            print("        '사업방법서' 페이로드 추출 성공, PDF 링크 생성 시도...")
                                            # _get_shinhanez_pdf_url_from_payload 함수 사용
                                            business_method_pdf_path = _get_shinhanez_pdf_url_from_payload(
                                                business_method_payload, SHINHANEZ_FILE_DOWN_URL)
                                            if not business_method_pdf_path:
                                                print("        경고: '사업방법서' 페이로드로부터 PDF 다운로드 링크 생성에 실패했습니다.")
                                        else:
                                            print("        경고: '사업방법서' 페이로드를 찾을 수 없습니다.")

                                        if business_method_pdf_path:
                                            download_links_status["사업방법서"] = True
                                            downloaded_pdf_paths["사업방법서"] = business_method_pdf_path
                                            print("        '사업방법서' PDF 다운로드/링크 성공: {}".format(business_method_pdf_path))
                                    except TimeoutException:
                                        print("        '사업방법서' 버튼을 찾을 수 없거나 클릭할 수 없음. (존재하지 않을 수 있음)")
                                    time.sleep(0.5)
                                else:
                                    print("    PdfLinkExtractor가 초기화되지 않아 PDF 다운로드 시도 건너뜀.")

                                print(
                                    f"      다운로드 상태: 상품요약={download_links_status['상품요약']}, "
                                    f"약관={download_links_status['약관']}, "
                                    f"사업방법서={download_links_status['사업방법서']}"
                                )

                                all_scraped_data.append({
                                    "상품명": product_name,
                                    "판매기간": sales_period_text,
                                    "상품요약_PDF_경로": downloaded_pdf_paths["상품요약"],
                                    "약관_PDF_경로": downloaded_pdf_paths["약관"],
                                    "사업방법서_PDF_경로": downloaded_pdf_paths["사업방법서"],
                                    "컨테이너_인덱스": container_idx + 1
                                })

                            except TimeoutException:
                                print(f"    판매 기간 '{sales_period_text}' 클릭 후 다운로드 버튼 컨테이너를 찾을 수 없거나 표시되지 않음 (타임아웃).")
                                all_scraped_data.append({
                                    "상품명": product_name,
                                    "판매기간": sales_period_text + " (다운로드 버튼 컨테이너 없음)",
                                    "다운로드_상품요약_가능": False,
                                    "다운로드_약관_가능": False,
                                    "다운로드_사업방법서_가능": False,
                                    "상품요약_PDF_경로": None,
                                    "약관_PDF_경로": None,
                                    "사업방법서_PDF_경로": None,
                                    "컨테이너_인덱스": container_idx + 1
                                })
                            except Exception as e:
                                print(f"    판매 기간 '{sales_period_text}' 처리 중 오류 발생: {e}")
                                all_scraped_data.append({
                                    "상품명": product_name,
                                    "판매기간": sales_period_text + f" (오류 발생: {e})",
                                    "다운로드_상품요약_가능": False,
                                    "다운로드_약관_가능": False,
                                    "다운로드_사업방법서_가능": False,
                                    "상품요약_PDF_경로": None,
                                    "약관_PDF_경로": None,
                                    "사업방법서_PDF_경로": None,
                                    "컨테이너_인덱스": container_idx + 1
                                })

                    except StaleElementReferenceException:
                        print(f"  상품명 '{product_name}' 처리 중 StaleElementReferenceException 발생. DOM이 변경된 것으로 보입니다. 현재 상품은 건너뜁니다.")
                        break
                    except Exception as e:
                        print(f"  상품명 '{product_name}' 클릭 또는 처리 중 예상치 못한 오류 발생: {e}")
                        continue

            except NoSuchElementException:
                print(f"  {container_idx + 1}번째 컨테이너 내에서 table/tbody[@data-eid='prdList']를 찾을 수 없습니다. 건너킵니다.")
                continue
            except Exception as e:
                print(f"  컨테이너 {container_idx + 1} 처리 중 오류 발생: {e}")
                continue

    except TimeoutException:
        print("페이지 초기 요소 로드를 기다리는 중 시간 초과.")
    except Exception as e:
        print(f"전체 스크랩 중 치명적인 오류가 발생했습니다: {e}")
    finally:
        driver.quit()

    return all_scraped_data


if __name__ == "__main__":
    target_url = "https://www.shinhanez.co.kr/static/pub/PUB2000T021.html"
    scraped_data = scrape_complex_insurance_products_final_with_logs(target_url)

    if scraped_data:
        print("\n--- 모든 컨테이너에서 스크랩된 보험 상품 데이터 ---")
        for product in scraped_data:
            print(product)

        try:
            if DatabaseManager:
                with DatabaseManager(db_name="shinhanez_web_data.db") as db_manager:
                    structured_rows = []
                    for item in scraped_data:
                        if item["약관_PDF_경로"]:
                            structured_rows.append([
                                "신한EZ손해보험",  # company_name
                                item["상품명"],
                                "",  # product_code (일단 비워둠)
                                "약관",  # document_type
                                item["판매기간"],
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                item["약관_PDF_경로"]
                            ])
                        if item["상품요약_PDF_경로"]:
                            structured_rows.append([
                                "신한EZ손해보험",  # company_name
                                item["상품명"],
                                "",  # product_code (일단 비워둠)
                                "상품요약서",  # document_type 변경
                                item["판매기간"],
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                item["상품요약_PDF_경로"]
                            ])
                        if item["사업방법서_PDF_경로"]:
                            structured_rows.append([
                                "신한EZ손해보험",  # company_name
                                item["상품명"],
                                "",  # product_code (일단 비워둠)
                                "사업방법서",  # document_type
                                item["판매기간"],
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                item["사업방법서_PDF_경로"]
                            ])
                    if structured_rows:
                        saved_count = db_manager.save_data(structured_rows)
                        print(f"\n총 {len(scraped_data)}개의 데이터 중 {saved_count}건 저장 완료.")
                    else:
                        print("\n저장할 데이터가 없습니다.")
            else:
                print("경고: DatabaseManager를 사용할 수 없습니다. DB 저장이 비활성화됩니다.")
        except Exception as e:
            print(f"DB 저장 중 오류 발생: {e}")
    else:
        print("스크랩된 데이터가 없습니다.")
