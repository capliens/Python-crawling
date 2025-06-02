import time
import os
import json
# from selenium import webdriver # Options, By 등은 직접 임포트하므로 전체 webdriver 임포트 불필요
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException  # TimeoutException 임포트 추가


class PdfLinkExtractor:
    def __init__(self, driver, download_directory=None):
        self.driver = driver
        self.download_dir = download_directory

    def get_pdf_url_via_network_interception(self, pdf_trigger_element_xpath):
        try:
            self.driver.execute_cdp_cmd("Network.enable", {})
            if self.download_dir and os.path.isdir(self.download_dir):
                files_before_click = set(os.listdir(self.download_dir))
            else:
                files_before_click = set()

            try:
                trigger_element = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, pdf_trigger_element_xpath))  # 클릭 가능할 때까지 대기
                )
                self.driver.execute_script("arguments[0].click();", trigger_element)
            except TimeoutException:
                print(f"방법 3: XPath '{pdf_trigger_element_xpath}'에 해당하는 요소를 찾거나 클릭할 수 없습니다 (Timeout).")
                return None
            except Exception as e_click:
                print(f"방법 3: XPath '{pdf_trigger_element_xpath}' 요소 클릭 중 오류: {e_click}")
                return None

            time.sleep(3)

            current_url_after_click = self.driver.current_url
            if current_url_after_click.lower().endswith(".pdf"):
                return current_url_after_click

            time.sleep(3)
            pdf_url_from_network = None
            try:
                logs = self.driver.get_log('performance')
                requests = {}
                for entry in logs:
                    log = json.loads(entry['message'])['message']
                    method = log.get('method')
                    params = log.get('params', {})
                    if 'Network.requestWillBeSent' == method:
                        requestId = params.get('requestId')
                        requests[requestId] = {'request': params.get('request', {}),
                                               'redirectResponse': params.get('redirectResponse')}
                    elif 'Network.responseReceived' == method:
                        requestId = params.get('requestId')
                        if requestId in requests:
                            requests[requestId]['response'] = params.get('response', {})

                for req_id, data in requests.items():
                    response = data.get('response')
                    if not response:
                        continue
                    current_url = response.get('url', '')
                    mime_type = response.get('mimeType', '').lower()
                    headers = response.get('headers', {})
                    status = response.get('status')
                    content_type_header = headers.get('content-type', headers.get('Content-Type', '')).lower()
                    content_disposition_header = headers.get('content-disposition', headers.get('Content-Disposition', '')).lower()
                    is_pdf_mime = 'application/pdf' in mime_type or 'application/pdf' in content_type_header
                    is_pdf_disposition = 'filename=' in content_disposition_header and '.pdf' in content_disposition_header

                    if status == 200 and (is_pdf_mime or is_pdf_disposition):
                        if current_url and current_url.lower().endswith('.pdf'):
                            pdf_url_from_network = current_url
                            break
                        else:
                            pass

                if pdf_url_from_network:
                    return pdf_url_from_network
            except Exception as e_perf:
                print(f"Performance 로그 분석 중 오류: {e_perf}")

            if self.download_dir and os.path.isdir(self.download_dir):
                pass
            else:
                if not hasattr(self, 'files_before_click_for_local_check'):
                    self.files_before_click_for_local_check = set()
                    if self.download_dir and os.path.isdir(self.download_dir):
                        self.files_before_click_for_local_check = set(os.listdir(self.download_dir))
                files_before_click = self.files_before_click_for_local_check

            start_time = time.time()
            download_check_timeout = 30
            check_interval = 1
            while time.time() - start_time < download_check_timeout:
                if self.driver.current_url.lower().endswith(".pdf"):
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
                        return f"downloaded:{file_path}"
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
                    return f"downloaded:{file_path}"
            return None
        except Exception as e:
            print(f"방법 3 실행 중 오류: {e}")
            return None
        finally:
            try:
                self.driver.execute_cdp_cmd("Network.disable", {})
            except Exception:
                pass

    def get_pdf_url_via_href(self, pdf_link_element_xpath):
        try:
            pdf_link_element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, pdf_link_element_xpath))  # 클릭 가능할 때까지 대기
            )
            pdf_url = pdf_link_element.get_attribute('href')

            download_trigger_patterns = [
                'download.do',
                'servlet/download',
                'filedownload',
                '.filedown',
                'downloadfile.jsp'
            ]

            if pdf_url:
                if pdf_url.startswith('/'):
                    from urllib.parse import urlparse
                    parsed_uri = urlparse(self.driver.current_url)
                    base_url = '{uri.scheme}://{uri.netloc}'.format(uri=parsed_uri)
                    pdf_url = base_url + pdf_url

                is_direct_pdf_link = '.pdf' in pdf_url.lower()
                is_download_trigger = any(pattern.lower() in pdf_url.lower() for pattern in download_trigger_patterns)

                if is_direct_pdf_link:
                    return pdf_url
                elif is_download_trigger:
                    return pdf_url
                else:
                    return None
            else:
                return None
        except TimeoutException:  # 요소를 찾지 못하거나 클릭 불가능한 경우
            print(f"방법 2: XPath '{pdf_link_element_xpath}'에 해당하는 요소를 찾거나 클릭할 수 없습니다 (Timeout).")
            return None
        except Exception as e:
            print(f"방법 2 실행 중 오류: {e}")
            return None

    def extract_pdf_link(self, target_url, pdf_trigger_element_xpath_method3, pdf_link_element_xpath_method2):
        pdf_url_found = None
        try:
            if not target_url:
                return None
            self.driver.get(target_url)
            time.sleep(3)

            if pdf_trigger_element_xpath_method3:
                pdf_url_found = self.get_pdf_url_via_network_interception(pdf_trigger_element_xpath_method3)

            if not pdf_url_found and pdf_link_element_xpath_method2:
                pdf_url_found = self.get_pdf_url_via_href(pdf_link_element_xpath_method2)
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
