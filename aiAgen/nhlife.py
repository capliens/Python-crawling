# nh농협생명/DB저장기능추가/판매중단도 섞여잇음
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
import re
import json  # JSON 저장을 위해 추가

# --- 설정 ---
URL = "https://www.nhlife.co.kr/ho/on/HOON0004M00.nhl"
# PDF 뷰어의 기본 URL (다운로드 링크 생성에 사용)
BASE_PDF_VIEWER_URL = "https://www.nhlife.co.kr/pdfViewerPopup.nhl"
OUTPUT_JSON_FILE = "nhlife_product_data.json"  # JSON 파일명 추가

chrome_options = Options()
# chrome_options.add_argument("--headless") # 필요에 따라 headless 모드를 활성화할 수 있습니다.
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev_shm-usage")
chrome_options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
chrome_options.add_argument("--start-maximized")

seleniumwire_options = {
    'enable_har': True,
}


def initialize_webdriver():
    """WebDriver를 초기화하고 반환합니다."""
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options, seleniumwire_options=seleniumwire_options)
        return driver
    except Exception as e:
        print(f"[{datetime.now()}] 오류: WebDriver 초기화 중 오류 발생: {e}")
        sys.exit(1)


def extract_all_modal_data(driver_instance):
    """
    열려있는 모달창에서 모든 상품 문서 관련 정보를 추출합니다.
    (driver_instance는 현재 모달창이 열린 상태로 포커스되어 있다고 가정합니다.)
    """
    modal_data = {
        "product_title": "",
        "total_documents_count": 0,
        "document_details": []  # 각 문서의 상세 정보 (판매기간, 다운로드 ID 등)
    }

    modal_wrapper_selector = (By.ID, "pop_wrapper")
    try:
        pass
    except TimeoutException:
        print(f"[{datetime.now()}] [모달 데이터 추출] 오류: 모달창이 나타나지 않아 정보를 추출할 수 없습니다.")
        return modal_data

    try:
        # 1. 상품 제목 추출
        product_title_element = WebDriverWait(driver_instance, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#pop_contents h5.product_title"))
        )
        modal_data["product_title"] = product_title_element.text.strip()
        print(f"[{datetime.now()}] [모달 데이터 추출] 상품 제목: '{modal_data['product_title']}'")

        # 2. 전체 문서 수 추출
        total_docs_element = WebDriverWait(driver_instance, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#pop_contents p strong"))
        )
        try:
            total_docs_text = total_docs_element.text.strip()
            num_match = re.search(r'\d+', total_docs_text)
            if num_match:
                modal_data["total_documents_count"] = int(num_match.group(0))
            else:
                modal_data["total_documents_count"] = 0
            print(f"[{datetime.now()}] [모달 데이터 추출] 전체 문서 수: {modal_data['total_documents_count']}건")
        except ValueError:
            print(f"[{datetime.now()}] [모달 데이터 추출] 경고: 전체 문서 수를 숫자로 변환할 수 없음. 텍스트: '{total_docs_element.text.strip()}'")

        # 3. 테이블 데이터 및 페이지네이션 처리 (총 문서 수가 0보다 클 경우에만 실행)
        if modal_data["total_documents_count"] > 0:
            current_page = 1
            while True:
                print(f"[{datetime.now()}] [모달 데이터 추출] 페이지 {current_page}에서 문서 상세 정보 추출 중...")

                table_body = WebDriverWait(driver_instance, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#pop_contents table.tbl_Type01 tbody"))
                )

                rows = table_body.find_elements(By.TAG_NAME, "tr")

                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) >= 4 and cols[0].text.strip() != "":
                        period = cols[0].text.strip()

                        # 각 문서 타입별 다운로드 ID 및 타입 추출 및 URL 생성 함수
                        def get_download_info(td_element):
                            try:
                                button = td_element.find_element(By.CSS_SELECTOR, "span.pdf button[onclick*='popupPdfViewer']")
                                onclick_attr = button.get_attribute("onclick")
                                match = re.search(r"popupPdfViewer\('([^']+)',\s*'([^']+)'\)", onclick_attr)
                                if match:
                                    file_id = match.group(1)
                                    file_type = match.group(2)
                                    # 다운로드 URL 생성
                                    download_url = f"{BASE_PDF_VIEWER_URL}?apdFlid={file_id}&fileSeqn={file_type}"
                                    return {"id": file_id, "type": file_type, "onclick_text": onclick_attr, "download_url": download_url}
                            except NoSuchElementException:
                                pass
                            return None

                        summary_doc_info = get_download_info(cols[1])  # 상품요약서
                        business_doc_info = get_download_info(cols[2])  # 사업방법서
                        policy_doc_info = get_download_info(cols[3])  # 보험약관

                        modal_data["document_details"].append({
                            "period": period,
                            "download_links": {
                                "summary": summary_doc_info,
                                "business": business_doc_info,
                                "policy": policy_doc_info
                            }
                        })

                # 페이지네이션 로직 (모달 내)
                if len(modal_data["document_details"]) >= modal_data["total_documents_count"]:
                    print(f"[{datetime.now()}] [모달 데이터 추출] 모든 문서 추출 완료. 모달 페이지네이션 종료.")
                    break

                pagination_paging_div = driver_instance.find_element(By.CSS_SELECTOR, "#pop_contents .pagenate .paging")
                next_page_number = current_page + 1
                next_page_button_xpath = f"./span/button[text()='{next_page_number}']"
                next_block_button_xpath = "./span/button[@class='pagingBtn next']"  # 다음 10개 페이지 블록 버튼

                try:
                    # 다음 페이지 번호 버튼 클릭 시도
                    next_button = pagination_paging_div.find_element(By.XPATH, next_page_button_xpath)
                    driver_instance.execute_script("arguments[0].click();", next_button)
                    print(f"[{datetime.now()}] [모달 데이터 추출] 다음 페이지 ({next_page_number})로 이동.")
                    current_page += 1
                    time.sleep(1)
                except NoSuchElementException:
                    # 다음 페이지 번호 버튼이 없으면, 다음 10개 페이지 블록 버튼 클릭 시도
                    try:
                        next_block_button = pagination_paging_div.find_element(By.XPATH, next_block_button_xpath)
                        onclick_attr = next_block_button.get_attribute("onclick")
                        match = re.search(r"linkPage\((\d+)\)", onclick_attr)
                        if match:
                            target_page = int(match.group(1))
                            driver_instance.execute_script(f"linkPage({target_page});")
                            print(f"[{datetime.now()}] [모달 데이터 추출] 다음 10페이지 블록 ({target_page}부터)으로 이동.")
                            current_page = target_page  # 현재 페이지를 새로운 블록의 시작 페이지로 업데이트
                            time.sleep(1)
                        else:
                            print(f"[{datetime.now()}] [모달 데이터 추출] 다음 페이지 또는 다음 블록 버튼을 찾을 수 없음. 모달 페이지네이션 종료.")
                            break
                    except NoSuchElementException:
                        print(f"[{datetime.now()}] [모달 데이터 추출] 다음 페이지 버튼 없음. 모달 페이지네이션 종료.")
                        break
        else:
            print(f"[{datetime.now()}] [모달 데이터 추출] 총 문서 수가 0이므로 테이블 데이터 추출을 건너뜁니다.")

    except TimeoutException as e:
        print(f"[{datetime.now()}] [모달 데이터 추출] 오류: 데이터 추출 중 타임아웃 발생: {e}")
    except NoSuchElementException as e:
        print(f"[{datetime.now()}] [모달 데이터 추출] 오류: 필요한 요소를 찾을 수 없음: {e}")
    except StaleElementReferenceException as e:
        print(f"[{datetime.now()}] [모달 데이터 추출] 오류: StaleElementReferenceException 발생 (요소 무효화): {e}")
        print(f"[{datetime.now()}] [모달 데이터 추출] 경고: 모달 내부의 DOM이 예기치 않게 변경되었을 수 있습니다. 해당 상품의 데이터 추출은 불완전할 수 있습니다.")
    except Exception as e:
        print(f"[{datetime.now()}] [모달 데이터 추출] 오류: 예상치 못한 오류 발생: {e}")

    return modal_data


