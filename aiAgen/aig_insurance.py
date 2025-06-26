# AIG손해보험/판매중지페이지
import re
import sys
import os
from datetime import datetime  # datetime 모듈 추가
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from seleniumwire import webdriver
from webdriver_manager.chrome import ChromeDriverManager

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from neoali.DB_save import DatabaseManager  # DatabaseManager import 추가
except ImportError as e:
    DatabaseManager = None  # DatabaseManager 초기화 추가
    print(f"경고: 모듈 임포트 실패 ({e}). 일부 기능이 비활성화될 수 있습니다.")


def parse_file_download_params(onclick_attr):
    """
    onclick 속성에서 fileDownLoad 함수의 fileId와 fileSeq를 파싱합니다.
    예: "fileDownLoad(12345, 1)" -> (12345, 1)
    """
    match = re.search(r"fileDownLoad\((\d+),\s*(\d+)\)", onclick_attr)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None


def get_insurance_product_list():
    url = "https://www.aig.co.kr/wo/dpwot001.html?menuId=MS702"

    options = Options()
    options.add_argument("--headless")  # 브라우저를 백그라운드에서 실행
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(url)

        # '보험종류 목록' 테이블이 로드될 때까지 기다립니다.
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//table[contains(., '보험종류') and contains(., '상품명') and contains(., '판매기간')]"))
        )

        table = driver.find_element(By.XPATH, "//table[contains(., '보험종류') and contains(., '상품명') and contains(., '판매기간')]")

        # 테이블 헤더 추출 (더 이상 사용되지 않으므로 제거)
        # headers = [header.text for header in table.find_elements(By.XPATH, "./thead/tr/th")]
        # download_cols_map 변수는 더 이상 사용되지 않으므로 제거합니다.

        products_data = []
        current_product = None

        rows = table.find_elements(By.XPATH, "./tbody/tr")

        for row in rows:
            # 각 행의 데이터를 임시로 저장할 딕셔너리
            row_detail = {}

            # 첫 번째 th (보험종류) 처리
            insurance_type_th = None
            try:
                insurance_type_th = row.find_element(By.XPATH, "./th[contains(@id, 'product01_')]")
            except NoSuchElementException:
                pass

            # 두 번째 th (상품명) 처리
            product_name_th = None
            try:
                product_name_th = row.find_element(By.XPATH, "./th[contains(@id, 'product02_')]")
            except NoSuchElementException:
                pass

            # 새로운 상품이 시작되는지 확인
            if insurance_type_th and product_name_th:
                # 새로운 상품이 시작되면 이전 상품을 products_data에 추가하고 current_product 초기화
                if current_product:
                    products_data.append(current_product)
                current_product = {
                    "보험종류": insurance_type_th.text.strip(),
                    "상품명": product_name_th.text.strip(),
                    "판매기간_정보": []
                }
            elif insurance_type_th:  # 보험종류만 변경되고 상품명은 동일한 경우 (이런 경우는 드물지만 대비)
                if current_product:
                    products_data.append(current_product)
                current_product = {
                    "보험종류": insurance_type_th.text.strip(),
                    "상품명": current_product["상품명"] if current_product else "N/A",  # 이전 상품명 유지
                    "판매기간_정보": []
                }
            elif product_name_th:  # 상품명만 변경되고 보험종류는 동일한 경우
                if current_product:
                    products_data.append(current_product)
                current_product = {
                    "보험종류": current_product["보험종류"] if current_product else "N/A",  # 이전 보험종류 유지
                    "상품명": product_name_th.text.strip(),
                    "판매기간_정보": []
                }

            # td 요소 처리
            # 판매기간 추출 (th 태그)
            try:
                sales_period_th = row.find_element(By.XPATH, "./th[contains(@id, 'product03_')]")
                row_detail["판매기간"] = sales_period_th.text.strip()
            except NoSuchElementException:
                row_detail["판매기간"] = "N/A"  # 판매기간이 없는 경우

            # td 요소 처리 (판매기간 th 다음부터 시작)
            cols = row.find_elements(By.TAG_NAME, "td")

            # 다운로드 링크 처리
            # HTML 구조: <th>보험종류</th>, <th>상품명</th>, <th>판매기간</th>, <td>상품설명서</td>, <td>상품요약서</td>, <td>사업방법서</td>, <td>약관</td>
            # 판매기간이 th로 추출되었으므로, cols는 <td>상품설명서</td>, <td>상품요약서</td>, <td>사업방법서</td>, <td>약관</td> 순서가 됩니다.
            # 상품설명서가 제외되었으므로, 실제 cols는 <td>상품요약서</td>, <td>사업방법서</td>, <td>약관</td> 순서가 됩니다.
            # 따라서 상품요약서: cols[1], 사업방법서: cols[2], 약관: cols[3] (상품설명서가 cols[0]에 해당하지만 제외되므로)

            doc_types_and_td_indices = [
                ("상품요약서", 1),  # cols[1] (상품설명서가 cols[0]에 해당하지만 제외되므로)
                ("사업방법서", 2),  # cols[2]
                ("약관", 3)       # cols[3]
            ]

            for doc_type, td_index in doc_types_and_td_indices:
                if td_index < len(cols):
                    download_link_element = None
                    try:
                        download_link_element = cols[td_index].find_element(By.TAG_NAME, "a")
                    except NoSuchElementException:
                        pass  # 다운로드 링크가 없는 경우

                    if download_link_element:
                        onclick_attr = download_link_element.get_attribute("onclick")
                        file_id, file_seq = parse_file_download_params(onclick_attr)
                        if file_id and file_seq:
                            download_url = f"https://www.aig.co.kr/downLoadFiles.do?fileId={file_id}&fileSeq={file_seq}"
                            row_detail[doc_type] = {
                                "text": download_link_element.text.strip(),
                                "link": download_url
                            }
                        else:
                            row_detail[doc_type] = None
                    else:
                        row_detail[doc_type] = None  # 다운로드 링크가 없는 경우
                else:
                    row_detail[doc_type] = None  # 해당 td가 없는 경우

            if current_product:
                current_product["판매기간_정보"].append(row_detail)

        if current_product:  # 마지막 상품 추가
            products_data.append(current_product)

        return products_data

    except NoSuchElementException as e:
        print(f"요소를 찾을 수 없습니다: {e}")
        return None
    except TimeoutException:
        print("페이지 로드 시간 초과 또는 테이블을 찾을 수 없습니다.")
        return None
    except Exception as e:
        print(f"오류 발생: {e}")
        return None
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    product_list = get_insurance_product_list()
    if product_list:
        print("보험종류 목록:")
        structured_rows_for_db = []
        scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        company_name = "AIG손해보험"  # 회사명 고정

        for product in product_list:
            product_name = product.get('상품명', 'N/A')

            for period_info in product.get("판매기간_정보", []):
                sales_period = period_info.get('판매기간', 'N/A')
                output_str = f"  판매기간:{sales_period}"
                download_links_output = []

                for doc_type in ["상품요약서", "사업방법서", "약관"]:
                    doc_info = period_info.get(doc_type)
                    if doc_info and doc_info.get("link"):
                        link = doc_info["link"]
                        download_links_output.append(f"{doc_type},{link}")

                        # DB 저장용 데이터 추가
                        structured_rows_for_db.append([
                            company_name,
                            product_name,
                            None,  # product_code는 현재 데이터에 없으므로 N/A
                            doc_type,
                            sales_period,
                            scraped_at,
                            link
                        ])

                if download_links_output:
                    output_str += f" {', '.join(download_links_output)}"
                print(output_str)

        # DB에 저장
        if DatabaseManager:
            db_name = "web_data.db"
            with DatabaseManager(db_name=db_name) as db_manager:
                db_manager.save_data(structured_rows_for_db)
        else:
            print("DatabaseManager를 사용할 수 없습니다. 데이터를 DB에 저장하지 못했습니다.")

    else:
        print("보험종류 목록을 가져오지 못했습니다.")
