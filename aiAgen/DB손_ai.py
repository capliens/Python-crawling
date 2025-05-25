import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from collections import deque


def _get_user_input_with_ai_guidance(prompt):
    """
    (개념적) Gemini AI 에이전트가 사용자 입력을 유도하는 부분입니다.
    실제 Gemini API가 연동된다면 이곳에서 모델을 호출하여 더 지능적인
    대화 및 가이드라인 제시가 가능합니다.
    현재는 단순히 사용자 입력을 받는 것으로 대체합니다.
    """
    return input(prompt)


def initialize_webdriver():
    """Selenium WebDriver를 초기화하고 반환합니다."""
    try:
        service = Service(ChromeDriverManager().install())
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # GUI 없이 백그라운드에서 실행
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        driver = webdriver.Chrome(service=service, options=options)
        print("WebDriver가 성공적으로 초기화되었습니다.")
        return driver
    except WebDriverException as e:
        print(f"WebDriver 초기화 중 오류 발생: {e}")
        print("크롬 드라이버가 제대로 설치되었는지, 크롬 브라우저가 최신 버전인지 확인해주세요.")
        return None


def fetch_page_content_selenium(driver, url, wait_time=5, scroll_count=0):
    """Selenium을 사용하여 페이지 내용을 가져옵니다 (동적 로딩 지원)."""
    try:
        print(f"페이지 로딩 중: {url}")
        driver.get(url)

        # 페이지 로딩 대기 (필요에 따라 더 구체적인 EC를 사용할 수 있음)
        WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(1)  # 추가적인 안정성을 위한 대기

        # 스크롤링 (동적 콘텐츠 로딩을 위해)
        for _ in range(scroll_count):
            driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # 스크롤 후 콘텐츠 로딩 대기

        return driver.page_source
    except TimeoutException:
        print(f"Error: Timeout while loading {url}")
        return None
    except WebDriverException as e:
        print(f"Error during page fetch {url}: {e}")
        return None


def parse_html(html_content):
    """HTML 내용을 BeautifulSoup 객체로 파싱합니다."""
    return BeautifulSoup(html_content, 'html.parser')


def extract_links(soup, base_url):
    """HTML에서 모든 링크를 추출합니다."""
    links = []
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        # 절대 경로로 변환
        if not href.startswith(('http://', 'https://')):
            href = requests.compat.urljoin(base_url, href)
        # 같은 도메인 내의 링크만 수집 (선택 사항)
        # requests.compat.urlparse 대신 urllib.parse를 사용하는 것이 더 일반적입니다.
        from urllib.parse import urlparse
        if urlparse(href).netloc == urlparse(base_url).netloc:
            links.append(href)
    return links


def extract_content(soup, extraction_rules):
    """
    사용자가 정의한 규칙에 따라 콘텐츠를 추출합니다.
    extraction_rules: { 'key': { 'css_selector': 'h1.title', 'attribute': 'text' } }
    """
    extracted_data = {}
    for key, rule in extraction_rules.items():
        if 'css_selector' in rule:
            elements = soup.select(rule['css_selector'])
        else:
            elements = []

        if elements:
            if rule.get('attribute') == 'text':
                extracted_data[key] = [elem.get_text(
                    strip=True) for elem in elements]
            elif rule.get('attribute') == 'href':
                extracted_data[key] = [
                    elem.get('href') for elem in elements if elem.get('href')]
            elif rule.get('attribute') == 'src':
                extracted_data[key] = [
                    elem.get('src') for elem in elements if elem.get('src')]
            else:
                extracted_data[key] = [str(elem)
                                       for elem in elements]  # 태그 전체를 문자열로 저장
        else:
            extracted_data[key] = []
    return extracted_data


def interactive_web_crawler_selenium():
    """대화형 웹 크롤링을 Selenium을 사용하여 시작합니다."""
    print("안녕하세요! Gemini AI 에이전트가 Selenium을 사용하여 웹 크롤링을 도와드리겠습니다.")

    driver = initialize_webdriver()
    if not driver:
        print("크롤링을 시작할 수 없습니다. WebDriver 초기화에 실패했습니다.")
        return

    start_url = _get_user_input_with_ai_guidance(
        "어떤 웹사이트에서 정보를 수집하고 싶으신가요? (URL을 입력해주세요): ")
    max_depth_str = _get_user_input_with_ai_guidance(
        "몇 단계까지 링크를 따라 크롤링할까요? (숫자를 입력하세요, 0은 현재 페이지만): ")
    try:
        max_depth = int(max_depth_str)
    except ValueError:
        print("잘못된 입력입니다. 크롤링 깊이를 0으로 설정합니다.")
        max_depth = 0

    scroll_count_str = _get_user_input_with_ai_guidance(
        "동적으로 로드되는 콘텐츠를 위해 페이지를 몇 번 스크롤할까요? (숫자 입력, 0은 스크롤 안 함): ")
    try:
        scroll_count = int(scroll_count_str)
    except ValueError:
        print("잘못된 입력입니다. 스크롤 횟수를 0으로 설정합니다.")
        scroll_count = 0

    print("\n어떤 정보를 추출하고 싶으신가요?")
    print("예시: '제목', '본문', '이미지 링크' 등. 여러 개를 쉼표로 구분하여 입력할 수 있습니다.")
    print("CSS 선택자를 사용하여 더 구체적인 규칙을 지정할 수 있습니다.")
    print("예시: '제목 (h1.title)', '본문 (div.article-content)', '이미지 (img[alt])'")
    desired_info_str = _get_user_input_with_ai_guidance(
        "추출할 정보의 키워드 또는 규칙을 입력하세요: ")

    extraction_rules = {}
    info_items = [item.strip() for item in desired_info_str.split(',')]

    for item in info_items:
        match_css = re.match(r'(.+)\s*\((.+)\)', item)  # '키워드 (선택자)' 형식 매칭
        if match_css:
            key = match_css.group(1).strip()
            selector_str = match_css.group(2).strip()
            attribute = 'text'  # 기본은 text
            if 'href' in selector_str.lower() or 'a' in selector_str.lower():
                attribute = 'href'
            elif 'src' in selector_str.lower() or 'img' in selector_str.lower():
                attribute = 'src'
            extraction_rules[key] = {
                'css_selector': selector_str, 'attribute': attribute}
        else:
            # 일반 키워드에 대한 기본 규칙 (Selenium에서는 CSS 선택자가 더 유용)
            if item.lower() == '제목':
                extraction_rules['제목'] = {
                    'css_selector': 'h1, h2, .title', 'attribute': 'text'}
            elif item.lower() == '본문':
                extraction_rules['본문'] = {
                    'css_selector': 'p, div.content, article', 'attribute': 'text'}
            elif item.lower() == '링크':
                extraction_rules['링크'] = {
                    'css_selector': 'a', 'attribute': 'href'}
            elif item.lower() == '이미지':
                extraction_rules['이미지'] = {
                    'css_selector': 'img', 'attribute': 'src'}
            else:
                print(
                    f"'{item}'에 대한 구체적인 추출 규칙을 알 수 없습니다. 해당 키워드를 무시합니다. (CSS 선택자를 사용해주세요)")

    visited_urls = set()
    urls_to_visit = deque([(start_url, 0)])  # (URL, 현재 깊이)

    all_extracted_data = {}

    while urls_to_visit:
        current_url, current_depth = urls_to_visit.popleft()

        if current_url in visited_urls:
            continue

        if current_depth > max_depth:
            continue

        print