if __name__ == "__main__":
    driver = None
    try:
        driver = initialize_webdriver()
        print(f"[{datetime.now()}] {URL} 로딩 중...")
        driver.get(URL)

        table_xpath = "//table[@summary='이 표는 판매중인 상품을 리스트형식으로 보여주는 곳으로 구분, 상품명, 판매여부, 기간별 다운로드(상품요약서, 사업방법서, 보험약관)로 나누어 설명합니다.']"
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, table_xpath))
        )
        print(f"[{datetime.now()}] 메인 페이지 로드 완료. 현재 제목: '{driver.title}'")

        mask_selector = (By.CLASS_NAME, "mask")
        modal_wrapper_selector = (By.ID, "pop_wrapper")

        all_extracted_product_data = []  # 모든 상품의 추출된 데이터를 저장할 리스트

        # --- 메인 테이블 페이지네이션 루프 시작 ---
        current_main_page = 1
        while True:
            # 12페이지까지 가면 중단하는 조건 추가
            if current_main_page > 12:
                print(f"[{datetime.now()}] 설정된 최대 페이지(12페이지)에 도달했습니다. 메인 테이블 페이지네이션을 중단합니다.")
                break

            print(f"\n[{datetime.now()}] --- 메인 테이블 페이지 {current_main_page} 처리 시작 ---")
            WebDriverWait(driver, 10).until(EC.invisibility_of_element_located(mask_selector))  # 마스크가 사라질 때까지 대기

            current_table = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, table_xpath))
            )
            initial_rows = current_table.find_elements(By.TAG_NAME, "tr")[1:]
            num_initial_rows = len(initial_rows)
            print(f"[{datetime.now()}] 현재 페이지에서 {num_initial_rows}개의 상품 데이터를 찾았습니다.")

            if num_initial_rows == 0 and current_main_page > 1:  # 첫 페이지가 아닌데 상품이 없으면 종료
                print(f"[{datetime.now()}] 현재 페이지에 더 이상 상품이 없습니다. 메인 테이블 페이지네이션 종료.")
                break

            for i in range(num_initial_rows):
                try:
                    # 각 상품을 처리하기 전에 다시 테이블과 행을 찾아 StaleElementReferenceException 방지
                    current_table = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, table_xpath))
                    )
                    current_rows = current_table.find_elements(By.TAG_NAME, "tr")[1:]

                    if i >= len(current_rows):
                        print(f"[{datetime.now()}] 더 이상 처리할 상품이 없습니다. 현재 페이지 반복을 종료합니다.")
                        break

                    row = current_rows[i]

                    product_name_element = WebDriverWait(row, 5).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "tLeft"))
                    )
                    product_name = product_name_element.get_attribute("title")

                    print(f"\n[{datetime.now()}] --- 상품 '{product_name}' 처리 시작 (메인페이지 {current_main_page}, 상품 {i + 1}/{num_initial_rows}) ---")

                    button_xpath_relative = ".//td[3]//button[@title='확인']"
                    confirm_button = WebDriverWait(row, 10).until(
                        EC.element_to_be_clickable((By.XPATH, button_xpath_relative))
                    )

                    driver.execute_script("arguments[0].click();", confirm_button)
                    print(f"[{datetime.now()}] '확인' 버튼 클릭 완료. 모달창 열림 예상.")

                    # --- **모달창 처리 로직 시작** ---
                    WebDriverWait(driver, 30).until(EC.presence_of_element_located(modal_wrapper_selector))
                    print(f"[{datetime.now()}] 모달창 로드 및 나타남 확인.")

                    print(f"[{datetime.now()}] 모달창 내부 콘텐츠 (총 문서 수) 업데이트 대기 중...")
                    try:
                        WebDriverWait(driver, 15).until(
                            lambda d: re.search(r'\d+', d.find_element(By.CSS_SELECTOR, "#pop_contents p strong").text) is not None
                        )
                        print(f"[{datetime.now()}] 모달창 내부 콘텐츠 업데이트 확인.")
                    except TimeoutException:
                        print(f"[{datetime.now()}] 경고: 모달창 내부 콘텐츠 업데이트 타임아웃. 데이터 신뢰도 낮을 수 있음.")

                    extracted_modal_data = extract_all_modal_data(driver)
                    all_extracted_product_data.append(extracted_modal_data)  # 추출된 데이터 저장

                    # 추출된 데이터를 요청된 형식으로 출력 (JSON 저장을 위해 여기서 출력하지 않음)
                    # if extracted_modal_data["total_documents_count"] > 0:
                    #     for doc_detail in extracted_modal_data["document_details"]:
                    #         summary_link = doc_detail["download_links"]["summary"]["download_url"] if doc_detail["download_links"]["summary"] else "N/A"
                    #         business_link = doc_detail["download_links"]["business"]["download_url"] if doc_detail["download_links"]["business"] else "N/A"
                    #         policy_link = doc_detail["download_links"]["policy"]["download_url"] if doc_detail["download_links"]["policy"] else "N/A"

                    #         print(f"상품명: {extracted_modal_data['product_title']}")
                    #         print(f"판매기간: {doc_detail['period']}")
                    #         print(f"상품요약서: {summary_link}")
                    #         print(f"사업방법서: {business_link}")
                    #         print(f"약관: {policy_link}")
                    #         print("-" * 30)  # 구분을 위한 줄
                    # else:
                    #     print(f"상품명: {extracted_modal_data['product_title']}")
                    #     print("판매기간: N/A (문서 없음)")
                    #     print("상품요약서: N/A")
                    #     print("사업방법서: N/A")
                    #     print("약관: N/A")
                    #     print("-" * 30)  # 구분을 위한 줄

                    close_button_xpath = "//input[@type='button' and @value='창닫기' and @onclick='goCertifyClose();']"

                    try:
                        modal_close_button = WebDriverWait(driver, 15).until(
                            EC.element_to_be_clickable((By.XPATH, close_button_xpath))
                        )
                        modal_close_button.click()
                        time.sleep(0.5)

                        WebDriverWait(driver, 20).until(EC.invisibility_of_element_located(modal_wrapper_selector))
                        print(f"[{datetime.now()}] 모달창 성공적으로 닫힘 확인.")

                    except (TimeoutException, NoSuchElementException, Exception) as e:
                        print(f"[{datetime.now()}] 오류: 모달 닫기 중 문제 발생: {e}.")
                        print(f"[{datetime.now()}] 경고: 모달창이 예상대로 닫히지 않았을 수 있습니다. 다음 작업에 영향이 있을 수 있습니다.")

                    # --- **모달창 처리 로직 끝** ---

                except StaleElementReferenceException:
                    print(f"[{datetime.now()}] 오류: 'StaleElementReferenceException' 발생. 해당 상품 처리를 건너뛰고 다음 상품으로 진행.")
                    continue
                except NoSuchElementException as e:
                    print(f"[{datetime.now()}] 오류: 요소를 찾을 수 없음 (상품명, 버튼, 모달 요소): {e}")
                except TimeoutException:
                    print(f"[{datetime.now()}] 오류: '확인' 버튼 클릭 후 모달창 관련 작업 타임아웃 발생.")
                except Exception as e:
                    print(f"[{datetime.now()}] 오류: 상품 처리 중 예상치 못한 오류 발생: {e}")

                print(f"[{datetime.now()}] --- 상품 '{product_name}' 처리 완료 ---\n")
                time.sleep(1)  # 각 상품 처리 후 잠시 대기

            # --- 메인 테이블 페이지네이션 처리 ---
            main_pagination_paging_div = driver.find_element(By.CSS_SELECTOR, ".pagenate .paging")

            # 마지막 페이지 버튼을 찾아서 총 페이지 수 가져오기 (try-except로 안정성 추가)
            total_main_pages = 1
            try:
                last_page_button = main_pagination_paging_div.find_element(By.XPATH, "./span/button[@class='pagingBtn last']")
                last_page_onclick = last_page_button.get_attribute("onclick")
                last_page_match = re.search(r"linkPage\((\d+)\)", last_page_onclick)
                if last_page_match:
                    total_main_pages = int(last_page_match.group(1))
            except NoSuchElementException:
                print(f"[{datetime.now()}] 경고: '마지막 페이지 이동' 버튼을 찾을 수 없습니다. 총 페이지 수를 1로 간주합니다.")

            print(f"[{datetime.now()}] 메인 테이블 총 페이지: {total_main_pages}")

            next_page_found = False
            # 먼저 다음 페이지 번호 버튼 (예: 2, 3, 4, ...)을 찾아서 클릭
            for page_num in range(current_main_page + 1, current_main_page + 11):  # 최대 10개 번호 버튼 탐색
                if page_num > total_main_pages:
                    break  # 총 페이지 수를 넘어섰으면 더 이상 다음 페이지를 찾지 않음

                if page_num > 12:  # 12페이지까지만 크롤링하는 조건
                    print(f"[{datetime.now()}] 다음 페이지 ({page_num})가 설정된 최대 페이지(12페이지)를 초과합니다. 메인 테이블 페이지네이션을 중단합니다.")
                    next_page_found = False  # 더 이상 다음 페이지를 찾지 않으므로 false 유지
                    break  # 페이지네이션 루프를 종료하기 위해 바깥 while 루프를 빠져나갈 준비

                try:
                    next_page_button = main_pagination_paging_div.find_element(By.XPATH, f"./span/button[text()='{page_num}']")
                    driver.execute_script("arguments[0].click();", next_page_button)
                    print(f"[{datetime.now()}] 메인 테이블 다음 페이지 ({page_num})로 이동.")
                    current_main_page = page_num
                    next_page_found = True
                    time.sleep(2)  # 페이지 로딩 대기
                    break  # 다음 페이지로 이동했으니 루프 종료
                except NoSuchElementException:
                    continue  # 해당 번호 버튼이 없으면 다음 번호 시도

            if not next_page_found:
                # 다음 페이지 번호 버튼이 없으면, '다음 10개 페이지 블록' 버튼 클릭 시도
                try:
                    next_block_button = main_pagination_paging_div.find_element(By.XPATH, "./span/button[@class='pagingBtn next']")
                    onclick_attr = next_block_button.get_attribute("onclick")
                    match = re.search(r"linkPage\((\d+)\)", onclick_attr)
                    if match:
                        target_page = int(match.group(1))

                        # 다음 블록으로 이동할 페이지가 12페이지를 초과하면 중단
                        if target_page > 12:
                            print(f"[{datetime.now()}] 다음 블록의 시작 페이지 ({target_page})가 설정된 최대 페이지(12페이지)를 초과합니다. 메인 테이블 페이지네이션을 중단합니다.")
                            break  # 메인 while 루프를 종료

                        # 현재 페이지가 마지막 페이지라면 더 이상 이동하지 않음
                        if target_page > total_main_pages and current_main_page == total_main_pages:
                            print(f"[{datetime.now()}] 마지막 메인 페이지입니다. 메인 테이블 페이지네이션 종료.")
                            break

                        # 다음 블록으로 이동하는 페이지 번호가 현재 페이지와 같거나 작으면, 더 이상 이동할 수 없다고 판단
                        if target_page <= current_main_page:
                            print(f"[{datetime.now()}] 다음 블록으로 이동할 수 없습니다 (현재 페이지 또는 이전 블록). 메인 테이블 페이지네이션 종료.")
                            break

                        driver.execute_script(f"linkPage({target_page});")
                        print(f"[{datetime.now()}] 메인 테이블 다음 10페이지 블록 ({target_page}부터)으로 이동.")
                        current_main_page = target_page
                        time.sleep(2)  # 페이지 로딩 대기
                    else:
                        print(f"[{datetime.now()}] 메인 테이블의 '다음' 버튼을 찾을 수 없습니다. 메인 테이블 페이지네이션 종료.")
                        break
                except NoSuchElementException:
                    print(f"[{datetime.now()}] 메인 테이블의 '다음' 또는 '다음 블록' 버튼을 찾을 수 없습니다. 메인 테이블 페이지네이션 종료.")
                    break
                except StaleElementReferenceException:
                    print(f"[{datetime.now()}] 경고: 메인 테이블 페이지네이션 버튼이 Stale 상태. 다시 시도.")
                    continue  # Stale 에러 발생 시 현재 페이지를 다시 시도

            # 현재 페이지가 마지막 페이지에 도달했는지 확인 (그리고 12페이지 중단 조건도 포함)
            if current_main_page >= total_main_pages or current_main_page >= 12:
                print(f"[{datetime.now()}] 모든 메인 테이블 페이지를 순회했거나 12페이지에 도달했습니다. 메인 테이블 페이지네이션 종료.")
                break

        # --- 메인 테이블 페이지네이션 루프 끝 ---

        # 추출된 모든 데이터를 JSON 파일로 저장
        print(f"[{datetime.now()}] 모든 데이터 추출 완료. JSON 파일로 저장 중: {OUTPUT_JSON_FILE}")
        with open(OUTPUT_JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_extracted_product_data, f, ensure_ascii=False, indent=4)
        print(f"[{datetime.now()}] 데이터가 '{OUTPUT_JSON_FILE}' 파일에 성공적으로 저장되었습니다.")

    except TimeoutException:
        print(f"[{datetime.now()}] 오류: 메인 페이지 로딩 중 타임아웃 발생. URL: {URL}")
    except Exception as e:
        print(f"[{datetime.now()}] 오류: 크롤링 중 예상치 못한 최상위 오류 발생: {e}")
    finally:
        if driver:
            driver.quit()
            print(f"[{datetime.now()}] WebDriver가 종료되었습니다.")
