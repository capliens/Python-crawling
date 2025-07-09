import os
import re
import urllib.parse  # 이 모듈은 더 이상 사용하지 않지만, 일단 남겨둡니다. shinhanez.py에서 사용될 것이기 때문입니다.
from seleniumwire import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
import time


class PdfLinkExtractor:
    def __init__(self, driver: webdriver.Chrome, download_directory: str = None):
        self.driver = driver
        self.download_directory = download_directory
        self.driver.request_interceptor = self._interceptor
        self.downloaded_files = []  # 다운로드된 파일 경로 저장
        print(f"PdfLinkExtractor 초기화. 다운로드 디렉토리: {self.download_directory}")

    def _interceptor(self, request):
        """
        Request interceptor to log POST requests, particularly for PDF downloads.
        """
        if request.method == 'POST' and 'fileDown' in request.url:
            print(f"  [Interceptor] PDF 다운로드 POST 요청 감지: {request.url}")
            # 페이로드 전체를 로깅하는 것은 너무 길 수 있으므로, 간략하게 변경하거나 제거할 수 있습니다.
            print(f"  [Interceptor] Request Body (Payload): {request.body.decode('utf-8')}")

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
        이 함수는 범용적으로 페이로드를 추출하는 역할만 수행합니다.
        """
        try:
            button = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, button_xpath))
            )
            print(f"  버튼 클릭 시도 (페이로드 추출용): {button_xpath}")

            # 버튼 클릭 전 요청 초기화
            del self.driver.requests

            button.click()
            print("  버튼 클릭 완료.")

            # 'fileDown'이 포함된 POST 요청의 응답을 기다림
            WebDriverWait(self.driver, timeout).until(
                lambda driver: any('fileDown' in r.url and r.method == 'POST' for r in driver.requests)
            )

            for request in self.driver.requests:
                if 'fileDown' in request.url and request.method == 'POST':
                    print(f"  [페이로드 추출기] PDF 다운로드 POST 요청 페이로드 감지: {request.body.decode('utf-8')}")
                    return request.body.decode('utf-8')  # 페이로드 반환

            print("  경고: 'fileDown' POST 요청 페이로드를 찾을 수 없습니다.")
            return None

        except TimeoutException:
            print(f"  오류: XPath '{button_xpath}'의 버튼을 {timeout}초 내에 찾거나 클릭할 수 없거나, 'fileDown' POST 요청이 감지되지 않았습니다.")
            return None
        except StaleElementReferenceException:
            print(f"  오류: XPath '{button_xpath}'의 버튼이 StaleElementReferenceException 발생. DOM이 변경되었을 수 있습니다.")
            return None
        except Exception as e:
            print(f"  버튼 클릭 및 페이로드 추출 중 예상치 못한 오류 발생: {e}")
            return None
