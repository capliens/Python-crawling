import time
import os
import json
import requests
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class PdfLinkExtractor:
    def __init__(self, driver, download_directory=None, verify_url_liveness=True):
        self.driver = driver
        self.download_dir = download_directory
        self.verify_url_liveness = verify_url_liveness

    def _is_url_live(self, url, timeout=5):
        if not url or url.startswith("downloaded:"):  # 로컬 경로나 빈 URL은 검증 불필요 (이제 downloaded: 접두사 없음)
            if "://" not in url and os.path.isabs(url):  # 로컬 경로인지 확인
                return True

        if not self.verify_url_liveness:
            return True

        try:
            response = requests.head(url, timeout=timeout, allow_redirects=True)
            if not response.ok:
                print(f"  [검증실패] URL 응답 오류 (상태 코드: {response.status_code}): {url}")
                return False

            content_type = response.headers.get('Content-Type', '').lower()
            is_pdf_content_type = 'application/pdf' in content_type
            is_url_ends_with_pdf = url.lower().endswith('.pdf')

            if is_url_ends_with_pdf or is_pdf_content_type:
                return True
            else:
                print(f"  [검증실패] URL은 유효(2xx)하나 PDF 콘텐츠 아님 (Content-Type: {content_type}, URL: {url})")
                return False
        except requests.exceptions.Timeout:
            print(f"  [검증실패] URL 유효성 확인 중 Timeout: {url}")
            return False
        except requests.exceptions.RequestException as e:
            print(f"  [검증실패] URL 유효성 확인 중 오류 발생 ({url}): {e}")
            return False

    def get_pdf_url_via_network_interception(self, pdf_trigger_element_xpath):
        try:
            self.driver.execute_cdp_cmd("Network.enable", {})
            if self.download_dir and os.path.isdir(self.download_dir):
                files_before_click = set(os.listdir(self.download_dir))
            else:
                files_before_click = set()

            try:
                trigger_element = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, pdf_trigger_element_xpath))
                )
                self.driver.execute_script("arguments[0].click();", trigger_element)
            except TimeoutException:
                print(f"네트워크 가로채기: XPath '{pdf_trigger_element_xpath}' 요소 찾기/클릭 실패 (Timeout).")
                return None
            except Exception as e_click:
                print(f"네트워크 가로채기: XPath '{pdf_trigger_element_xpath}' 요소 클릭 중 오류: {e_click}")
                return None

            time.sleep(3)

            current_url_after_click = self.driver.current_url
            if self._is_url_live(current_url_after_click):
                if current_url_after_click.lower().endswith(".pdf") or \
                   ('application/pdf' in requests.head(current_url_after_click, timeout=3, allow_redirects=True).headers.get('Content-Type', '').lower()):
                    return current_url_after_click

            time.sleep(3)
            try:
                logs = self.driver.get_log('performance')
                requests_data = {}
                for entry in logs:
                    log = json.loads(entry['message'])['message']
                    method = log.get('method')
                    params = log.get('params', {})
                    if 'Network.requestWillBeSent' == method:
                        requestId = params.get('requestId')
                        requests_data[requestId] = {'request': params.get('request', {}),
                                                    'redirectResponse': params.get('redirectResponse')}
                    elif 'Network.responseReceived' == method:
                        requestId = params.get('requestId')
                        if requestId in requests_data:
                            requests_data[requestId]['response'] = params.get('response', {})

                for req_id, data in requests_data.items():
                    response = data.get('response')
                    if not response:
                        continue
                    response_url = response.get('url', '')
                    if not response_url:
                        continue

                    mime_type = response.get('mimeType', '').lower()
                    headers = response.get('headers', {})
                    status = response.get('status')
                    content_type_header = next((v.lower() for k, v in headers.items() if k.lower() == 'content-type'), '')
                    content_disposition_header = next((v.lower() for k, v in headers.items() if k.lower() == 'content-disposition'), '')

                    is_pdf_mime = 'application/pdf' in mime_type or 'application/pdf' in content_type_header
                    is_pdf_disposition = 'filename=' in content_disposition_header and '.pdf' in content_disposition_header

                    if status == 200 and (response_url.lower().endswith('.pdf') or is_pdf_disposition or is_pdf_mime):
                        if self._is_url_live(response_url):
                            return response_url
            except Exception as e_perf:
                print(f"Performance 로그 분석 중 오류: {e_perf}")

            start_time = time.time()
            download_check_timeout = 30
            check_interval = 1
            while time.time() - start_time < download_check_timeout:
                if self.driver.current_url.lower().endswith(".pdf"):
                    if self._is_url_live(self.driver.current_url):
                        return self.driver.current_url
                if self.download_dir and os.path.isdir(self.download_dir):
                    current_files_in_loop = set(os.listdir(self.download_dir))
                    potential_new_pdfs = [
                        f for f in current_files_in_loop
                        if f.lower().endswith(".pdf") and f not in files_before_click
                    ]
                    if potential_new_pdfs:
                        new_pdf_file = potential_new_pdfs[0]
                        file_path = os.path.join(self.download_dir, new_pdf_file)
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
                    return file_path
            return None
        except Exception as e:
            print(f"네트워크 가로채기 전체 실행 중 오류: {e}")
            return None
        finally:
            try:
                self.driver.execute_cdp_cmd("Network.disable", {})
            except Exception:
                pass

    # def get_pdf_url_via_href(self, pdf_link_element_xpath): # 메서드 삭제
    #     # ... (이전 내용) ...
    #     pass

    def extract_pdf_link(self, target_url, pdf_trigger_element_xpath):  # pdf_link_element_xpath_method2 제거
        pdf_url_found = None
        try:
            # 이제 항상 네트워크 가로채기 방법을 사용
            if pdf_trigger_element_xpath:
                pdf_url_found = self.get_pdf_url_via_network_interception(pdf_trigger_element_xpath)

            if pdf_url_found:
                print(f"PdfLinkExtractor: 최종 추출된 PDF 링크/경로: {pdf_url_found}")
            return pdf_url_found
        except Exception as e:
            print(f"PDF 링크 추출 중 오류: {e}")
            return None


if __name__ == "__main__":
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    driver = None
    pass
