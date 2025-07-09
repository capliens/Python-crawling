import os
import re
import requests
import urllib.parse  # 이 모듈은 더 이상 사용하지 않지만, 일단 남겨둡니다. shinhanez.py에서 사용될 것이기 때문입니다.
from seleniumwire import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
import time


class PdfLinkExtractor:
    def __init__(self, driver: webdriver.Chrome, download_directory: str = None, element_wait_timeout: int = 10,
                 request_timeout: int = 10, verify_url_liveness: bool = True, url_filter_pattern: str = None):
        self.driver = driver
        self.download_directory = download_directory
        self.element_wait_timeout = element_wait_timeout
        self.request_timeout = request_timeout
        self.verify_url_liveness = verify_url_liveness
        self.driver.request_interceptor = self._interceptor
        self.downloaded_files = []  # 다운로드된 파일 경로 저장
        self.url_filter_pattern = url_filter_pattern
        print(f"PdfLinkExtractor 초기화. 다운로드 디렉토리: {self.download_directory}")

    def _interceptor(self, request):
        pass

    def _wait_for_download(self, initial_files=None, timeout=30):
        """
        주어진 디렉토리에서 새 파일 다운로드가 완료될 때까지 기다립니다.
        """
        if initial_files is None:
            initial_files = set(os.listdir(self.download_directory))

        start_time = time.time()
        while time.time() - start_time < timeout:
            current_files = set(os.listdir(self.download_directory))
            new_files = current_files - initial_files

            for f_name in new_files:
                f_path = os.path.join(self.download_directory, f_name)
                # .crdownload 확장자가 사라지면 다운로드 완료로 간주
                if not f_name.endswith('.crdownload') and os.path.exists(f_path):
                    self.downloaded_files.append(f_path)
                    print(f"  [Download Monitor] 새 파일 다운로드 완료: {f_path}")
                    return f_path
            time.sleep(0.5)  # 0.5초 간격으로 확인
        print(f"  [Download Monitor] 지정된 시간({timeout}초) 내에 새 파일 다운로드 완료되지 않음.")
        return None

    def click_and_get_download_link(self, button_xpath: str, timeout: int = 10):
        """
        XPath로 버튼을 클릭하고 네트워크 요청을 모니터링하여 PDF 다운로드 링크를 추출하거나 파일 다운로드를 감지합니다.
        (이 함수는 실제 파일 다운로드 방식을 사용할 때 유용합니다.)
        """
        try:
            button = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, button_xpath))
            )
            print(f"  버튼 클릭 시도: {button_xpath}")

            # 현재 존재하는 파일 목록 저장 (다운로드 감지를 위해)
            initial_files = set(os.listdir(self.download_directory))

            # 버튼 클릭 전 요청 초기화 (Selenium Wire)
            del self.driver.requests

            button.click()
            print("  버튼 클릭 완료.")

            # 특정 POST 요청이 발생할 때까지 기다립니다.
            try:
                # 'fileDown'이 포함된 POST 요청을 기다림
                WebDriverWait(self.driver, timeout).until(
                    lambda driver: any('fileDown' in r.url and r.method == 'POST' for r in driver.requests)
                )
                print("  PDF 다운로드 관련 POST 요청 감지됨.")
            except TimeoutException:
                print(f"  경고: {timeout}초 내에 PDF 다운로드 POST 요청이 감지되지 않았습니다. 파일 다운로드 대기 시도.")
                # 요청이 감지되지 않아도 실제 파일 다운로드가 시작될 수 있으므로 계속 진행

            # 파일 다운로드를 기다립니다.
            downloaded_file_path = self._wait_for_download(initial_files, timeout=timeout)
            if downloaded_file_path:
                return downloaded_file_path
            else:
                print("  경고: 파일 다운로드 경로를 얻지 못했습니다. 네트워크 요청에서 링크를 찾거나 직접 다운로드되지 않을 수 있습니다.")
                return None  # 파일 다운로드가 감지되지 않으면 None 반환

        except TimeoutException:
            print(f"  오류: XPath '{button_xpath}'의 버튼을 {timeout}초 내에 찾거나 클릭할 수 없습니다.")
            return None
        except StaleElementReferenceException:
            print(f"  오류: XPath '{button_xpath}'의 버튼이 StaleElementReferenceException 발생. DOM이 변경되었을 수 있습니다.")
            return None
        except Exception as e:
            print(f"  버튼 클릭 및 링크 추출 중 예상치 못한 오류 발생: {e}")
            return None

    def get_pdf_download_payload(self, button_xpath: str, timeout: int = 10):
        """
        XPath로 버튼을 클릭하고 해당 POST 요청의 페이로드를 반환합니다.
        실제 PDF 링크가 아닌, PDF 다운로드에 사용되는 요청의 바디를 추출합니다.
        여기서 모든 로깅이 이루어집니다.
        """
        try:
            button = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, button_xpath))
            )
            print(f"  버튼 클릭 시도 (페이로드 추출용): {button_xpath}")

            # 버튼 클릭 전 모든 이전 요청 기록을 지웁니다.
            # 이렇게 해야 현재 클릭으로 발생한 요청만 깔끔하게 확인할 수 있습니다.
            del self.driver.requests

            button.click()
            print("  버튼 클릭 완료.")

            # 사용자가 정의한 URL 필터 패턴을 포함하는 POST 요청을 기다림
            # WebDriverWait을 사용하여 요청이 발생할 때까지 기다립니다.
            target_request = None
            try:
                WebDriverWait(self.driver, timeout).until(
                    lambda driver: any(
                        r.method == 'POST'
                        and (self.url_filter_pattern is None or self.url_filter_pattern in r.url)
                        for r in driver.requests
                    )
                )
                # 요청 목록을 역순으로 탐색하여 가장 최근의 일치하는 요청을 찾습니다.
                for req in reversed(self.driver.requests):
                    if req.method == 'POST' and (self.url_filter_pattern is None or self.url_filter_pattern in req.url):
                        target_request = req
                        break
            except TimeoutException:
                # 요청이 시간 내에 감지되지 않았을 때의 처리
                print(f"  오류: 지정된 패턴 '{self.url_filter_pattern}'을 포함하는 POST 요청이 {timeout}초 내에 감지되지 않았습니다.")
                return None

            if target_request:
                # 최종적으로 찾은 요청에 대한 정보를 출력합니다.
                print(f"  [최종 감지된 요청] URL: {target_request.url}")
                try:
                    decoded_payload = target_request.body.decode('utf-8')
                    print(f"  [최종 감지된 요청] Payload: {decoded_payload}")
                    return decoded_payload
                except UnicodeDecodeError:
                    print(f"  [최종 감지된 요청] Payload (바이너리 데이터): {target_request.body[:50]}...")
                    return "BINARY_PAYLOAD"
                except Exception as e:
                    print(f"  [최종 감지된 요청] Payload 디코딩 오류: {e}")
                    return None
            else:
                print(f"  경고: 지정된 패턴 '{self.url_filter_pattern}'을 포함하는 PDF 다운로드 POST 요청 페이로드를 찾을 수 없습니다.")
                return None

        except TimeoutException:
            print(f"  오류: XPath '{button_xpath}'의 버튼을 {timeout}초 내에 찾거나 클릭할 수 없습니다.")
            return None
        except StaleElementReferenceException:
            print(f"  오류: XPath '{button_xpath}'의 버튼이 StaleElementReferenceException 발생. DOM이 변경되었을 수 있습니다.")
            return None
        except Exception as e:
            print(f"  버튼 클릭 및 페이로드 추출 중 예상치 못한 오류 발생: {e}")
            return None

    def _is_url_live(self, url, timeout=None):
        if timeout is None:
            timeout = self.request_timeout

        if not url:
            return False

        # 로컬 경로는 이 함수에서 검증하지 않음 (항상 유효하다고 간주)
        if "://" not in url and os.path.isabs(url):
            return True

        if not self.verify_url_liveness:  # 검증 비활성화 시, 기본적인 웹 URL 형식인지 정도만 확인
            if "://" in url:
                return True
            # print(f"  [_is_url_live] 검증 비활성화, 그러나 유효한 URL 형식 아님: {url}")
            return False

        # verify_url_liveness=True인 경우 실제 HEAD 요청 검증
        try:
            response = requests.head(url, timeout=timeout, allow_redirects=True)
            if not response.ok:
                print(f"  [_is_url_live] 검증실패: URL 응답 오류 (상태 코드: {response.status_code}): {url}")
                return False

            content_type = response.headers.get('Content-Type', '').lower()
            # Content-Disposition도 확인하여 PDF 파일명을 명시하는지 검토 가능
            # content_disposition = response.headers.get('Content-Disposition', '').lower()
            # is_disposition_pdf = 'filename=' in content_disposition and '.pdf' in content_disposition

            is_pdf_content_type = 'application/pdf' in content_type
            is_url_ends_with_pdf = url.lower().endswith('.pdf')

            # PDF로 판단할 조건: URL이 .pdf로 끝나거나, Content-Type이 application/pdf인 경우
            if is_url_ends_with_pdf or is_pdf_content_type:  # or is_disposition_pdf:
                return True
            else:
                # API URL과 같은 경우, Content-Type이 application/json 등일 수 있음
                print(f"  [_is_url_live] 검증실패: URL은 유효(2xx)하나 PDF 콘텐츠 아님 (Content-Type: {content_type}, URL: {url})")
                return False
        except requests.exceptions.Timeout:
            print(f"  [_is_url_live] 검증실패: URL 유효성 확인 중 Timeout ({timeout}초): {url}")
            return False
        except requests.exceptions.RequestException as e:
            print(f"  [_is_url_live] 검증실패: URL 유효성 확인 중 오류 발생 ({url}): {e}")
            return False

    def get_pdf_url_via_network_interception(self, pdf_trigger_element_xpath):
        print(f"[Network Interception with Selenium Wire] 시작 - XPath: {pdf_trigger_element_xpath}")
        try:
            del self.driver.requests

            if self.download_directory and os.path.isdir(self.download_directory):
                files_before_click = set(os.listdir(self.download_directory))
            else:
                files_before_click = set()

            try:
                trigger_element = WebDriverWait(self.driver, self.element_wait_timeout).until(
                    EC.element_to_be_clickable((By.XPATH, pdf_trigger_element_xpath))
                )
                self.driver.execute_script("arguments[0].click();", trigger_element)
            except TimeoutException:
                print(f"  [SW Interception] 요소 찾기/클릭 실패 (Timeout: {self.element_wait_timeout}s): {pdf_trigger_element_xpath}")
                return None
            except Exception as e_click:
                print(f"  [SW Interception] 요소 클릭 중 오류: {e_click} (XPath: {pdf_trigger_element_xpath})")
                return None

            time.sleep(3)

            current_url_after_click = self.driver.current_url
            if current_url_after_click.lower().endswith(".pdf"):  # .pdf로 끝나면 우선적으로 고려
                if self._is_url_live(current_url_after_click):
                    print(f"  [SW Interception] 클릭 후 URL이 실제 PDF임: {current_url_after_click}")
                    return current_url_after_click

            time.sleep(1)
            for request_num in range(len(self.driver.requests) - 1, -1, -1):
                request = self.driver.requests[request_num]
                if request.response:
                    response_url = request.url

                    # API 호출로 보이는 URL 패턴 필터링 (더 많은 패턴 추가 가능)
                    api_patterns = ["/api/", "dataserviceid=", "pageid="]
                    is_api_call_pattern = any(pattern in response_url.lower() for pattern in api_patterns)
                    if is_api_call_pattern:
                        # print(f"    [SW Log] API 호출로 보이는 URL 건너뜀: {response_url}")
                        continue

                    content_type = request.response.headers.get('Content-Type', '').lower()
                    content_disposition = request.response.headers.get('Content-Disposition', '').lower()

                    is_pdf_mime = 'application/pdf' in content_type
                    is_pdf_disposition = 'filename=' in content_disposition and '.pdf' in content_disposition

                    if request.response.status_code == 200 and \
                       (response_url.lower().endswith('.pdf') or is_pdf_disposition or is_pdf_mime):
                        if self._is_url_live(response_url):
                            print(f"  [SW Interception] Selenium Wire 요청에서 PDF URL 발견 및 검증 성공: {response_url}")
                            return response_url

            start_time = time.time()
            download_check_timeout = 30
            check_interval = 1
            while time.time() - start_time < download_check_timeout:
                current_loop_url = self.driver.current_url
                if current_loop_url.lower().endswith(".pdf"):  # .pdf로 끝나는지만 먼저 확인
                    if self._is_url_live(current_loop_url):
                        print(f"  [SW Interception] 로컬 다운로드 감지 중 현재 URL이 PDF로 변경됨: {current_loop_url}")
                        return current_loop_url

                if self.download_directory and os.path.isdir(self.download_directory):
                    current_files_in_loop = set(os.listdir(self.download_directory))
                    potential_new_pdfs = [
                        f for f in current_files_in_loop
                        if f.lower().endswith(".pdf") and f not in files_before_click
                    ]
                    if potential_new_pdfs:
                        new_pdf_file = potential_new_pdfs[0]
                        file_path = os.path.join(self.download_directory, new_pdf_file)
                        print(f"  [SW Interception] 로컬 다운로드 감지 성공: {file_path}")
                        return file_path
                time.sleep(check_interval)

            if self.download_directory and os.path.isdir(self.download_directory):
                final_files = set(os.listdir(self.download_directory))
                final_new_pdfs = [
                    f for f in final_files
                    if f.lower().endswith(".pdf") and f not in files_before_click
                ]
                if final_new_pdfs:
                    new_pdf_file = final_new_pdfs[0]
                    file_path = os.path.join(self.download_directory, new_pdf_file)
                    print(f"  [SW Interception] 최종 확인에서 로컬 다운로드 감지 성공: {file_path}")
                    return file_path

            print(f"  [SW Interception] 모든 방법 실패 - XPath: {pdf_trigger_element_xpath}")
            return None
        except Exception as e:
            print(f"네트워크 가로채기(SW) 전체 실행 중 오류: {e} (XPath: {pdf_trigger_element_xpath})")
            return None

    def extract_pdf_link(self, target_url, pdf_trigger_element_xpath):
        pdf_url_found = None
        try:
            if pdf_trigger_element_xpath:
                pdf_url_found = self.get_pdf_url_via_network_interception(pdf_trigger_element_xpath)

            if pdf_url_found:
                print(f"PdfLinkExtractor: 최종 추출된 PDF 링크/경로: {pdf_url_found}")
            return pdf_url_found
        except Exception as e:
            print(f"PDF 링크 추출 중 오류: {e}")
            return None
