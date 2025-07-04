import time
import os
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class PdfLinkExtractor:
    def __init__(self, driver, download_directory=None, verify_url_liveness=True, element_wait_timeout=15, request_timeout=15):  # verify_url_liveness 기본값을 True로 변경
        self.driver = driver
        self.download_dir = download_directory
        self.verify_url_liveness = verify_url_liveness
        self.element_wait_timeout = element_wait_timeout
        self.request_timeout = request_timeout
        print(
            f"PdfLinkExtractor initialized (Selenium Wire mode). Verify Liveness: {self.verify_url_liveness}, Element Wait: {self.element_wait_timeout}s, Request Timeout: {self.request_timeout}s, Download Dir: {self.download_dir}")

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

            if self.download_dir and os.path.isdir(self.download_dir):
                files_before_click = set(os.listdir(self.download_dir))
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

                if self.download_dir and os.path.isdir(self.download_dir):
                    current_files_in_loop = set(os.listdir(self.download_dir))
                    potential_new_pdfs = [
                        f for f in current_files_in_loop
                        if f.lower().endswith(".pdf") and f not in files_before_click
                    ]
                    if potential_new_pdfs:
                        new_pdf_file = potential_new_pdfs[0]
                        file_path = os.path.join(self.download_dir, new_pdf_file)
                        print(f"  [SW Interception] 로컬 다운로드 감지 성공: {file_path}")
                        return file_path
                time.sleep(check_interval)

            if self.download_dir and os.path.isdir(self.download_dir):
                final_files = set(os.listdir(self.download_dir))
                final_new_pdfs = [
                    f for f in final_files
                    if f.lower().endswith(".pdf") and f not in files_before_click
                ]
                if final_new_pdfs:
                    new_pdf_file = final_new_pdfs[0]
                    file_path = os.path.join(self.download_dir, new_pdf_file)
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

    def click_and_get_download_link(self, pdf_trigger_element_xpath):
        """
        지정된 XPath의 요소를 클릭하고, 다운로드된 PDF 파일의 로컬 경로를 반환합니다.
        다운로드 디렉토리가 설정되어 있어야 로컬 파일 감지가 작동합니다.
        """
        print(f"클릭 후 다운로드 링크/경로 가져오기 시작 - XPath: {pdf_trigger_element_xpath}")

        if not self.download_dir or not os.path.isdir(self.download_dir):
            print(f"  [Download Link] 다운로드 디렉토리가 설정되지 않았거나 유효하지 않습니다: {self.download_dir}")
            return None

        files_before_click = set(os.listdir(self.download_dir))

        try:
            trigger_element = WebDriverWait(self.driver, self.element_wait_timeout).until(
                EC.element_to_be_clickable((By.XPATH, pdf_trigger_element_xpath))
            )
            self.driver.execute_script("arguments[0].click();", trigger_element)
            print(f"  [Download Link] 요소 클릭 완료: {pdf_trigger_element_xpath}")
        except TimeoutException:
            print(f"  [Download Link] 요소 찾기/클릭 실패 (Timeout: {self.element_wait_timeout}s): {pdf_trigger_element_xpath}")
            return None
        except Exception as e_click:
            print(f"  [Download Link] 요소 클릭 중 오류: {e_click} (XPath: {pdf_trigger_element_xpath})")
            return None

        # 다운로드 완료를 기다립니다.
        start_time = time.time()
        download_check_timeout = 120  # 다운로드 대기 시간 (초)를 120초로 늘림
        check_interval = 1  # 파일 존재 여부 확인 간격 (초)

        while time.time() - start_time < download_check_timeout:
            current_files = set(os.listdir(self.download_dir))
            new_files = current_files - files_before_click

            for f in new_files:
                file_path = os.path.join(self.download_dir, f)
                # PDF 파일이고, 다운로드가 완료된 것으로 보이는지 확인 (예: .crdownload 확장자가 없는지)
                # 추가: 파일 크기가 0보다 큰지 확인
                if f.lower().endswith(".pdf") and not f.endswith(".crdownload") and os.path.getsize(file_path) > 0:
                    print(f"  [Download Link] 로컬 다운로드 감지 성공: {file_path}")
                    return file_path
            time.sleep(check_interval)

        print(f"  [Download Link] 지정된 시간 내에 PDF 다운로드를 감지하지 못했습니다. (Timeout: {download_check_timeout}s)")
        return None


if __name__ == "__main__":
    # from seleniumwire import webdriver
    # from selenium.webdriver.chrome.options import Options
    # chrome_options = Options()
    pass
