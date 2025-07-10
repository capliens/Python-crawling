import os
import re
import requests
import urllib.parse
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
        self.downloaded_files = []
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
            time.sleep(0.5)
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

            initial_files = set(os.listdir(self.download_directory))

            del self.driver.requests

            # Selenium의 .click() 대신 JavaScript를 사용하여 클릭
            self.driver.execute_script("arguments[0].click();", button)
            print("  버튼 클릭 완료.")

            try:
                WebDriverWait(self.driver, timeout).until(
                    lambda driver: any('fileDown' in r.url and r.method == 'POST' for r in driver.requests)
                )
                print("  PDF 다운로드 관련 POST 요청 감지됨.")
            except TimeoutException:
                print(f"  경고: {timeout}초 내에 PDF 다운로드 POST 요청이 감지되지 않았습니다. 파일 다운로드 대기 시도.")

            downloaded_file_path = self._wait_for_download(initial_files, timeout=timeout)
            if downloaded_file_path:
                return downloaded_file_path
            else:
                print("  경고: 파일 다운로드 경로를 얻지 못했습니다. 네트워크 요청에서 링크를 찾거나 직접 다운로드되지 않을 수 있습니다.")
                return None

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

            del self.driver.requests

            # Selenium의 .click() 대신 JavaScript를 사용하여 클릭
            self.driver.execute_script("arguments[0].click();", button)
            print("  버튼 클릭 완료.")

            target_request = None
            try:
                WebDriverWait(self.driver, timeout).until(
                    lambda driver: any(
                        r.method == 'POST'
                        and (self.url_filter_pattern is None or self.url_filter_pattern in r.url)
                        for r in driver.requests
                    )
                )
                for req in reversed(self.driver.requests):
                    if req.method == 'POST' and (self.url_filter_pattern is None or self.url_filter_pattern in req.url):
                        target_request = req
                        break
            except TimeoutException:
                print(f"  오류: 지정된 패턴 '{self.url_filter_pattern}'을 포함하는 POST 요청이 {timeout}초 내에 감지되지 않았습니다.")
                return None

            if target_request:
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

        if "://" not in url and os.path.isabs(url):
            return True

        if not self.verify_url_liveness:
            if "://" in url:
                return True
            return False

        try:
            response = requests.head(url, timeout=timeout, allow_redirects=True)
            if not response.ok:
                print(f"  [_is_url_live] 검증실패: URL 응답 오류 (상태 코드: {response.status_code}): {url}")
                return False

            content_type = response.headers.get('Content-Type', '').lower()
            is_pdf_content_type = 'application/pdf' in content_type
            is_url_ends_with_pdf = url.lower().endswith('.pdf')

            if is_url_ends_with_pdf or is_pdf_content_type:
                return True
            else:
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
                # Selenium의 .click() 대신 JavaScript를 사용하여 클릭
                self.driver.execute_script("arguments[0].click();", trigger_element)
            except TimeoutException:
                print(f"  [SW Interception] 요소 찾기/클릭 실패 (Timeout: {self.element_wait_timeout}s): {pdf_trigger_element_xpath}")
                return None
            except Exception as e_click:
                print(f"  [SW Interception] 요소 클릭 중 오류: {e_click} (XPath: {pdf_trigger_element_xpath})")
                return None

            time.sleep(3)

            current_url_after_click = self.driver.current_url
            if current_url_after_click.lower().endswith(".pdf"):
                if self._is_url_live(current_url_after_click):
                    print(f"  [SW Interception] 클릭 후 URL이 실제 PDF임: {current_url_after_click}")
                    return current_url_after_click

            time.sleep(1)
            for request_num in range(len(self.driver.requests) - 1, -1, -1):
                request = self.driver.requests[request_num]
                if request.response:
                    response_url = request.url

                    api_patterns = ["/api/", "dataserviceid=", "pageid="]
                    is_api_call_pattern = any(pattern in response_url.lower() for pattern in api_patterns)
                    if is_api_call_pattern:
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
                if current_loop_url.lower().endswith(".pdf"):
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
