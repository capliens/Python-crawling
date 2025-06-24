# nh농협생명  https://www.nhlife.co.kr/ho/on/HOON0004M00.nhl
# https://www.nhlife.co.kr/pdfViewerPopup.nhl?apdFlid=FILE_000000000022383&fileSeqn=2 형식
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

# --- 설정 ---
URL = "https://www.nhlife.co.kr/ho/on/HOON0004M00.nhl"
# PDF 뷰어의 기본 URL (다운로드 링크 생성에 사용)
BASE_PDF_VIEWER_URL = "https://www.nhlife.co.kr/pdfViewerPopup.nhl"

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

                if len(modal_data["document_details"]) >= modal_data["total_documents_count"]:
                    print(f"[{datetime.now()}] [모달 데이터 추출] 모든 문서 추출 완료. 페이지네이션 종료.")
                    break

                pagination_paging_div = driver_instance.find_element(By.CSS_SELECTOR, "#pop_contents .pagenate .paging")
                next_page_number = current_page + 1
                next_page_button_xpath = f"./span/button[text()='{next_page_number}']"

                try:
                    next_button = pagination_paging_div.find_element(By.XPATH, next_page_button_xpath)
                    next_button.click()
                    print(f"[{datetime.now()}] [모달 데이터 추출] 다음 페이지 ({next_page_number})로 이동.")
                    current_page += 1
                    time.sleep(1)
                except NoSuchElementException:
                    print(f"[{datetime.now()}] [모달 데이터 추출] 다음 페이지 버튼 없음. 페이지네이션 종료.")
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

        table_element = driver.find_element(By.XPATH, table_xpath)
        initial_rows = table_element.find_elements(By.TAG_NAME, "tr")[1:]
        num_initial_rows = len(initial_rows)

        print(f"[{datetime.now()}] 총 {num_initial_rows}개의 상품 데이터를 찾았습니다. 각 상품 처리 시작.")

        all_extracted_product_data = []  # 모든 상품의 추출된 데이터를 저장할 리스트

        for i in range(num_initial_rows):
            try:
                WebDriverWait(driver, 10).until(EC.invisibility_of_element_located(mask_selector))

                current_table = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, table_xpath))
                )
                current_rows = current_table.find_elements(By.TAG_NAME, "tr")[1:]

                if i >= len(current_rows):
                    print(f"[{datetime.now()}] 더 이상 처리할 상품이 없습니다. 반복을 종료합니다.")
                    break

                row = current_rows[i]

                product_name_element = WebDriverWait(row, 5).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "tLeft"))
                )
                product_name = product_name_element.get_attribute("title")

                print(f"\n[{datetime.now()}] --- 상품 '{product_name}' 처리 시작 ({i + 1}/{num_initial_rows}) ---")

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

                # 추출된 데이터를 요청된 형식으로 출력
                if extracted_modal_data["total_documents_count"] > 0:
                    for doc_detail in extracted_modal_data["document_details"]:
                        summary_link = doc_detail["download_links"]["summary"]["download_url"] if doc_detail["download_links"]["summary"] else "N/A"
                        business_link = doc_detail["download_links"]["business"]["download_url"] if doc_detail["download_links"]["business"] else "N/A"
                        policy_link = doc_detail["download_links"]["policy"]["download_url"] if doc_detail["download_links"]["policy"] else "N/A"

                        print(f"상품명: {extracted_modal_data['product_title']}")
                        print(f"판매기간: {doc_detail['period']}")
                        print(f"상품요약서: {summary_link}")
                        print(f"사업방법서: {business_link}")
                        print(f"약관: {policy_link}")
                        print("-" * 30)  # 구분을 위한 줄

                else:
                    print(f"상품명: {extracted_modal_data['product_title']}")
                    print("판매기간: N/A (문서 없음)")
                    print("상품요약서: N/A")
                    print("사업방법서: N/A")
                    print("약관: N/A")
                    print("-" * 30)  # 구분을 위한 줄

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
            time.sleep(2)

    except TimeoutException:
        print(f"[{datetime.now()}] 오류: 메인 페이지 로딩 중 타임아웃 발생. URL: {URL}")
    except Exception as e:
        print(f"[{datetime.now()}] 오류: 크롤링 중 예상치 못한 최상위 오류 발생: {e}")
    finally:
        if driver:
            driver.quit()
            print(f"[{datetime.now()}] WebDriver가 종료되었습니다.")
