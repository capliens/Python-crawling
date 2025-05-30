import time
import os  # os 모듈 임포트 추가
import json  # json 모듈 임포트 추가
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class PdfLinkExtractor:
    def __init__(self, driver, download_directory=None):
        """
        PdfLinkExtractor 클래스의 생성자입니다.
        :param driver: Selenium WebDriver 인스턴스
        :param download_directory: PDF 파일이 다운로드될 폴더 경로
        """
        self.driver = driver
        self.download_dir = download_directory

    def get_pdf_url_via_network_interception(self, pdf_trigger_element_xpath):
        """
        네트워크 요청을 가로채 PDF URL을 가져오려고 시도합니다. (방법 3)
        성공하면 PDF URL을, 실패하면 None을 반환합니다.
        """
        print("방법 3: 네트워크 요청 가로채기를 시도합니다...")
        try:
            # CDP 세션 활성화 (Selenium 4 이상)
            self.driver.execute_cdp_cmd("Network.enable", {})

            # 클릭 전에 현재 파일 목록 가져오기
            if self.download_dir and os.path.isdir(self.download_dir):
                files_before_click = set(os.listdir(self.download_dir))
                print(f"다운로드 폴더({self.download_dir}) 확인. 클릭 전 파일 개수: {len(files_before_click)}")
            else:
                files_before_click = set()
                print(f"다운로드 폴더({self.download_dir})를 확인할 수 없거나 유효하지 않습니다.")

            trigger_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, pdf_trigger_element_xpath))
            )
            trigger_element.click()
            print(f"'{pdf_trigger_element_xpath}' 요소를 클릭했습니다. 잠시 후 상태를 확인합니다...")
            time.sleep(3)  # JavaScript 실행 및 페이지 변경 가능성 대기

            current_url_after_click = self.driver.current_url
            print(f"클릭 후 현재 URL: {current_url_after_click}")

            window_handles = self.driver.window_handles
            print(f"클릭 후 Window handles 개수: {len(window_handles)}")
            if len(window_handles) > 1:
                print(f"  현재 Window handle: {self.driver.current_window_handle}")
                for handle in window_handles:
                    # 새 창으로 전환하여 URL을 확인하는 것은 추가 로직이 필요하므로 여기서는 핸들 값만 출력
                    print(f"  발견된 Window handle: {handle}")

            # 1. 클릭 후 현재 URL이 PDF로 바로 변경된 경우
            if current_url_after_click.lower().endswith(".pdf"):
                print(f"네트워크 가로채기 (클릭 후 URL 확인): PDF URL 발견 - {current_url_after_click}")
                return current_url_after_click

            # 2. 새 창/탭이 열렸고, 그 창의 URL이 PDF인 경우 (이 부분은 추가적인 창 전환 로직 필요)
            #    여기서는 간단히 현재 창의 URL만 확인하는 것으로 제한.
            #    만약 새 창으로 PDF가 열린다면, 이 로직으로는 감지 불가.

            # 3. Performance 로그를 사용하여 PDF 요청 URL 찾기 시도 (리디렉션 추적 강화)
            print("Performance 로그를 통해 PDF 요청 URL 분석 시도 (리디렉션 추적 포함)...")
            time.sleep(3)  # 클릭 후 네트워크 로그가 충분히 기록될 시간 확보 (시간 약간 늘림)

            pdf_url_from_network = None
            try:
                logs = self.driver.get_log('performance')
                requests = {}  # requestId를 키로 하여 요청 정보 저장

                # 1단계: 모든 요청과 응답 정보 수집 및 매핑
                for entry in logs:
                    log = json.loads(entry['message'])['message']
                    method = log.get('method')
                    params = log.get('params', {})

                    if 'Network.requestWillBeSent' == method:
                        requestId = params.get('requestId')
                        requests[requestId] = {'request': params.get(
                            'request', {}), 'redirectResponse': params.get('redirectResponse')}

                    elif 'Network.responseReceived' == method:
                        requestId = params.get('requestId')
                        if requestId in requests:
                            requests[requestId]['response'] = params.get('response', {})

                # 2단계: PDF 응답 찾기 (리디렉션 체인 고려)
                for req_id, data in requests.items():
                    response = data.get('response')
                    if not response:
                        continue

                    current_url = response.get('url', '')
                    mime_type = response.get('mimeType', '').lower()
                    headers = response.get('headers', {})
                    status = response.get('status')

                    content_type_header = headers.get('content-type', headers.get('Content-Type', '')).lower()
                    content_disposition_header = headers.get(
                        'content-disposition', headers.get('Content-Disposition', '')).lower()

                    is_pdf_mime = 'application/pdf' in mime_type or 'application/pdf' in content_type_header
                    is_pdf_disposition = 'filename=' in content_disposition_header and '.pdf' in content_disposition_header

                    # 리디렉션이 아닌 실제 컨텐츠를 가진 응답(주로 200 OK)이면서 PDF인 경우
                    if status == 200 and (is_pdf_mime or is_pdf_disposition):
                        print(f"방법 3: Performance 로그에서 PDF 관련 응답 발견 (Status 200).")
                        print(
                            f"  URL: {current_url}, MIME: {mime_type}, Content-Type: {content_type_header}, Content-Disposition: {content_disposition_header}")
                        # current_url 자체가 .pdf로 끝나는 경우에만 직접적인 URL로 간주
                        if current_url and current_url.lower().endswith('.pdf'):
                            print(f"  직접적인 PDF URL로 판단: {current_url}")
                            pdf_url_from_network = current_url
                            break  # 직접적인 PDF URL을 찾았으므로 종료
                        else:
                            # Content-Disposition에 .pdf가 있더라도, URL 자체가 .pdf가 아니면
                            # (예: download.do?...) 로컬 다운로드 감지를 우선시함.
                            print(f"  URL({current_url})이 직접적인 .pdf 링크가 아니므로 로컬 다운로드 감지로 진행합니다.")
                            # pdf_url_from_network는 None으로 유지되어 로컬 다운로드 감지 로직으로 넘어감

                if pdf_url_from_network:  # 직접적인 .pdf URL을 찾은 경우에만 반환
                    return pdf_url_from_network

            except Exception as e_perf:
                print(f"Performance 로그 분석 중 오류: {e_perf} (계속 진행)")

            # 4. 로컬 파일 다운로드 감지 (Fallback)
            if self.download_dir and os.path.isdir(self.download_dir):
                # files_before_click은 이미 위에서 설정됨 (클릭 직전에)
                print(f"다운로드 폴더({self.download_dir})에서 파일 변경 감지 시도. 클릭 전 파일: {len(files_before_click)}")
            else:
                # files_before_click이 설정되지 않았으면 여기서 초기화
                if not hasattr(self, 'files_before_click_for_local_check'):  # 중복 방지
                    self.files_before_click_for_local_check = set()
                    if self.download_dir and os.path.isdir(self.download_dir):
                        self.files_before_click_for_local_check = set(os.listdir(self.download_dir))
                files_before_click = self.files_before_click_for_local_check  # 로컬 변수에 할당
                print(f"다운로드 폴더({self.download_dir})를 확인할 수 없거나 유효하지 않습니다. 클릭 전 파일: {len(files_before_click)}")

            print("로컬 파일 다운로드를 기다립니다...")
            start_time = time.time()
            download_check_timeout = 30
            check_interval = 1

            while time.time() - start_time < download_check_timeout:
                try:  # 현재 URL이 PDF로 변경되었는지도 계속 확인
                    if self.driver.current_url.lower().endswith(".pdf"):
                        print(f"네트워크 가로채기 (루프 중 URL 확인): PDF URL 발견 - {self.driver.current_url}")
                        return self.driver.current_url
                except Exception:
                    pass

                if self.download_dir and os.path.isdir(self.download_dir):
                    current_files_in_loop = set(os.listdir(self.download_dir))
                    potential_new_pdfs = [
                        f for f in current_files_in_loop
                        if f.lower().endswith(".pdf") and f not in files_before_click
                    ]
                    if potential_new_pdfs:
                        new_pdf_file = potential_new_pdfs[0]
                        file_path = os.path.join(self.download_dir, new_pdf_file)
                        print(f"방법 3: 새 PDF 파일 다운로드 감지 (로컬) - {file_path}")
                        return f"downloaded:{file_path}"
                time.sleep(check_interval)

            # 루프 종료 후 최종 확인
            if self.download_dir and os.path.isdir(self.download_dir):
                final_files = set(os.listdir(self.download_dir))
                final_new_pdfs = [
                    f for f in final_files
                    if f.lower().endswith(".pdf") and f not in files_before_click
                ]
                if final_new_pdfs:
                    new_pdf_file = final_new_pdfs[0]
                    file_path = os.path.join(self.download_dir, new_pdf_file)
                    print(f"방법 3: 새 PDF 파일 다운로드 감지 (로컬 최종 확인) - {file_path}")
                    return f"downloaded:{file_path}"

            print("방법 3: URL 변경, Performance 로그, 로컬 파일 다운로드를 통해 PDF를 감지하지 못했습니다.")
            return None
        except Exception as e:
            print(f"방법 3 실행 중 오류 발생: {e}")
            return None
        finally:
            try:
                self.driver.execute_cdp_cmd("Network.disable", {})
            except Exception:  # CDP 명령 실패는 무시할 수 있음
                pass

    def get_pdf_url_via_href(self, pdf_link_element_xpath):
        """
        <a> 태그의 href 속성에서 PDF URL을 직접 추출합니다. (방법 2)
        성공하면 PDF URL을, 실패하면 None을 반환합니다.
        """
        print("방법 2: <a> 태그의 href 속성 직접 추출을 시도합니다...")
        try:
            pdf_link_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, pdf_link_element_xpath))
            )
            pdf_url = pdf_link_element.get_attribute('href')
            element_type = pdf_link_element.get_attribute('type')
            is_pdf_type = element_type and 'application/pdf' in element_type.lower()
            if pdf_url and ('.pdf' in pdf_url.lower() or is_pdf_type):
                print(f"방법 2 성공: PDF URL 발견 - {pdf_url}")
                return pdf_url
            elif pdf_url:
                print(f"방법 2: href 값은 찾았으나 PDF 링크로 보이지 않습니다: {pdf_url}")
                return None
            else:
                print("방법 2: href 속성을 찾았지만 값이 비어있습니다.")
                return None
        except Exception as e:
            print(f"방법 2 실행 중 오류 발생: {e}")
            return None

    def extract_pdf_link(self, target_url, pdf_trigger_element_xpath_method3, pdf_link_element_xpath_method2):
        """
        주어진 URL에서 PDF 링크를 추출합니다. 방법 3을 먼저 시도하고 실패하면 방법 2를 시도합니다.
        """
        pdf_url_found = None
        try:
            if not target_url:
                print("오류: target_url이 제공되지 않았습니다.")
                return None

            self.driver.get(target_url)
            print(f"페이지 로드: {target_url}")
            time.sleep(3)  # 페이지 로딩 대기

            # 방법 3 시도
            if pdf_trigger_element_xpath_method3:
                print("\n--- 방법 3 시도 ---")
                pdf_url_found = self.get_pdf_url_via_network_interception(pdf_trigger_element_xpath_method3)

            # 방법 3 실패 시 방법 2 시도
            if not pdf_url_found and pdf_link_element_xpath_method2:
                print("\n--- 방법 3 실패 또는 시도 안함, 방법 2 시도 ---")
                # 페이지 상태가 변경되었을 수 있으므로, 필요시 새로고침
                # self.driver.refresh()
                # time.sleep(2)
                pdf_url_found = self.get_pdf_url_via_href(pdf_link_element_xpath_method2)

            if pdf_url_found:
                print(f"\n최종적으로 발견된 PDF URL: {pdf_url_found}")
            else:
                print("\n두 가지 방법 모두 PDF URL을 찾는 데 실패했거나 시도할 XPATH가 제공되지 않았습니다.")
            return pdf_url_found

        except Exception as e:
            print(f"PDF 링크 추출 중 오류 발생: {e}")
            return None


# --- 예시 사용법 ---
if __name__ == "__main__":
    # Chrome 옵션 설정
    chrome_options = Options()
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    # WebDriver 초기화 (try-finally로 driver.quit() 보장)
    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)

        # PdfLinkExtractor 인스턴스 생성
        extractor = PdfLinkExtractor(driver)

        # 대상 URL 및 XPATH 설정 (실제 값으로 변경 필요)
        target_page_url = "YOUR_TARGET_PAGE_URL_HERE"  # 예: "https://www.example.com/documents"
        # 방법 3을 위한 PDF 다운로드 유발 요소의 XPATH
        # 예: "//button[contains(text(),'Download PDF')]"
        trigger_xpath_method3 = "XPATH_FOR_PDF_DOWNLOAD_TRIGGER_ELEMENT"
        # 방법 2를 위한 PDF <a> 태그의 XPATH
        link_xpath_method2 = "XPATH_FOR_PDF_LINK_A_TAG"  # 예: "//a[contains(@href,'.pdf')]"

        if target_page_url == "YOUR_TARGET_PAGE_URL_HERE" or \
           trigger_xpath_method3 == "XPATH_FOR_PDF_DOWNLOAD_TRIGGER_ELEMENT" or \
           link_xpath_method2 == "XPATH_FOR_PDF_LINK_A_TAG":
            print("스크립트 상단의 target_page_url, trigger_xpath_method3, link_xpath_method2 변수를"
                  " 실제 값으로 변경한 후 실행해주세요.")
        else:
            # PDF 링크 추출 실행
            extracted_link = extractor.extract_pdf_link(target_page_url, trigger_xpath_method3, link_xpath_method2)

            if extracted_link:
                print(f"\n예시 실행: 추출된 PDF 링크: {extracted_link}")
            else:
                print("\n예시 실행: PDF 링크를 추출하지 못했습니다.")

    except Exception as e:
        print(f"예시 실행 중 오류 발생: {e}")
    finally:
        if driver:
            driver.quit()
            print("WebDriver를 종료했습니다.")
