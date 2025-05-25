import google.generativeai as genai
import os
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
from urllib.parse import urlparse
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException

# --- 1. Gemini API 키 설정 (환경 변수 권장) ---
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

# --- 2. Selenium 웹 드라이버 도구 함수 정의 ---
driver_instance = None


def _get_driver():
    global driver_instance
    if driver_instance is None:
        try:
            # ChromeDriverManager().install()이 자동으로 ChromeDriver를 다운로드하고 경로를 반환합니다.
            service = Service(ChromeDriverManager().install())
        except Exception as e:
            # webdriver-manager가 실패했을 때의 예외 처리 (수동 경로 지정 백업 등)
            print(f"WebDriverManager 설치 오류: {e}")
            print(
                "수동으로 ChromeDriver 경로를 지정해 보세요. 예: service = Service(executable_path='./chromedriver')")
            raise  # 오류를 다시 발생시켜 상위 호출자에게 알립니다.

        chrome_options = Options()
        # chrome_options.add_argument("--headless") # 필요시 주석 해제 (백그라운드 실행)
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--start-maximized")  # 브라우저 창 최대화

        driver_instance = webdriver.Chrome(
            service=service, options=chrome_options)
    return driver_instance


def open_browser_and_navigate(url: str) -> str:
    try:
        driver = _get_driver()
        driver.get(url)
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script(
                'return document.readyState') == 'complete'
        )
        time.sleep(2)
        return f"Successfully navigated to {url}. Current page title: {driver.title}"
    except Exception as e:
        return f"Error opening browser or navigating to {url}: {e}"


# --- 요소 찾기 헬퍼 함수 분리 (최적화) ---
def _find_element(by_type: str, value: str):
    driver = _get_driver()
    wait = WebDriverWait(driver, 10)
    if by_type == 'id':
        return wait.until(EC.presence_of_element_located((By.ID, value)))
    elif by_type == 'name':
        return wait.until(EC.presence_of_element_located((By.NAME, value)))
    elif by_type == 'xpath':
        return wait.until(EC.presence_of_element_located((By.XPATH, value)))
    elif by_type == 'css_selector':
        return wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, value)))
    elif by_type == 'class_name':
        return wait.until(EC.presence_of_element_located((By.CLASS_NAME, value)))
    else:
        raise ValueError(f"Unsupported by_type for single element: {by_type}")


def _find_elements(by_type: str, value: str):
    driver = _get_driver()
    wait = WebDriverWait(driver, 10)
    if by_type == 'id':
        # ID는 일반적으로 유일하지만, find_elements를 사용하여 리스트 반환 일관성 유지
        return driver.find_elements(By.ID, value)
    elif by_type == 'name':
        return driver.find_elements(By.NAME, value)
    elif by_type == 'xpath':
        return driver.find_elements(By.XPATH, value)
    elif by_type == 'css_selector':
        return driver.find_elements(By.CSS_SELECTOR, value)
    elif by_type == 'class_name':
        return driver.find_elements(By.CLASS_NAME, value)
    else:
        raise ValueError(
            f"Unsupported by_type for multiple elements: {by_type}")


def click_element(by_type: str, value: str) -> str:
    driver = _get_driver()
    initial_url = driver.current_url
    initial_dom_hash = hash(driver.page_source)

    try:
        element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((getattr(By, by_type.upper()), value))
        )
        driver.execute_script("arguments[0].click();", element)
        time.sleep(3)

        current_url = driver.current_url
        current_dom_hash = hash(driver.page_source)

        if current_url != initial_url:
            change_status = f"URL changed from {initial_url} to {current_url}."
        elif current_dom_hash != initial_dom_hash:
            change_status = "DOM content changed significantly."
        else:
            change_status = "No significant URL or DOM change detected after click."

        return f"Successfully clicked element found by {by_type}='{value}'. {change_status}"

    except Exception as e:
        return f"Error clicking element by {by_type}='{value}': {e}"


def get_element_text(by_type: str, value: str) -> str:
    try:
        element = _find_element(by_type, value)
        return element.text
    except Exception as e:
        return f"Error getting text from element by {by_type}='{value}': {e}"


def get_all_links_on_page() -> str:
    driver = _get_driver()
    try:
        links = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.TAG_NAME, 'a')))
        link_urls = [link.get_attribute('href')
                     for link in links if link.get_attribute('href')]
        return json.dumps(link_urls)
    except Exception as e:
        return f"Error getting all links: {e}"


def close_browser() -> str:
    global driver_instance
    if driver_instance:
        driver_instance.quit()
        driver_instance = None
        return "Browser closed successfully."
    return "No active browser session to close."


# --- 새로운 반복 기능들 (세분화 및 최적화) ---

def repeat_click(by_type: str, value: str, count: int = 1) -> str:
    """
    지정된 요소를 'count' 횟수만큼 클릭합니다.
    """
    results = []
    for i in range(count):
        print(
            f"[DEBUG] Repeating click (iteration {i + 1}/{count}) on {by_type}='{value}'")
        try:
            result = click_element(by_type=by_type, value=value)
            results.append(f"Iteration {i+1}: {result}")
            time.sleep(2)  # 클릭 후 잠시 대기
        except Exception as e:
            results.append(
                f"Error during repetition {i+1} for click on {by_type}='{value}': {e}")
            break  # 오류 발생 시 반복 중단
    return "Repetition results:\n" + "\n".join(results)


def repeat_get_element_text(by_type: str, value: str, count: int = 1) -> str:
    """
    지정된 단일 요소의 텍스트를 'count' 횟수만큼 반복해서 가져옵니다.
    (이 기능은 동적으로 변하는 단일 요소의 텍스트를 모니터링할 때 유용할 수 있습니다.
    여러 요소의 텍스트를 가져올 때는 `repeat_get_elements_text_list`를 사용하는 것이 좋습니다.)
    """
    results = []
    for i in range(count):
        print(
            f"[DEBUG] Repeating get_element_text (iteration {i + 1}/{count}) on {by_type}='{value}'")
        try:
            text = get_element_text(by_type=by_type, value=value)
            results.append(f"Iteration {i+1}: {text}")
            time.sleep(1)  # 대기 시간 추가 (필요에 따라 조절)
        except Exception as e:
            results.append(
                f"Error during repetition {i+1} for get_element_text on {by_type}='{value}': {e}")
            break
    return "Repetition results:\n" + "\n".join(results)


def get_elements_text_list(by_type: str, value: str) -> str:
    """
    지정된 by_type과 value에 해당하는 모든 요소의 텍스트 콘텐츠를 리스트로 반환합니다.
    """
    try:
        elements = _find_elements(by_type, value)
        if not elements:
            return f"No elements found for {by_type}='{value}'."

        # 빈 문자열 제외
        text_list = [elem.text for elem in elements if elem.text.strip()]
        return json.dumps(text_list, ensure_ascii=False)  # 한글 인코딩 문제 방지
    except Exception as e:
        return f"Error getting text list from elements by {by_type}='{value}': {e}"


def repeat_get_elements_text_list(by_type: str, value: str, count: int = 1) -> str:
    """
    지정된 여러 요소의 텍스트 리스트를 'count' 횟수만큼 반복해서 가져옵니다.
    """
    results = []
    for i in range(count):
        print(
            f"[DEBUG] Repeating get_elements_text_list (iteration {i + 1}/{count}) on {by_type}='{value}'")
        try:
            text_list = get_elements_text_list(by_type=by_type, value=value)
            results.append(f"Iteration {i+1}: {text_list}")
            time.sleep(1)  # 대기 시간 추가 (필요에 따라 조절)
        except Exception as e:
            results.append(
                f"Error during repetition {i+1} for get_elements_text_list on {by_type}='{value}': {e}")
            break
    return "Repetition results:\n" + "\n".join(results)


def get_elements_attribute(by_type: str, value: str, attribute_name: str) -> str:
    """
    지정된 by_type과 value에 해당하는 모든 요소의 특정 속성 값을 리스트로 반환합니다.
    """
    try:
        elements = _find_elements(by_type, value)
        if not elements:
            return f"No elements found for {by_type}='{value}'."

        attribute_list = [elem.get_attribute(
            attribute_name) for elem in elements if elem.get_attribute(attribute_name)]
        return json.dumps(attribute_list, ensure_ascii=False)
    except Exception as e:
        return f"Error getting attribute list from elements by {by_type}='{value}' for attribute '{attribute_name}': {e}"


def repeat_get_elements_attribute(by_type: str, value: str, attribute_name: str, count: int = 1) -> str:
    """
    지정된 여러 요소의 특정 속성 값을 'count' 횟수만큼 반복해서 가져옵니다.
    """
    results = []
    for i in range(count):
        print(
            f"[DEBUG] Repeating get_elements_attribute (iteration {i + 1}/{count}) on {by_type}='{value}', attribute='{attribute_name}'")
        try:
            attr_list = get_elements_attribute(
                by_type=by_type, value=value, attribute_name=attribute_name)
            results.append(f"Iteration {i+1}: {attr_list}")
            time.sleep(1)  # 대기 시간 추가 (필요에 따라 조절)
        except Exception as e:
            results.append(
                f"Error during repetition {i+1} for get_elements_attribute on {by_type}='{value}', attribute='{attribute_name}': {e}")
            break
    return "Repetition results:\n" + "\n".join(results)


# --- 3. Gemini 모델에 전달할 도구 정의 (수정된 부분) ---
def define_selenium_tools():
    """
    Gemini 모델이 호출할 수 있는 Selenium 관련 도구들을 정의합니다.
    genai.protos.Tool 및 genai.protos.FunctionDeclaration을 사용합니다.
    """
    return [
        genai.protos.Tool(
            function_declarations=[
                genai.protos.FunctionDeclaration(
                    name="open_browser_and_navigate",
                    description="지정된 URL로 웹 브라우저를 열고 이동합니다.",
                    parameters=genai.protos.Schema(
                        type=genai.protos.Type.OBJECT,
                        properties={
                            "url": genai.protos.Schema(
                                type=genai.protos.Type.STRING,
                                description="접근할 웹 페이지의 전체 URL (예: 'https://www.google.com')."
                            )
                        },
                        required=["url"]
                    )
                )
            ]
        ),
        genai.protos.Tool(
            function_declarations=[
                genai.protos.FunctionDeclaration(
                    name="click_element",
                    description="웹 페이지에서 특정 요소를 찾아 JavaScript를 통해 클릭하고, 클릭 후 URL 또는 DOM 변경 여부를 확인합니다. 버튼, 링크 등에 사용됩니다.",
                    parameters=genai.protos.Schema(
                        type=genai.protos.Type.OBJECT,
                        properties={
                            "by_type": genai.protos.Schema(
                                type=genai.protos.Type.STRING,
                                enum=["id", "name", "xpath",
                                      "css_selector", "class_name"],
                                description="요소를 찾을 기준 (예: 'id', 'css_selector', 'xpath')."
                            ),
                            "value": genai.protos.Schema(
                                type=genai.protos.Type.STRING,
                                description="by_type에 해당하는 요소의 값 (예: 'submit-button', '/html/body/div[1]/a')."
                            )
                        },
                        required=["by_type", "value"]
                    )
                )
            ]
        ),
        genai.protos.Tool(
            function_declarations=[
                genai.protos.FunctionDeclaration(
                    name="get_element_text",
                    description="웹 페이지에서 특정 요소를 찾아 해당 요소의 텍스트 콘텐츠를 반환합니다. (단일 요소)",
                    parameters=genai.protos.Schema(
                        type=genai.protos.Type.OBJECT,
                        properties={
                            "by_type": genai.protos.Schema(
                                type=genai.protos.Type.STRING,
                                enum=["id", "name", "xpath",
                                      "css_selector", "class_name"],
                                description="요소를 찾을 기준 (예: 'name', 'id', 'css_selector')."
                            ),
                            "value": genai.protos.Schema(
                                type=genai.protos.Type.STRING,
                                description="by_type에 해당하는 요소의 값 (예: 'main-title', 'price-tag')."
                            )
                        },
                        required=["by_type", "value"]
                    )
                )
            ]
        ),
        genai.protos.Tool(
            function_declarations=[
                genai.protos.FunctionDeclaration(
                    name="get_all_links_on_page",
                    description="현재 웹 페이지의 모든 링크(href 속성)를 리스트 형태로 반환합니다.",
                    parameters=genai.protos.Schema(
                        type=genai.protos.Type.OBJECT,
                        properties={},
                        required=[]
                    )
                )
            ]
        ),
        genai.protos.Tool(
            function_declarations=[
                genai.protos.FunctionDeclaration(
                    name="close_browser",
                    description="활성화된 웹 브라우저를 닫고 드라이버 세션을 종료합니다.",
                    parameters=genai.protos.Schema(
                        type=genai.protos.Type.OBJECT,
                        properties={},
                        required=[]
                    )
                )
            ]
        ),
        # --- 새로 추가/수정된 반복 및 다중 요소 처리 도구 정의 ---
        genai.protos.Tool(
            function_declarations=[
                genai.protos.FunctionDeclaration(
                    name="repeat_click",
                    description="지정된 요소를 주어진 횟수만큼 클릭합니다. (버튼, 링크 등 반복 클릭)",
                    parameters=genai.protos.Schema(
                        type=genai.protos.Type.OBJECT,
                        properties={
                            "by_type": genai.protos.Schema(
                                type=genai.protos.Type.STRING,
                                enum=["id", "name", "xpath",
                                      "css_selector", "class_name"],
                                description="클릭할 요소를 찾을 기준 (예: 'css_selector')."
                            ),
                            "value": genai.protos.Schema(
                                type=genai.protos.Type.STRING,
                                description="by_type에 해당하는 요소의 값 (예: '.next-page-button')."
                            ),
                            "count": genai.protos.Schema(
                                type=genai.protos.Type.INTEGER,
                                description="액션을 반복할 횟수. 기본값은 1입니다.",

                            )
                        },
                        required=["by_type", "value"]
                    )
                )
            ]
        ),
        genai.protos.Tool(
            function_declarations=[
                genai.protos.FunctionDeclaration(
                    name="repeat_get_element_text",
                    description="지정된 단일 요소의 텍스트를 주어진 횟수만큼 반복해서 가져옵니다. (동적 텍스트 모니터링 시 유용)",
                    parameters=genai.protos.Schema(
                        type=genai.protos.Type.OBJECT,
                        properties={
                            "by_type": genai.protos.Schema(
                                type=genai.protos.Type.STRING,
                                enum=["id", "name", "xpath",
                                      "css_selector", "class_name"],
                                description="텍스트를 가져올 요소를 찾을 기준."
                            ),
                            "value": genai.protos.Schema(
                                type=genai.protos.Type.STRING,
                                description="by_type에 해당하는 요소의 값."
                            ),
                            "count": genai.protos.Schema(
                                type=genai.protos.Type.INTEGER,
                                description="액션을 반복할 횟수. 기본값은 1입니다.",
                            )
                        },
                        required=["by_type", "value"]
                    )
                )
            ]
        ),
        genai.protos.Tool(
            function_declarations=[
                genai.protos.FunctionDeclaration(
                    name="get_elements_text_list",
                    description="지정된 CSS 셀렉터, XPath 등에 해당하는 모든 요소의 텍스트 콘텐츠를 리스트로 반환합니다. (여러 요소)",
                    parameters=genai.protos.Schema(
                        type=genai.protos.Type.OBJECT,
                        properties={
                            "by_type": genai.protos.Schema(
                                type=genai.protos.Type.STRING,
                                enum=["id", "name", "xpath",
                                      "css_selector", "class_name"],
                                description="요소들을 찾을 기준 (예: 'css_selector', 'xpath')."
                            ),
                            "value": genai.protos.Schema(
                                type=genai.protos.Type.STRING,
                                description="by_type에 해당하는 요소들의 값 (예: '.product-name', '//div[@class=\'item\']/h2')."
                            )
                        },
                        required=["by_type", "value"]
                    )
                )
            ]
        ),
        genai.protos.Tool(
            function_declarations=[
                genai.protos.FunctionDeclaration(
                    name="repeat_get_elements_text_list",
                    description="지정된 여러 요소의 텍스트 리스트를 주어진 횟수만큼 반복해서 가져옵니다. (여러 요소의 텍스트를 주기적으로 가져올 때 유용)",
                    parameters=genai.protos.Schema(
                        type=genai.protos.Type.OBJECT,
                        properties={
                            "by_type": genai.protos.Schema(
                                type=genai.protos.Type.STRING,
                                enum=["id", "name", "xpath",
                                      "css_selector", "class_name"],
                                description="텍스트 리스트를 가져올 요소들을 찾을 기준."
                            ),
                            "value": genai.protos.Schema(
                                type=genai.protos.Type.STRING,
                                description="by_type에 해당하는 요소들의 값."
                            ),
                            "count": genai.protos.Schema(
                                type=genai.protos.Type.INTEGER,
                                description="액션을 반복할 횟수. 기본값은 1입니다.",

                            )
                        },
                        required=["by_type", "value"]
                    )
                )
            ]
        ),
        genai.protos.Tool(
            function_declarations=[
                genai.protos.FunctionDeclaration(
                    name="get_elements_attribute",
                    description="지정된 CSS 셀렉터, XPath 등에 해당하는 모든 요소의 특정 속성 값을 리스트로 반환합니다.",
                    parameters=genai.protos.Schema(
                        type=genai.protos.Type.OBJECT,
                        properties={
                            "by_type": genai.protos.Schema(
                                type=genai.protos.Type.STRING,
                                enum=["id", "name", "xpath",
                                      "css_selector", "class_name"],
                                description="요소들을 찾을 기준 (예: 'css_selector', 'xpath')."
                            ),
                            "value": genai.protos.Schema(
                                type=genai.protos.Type.STRING,
                                description="by_type에 해당하는 요소들의 값 (예: '.product-image', '//a/@href')."
                            ),
                            "attribute_name": genai.protos.Schema(
                                type=genai.protos.Type.STRING,
                                description="가져올 속성의 이름 (예: 'href', 'src', 'alt')."
                            )
                        },
                        required=["by_type", "value", "attribute_name"]
                    )
                )
            ]
        ),
        genai.protos.Tool(
            function_declarations=[
                genai.protos.FunctionDeclaration(
                    name="repeat_get_elements_attribute",
                    description="지정된 여러 요소의 특정 속성 값을 주어진 횟수만큼 반복해서 가져옵니다. (여러 요소의 속성 값을 주기적으로 가져올 때 유용)",
                    parameters=genai.protos.Schema(
                        type=genai.protos.Type.OBJECT,
                        properties={
                            "by_type": genai.protos.Schema(
                                type=genai.protos.Type.STRING,
                                enum=["id", "name", "xpath",
                                      "css_selector", "class_name"],
                                description="속성 값을 가져올 요소들을 찾을 기준."
                            ),
                            "value": genai.protos.Schema(
                                type=genai.protos.Type.STRING,
                                description="by_type에 해당하는 요소들의 값."
                            ),
                            "attribute_name": genai.protos.Schema(
                                type=genai.protos.Type.STRING,
                                description="가져올 속성의 이름."
                            ),
                            "count": genai.protos.Schema(
                                type=genai.protos.Type.INTEGER,
                                description="액션을 반복할 횟수. 기본값은 1입니다.",
                            )
                        },
                        required=["by_type", "value", "attribute_name"]
                    )
                )
            ]
        )
    ]


# --- 4. Gemini 에이전트 메인 로직 ---
def selenium_agent():
    model = genai.GenerativeModel(
        'gemini-1.5-flash', tools=define_selenium_tools())
    chat = model.start_chat(history=[])

    print("--- Selenium 기반 웹 상호작용 및 데이터 추출 에이전트 ---")
    print("예시:")
    print("    1. 'https://www.google.com 에 접속해줘.'")
    print("    2. 'https://www.naver.com 에 접속해서 ID가 'query'인 요소의 텍스트를 가져와줘.'")
    print("    3. '현재 페이지의 모든 링크를 가져와줘.'")
    print("    4. 'https://www.naver.com 에 접속해서 CSS 셀렉터가 '#account > a'인 요소를 클릭해줘.' (네이버 로그인 버튼 예시)")
    print("    5. 'CSS 셀렉터가 '.next-page-button'인 요소를 3번 클릭해줘.'")
    print("    6. '클래스 이름이 'product-item'인 모든 요소의 텍스트를 가져와줘.'")
    print("    7. '클래스 이름이 'product-price'인 모든 요소의 텍스트를 5번 반복해서 가져와줘.'")
    print("    8. 'XPath가 '//img'인 모든 요소의 'src' 속성 값을 가져와줘.'")
    print("    9. 'XPath가 '//a'인 모든 요소의 'href' 속성 값을 2번 반복해서 가져와줘.'")
    print("    10. '브라우저 닫아줘.'")
    print("---------------------------------------")
    print("('종료'를 입력하면 에이전트가 종료됩니다.)")

    while True:
        user_input = input("\n당신: ")
        if user_input.lower() == '종료':
            close_browser()
            print("에이전트를 종료합니다.")
            break

        try:
            response = chat.send_message(user_input)

            # 디버깅을 위한 raw response 출력
            print(
                f"[DEBUG] 모델의 raw response: {response.candidates[0].content}")

            if hasattr(response.candidates[0].content, 'parts') and \
               response.candidates[0].content.parts and \
               hasattr(response.candidates[0].content.parts[0], 'function_call') and \
               response.candidates[0].content.parts[0].function_call:

                function_call = response.candidates[0].content.parts[0].function_call
                function_name = function_call.name
                function_args = {k: v for k, v in function_call.args.items()}

                print(f"[DEBUG] 모델이 '{function_name}' 함수 호출을 요청했습니다.")
                print(f"[DEBUG] 인자: {function_args}")

                available_functions = {
                    "open_browser_and_navigate": open_browser_and_navigate,
                    "click_element": click_element,
                    "get_element_text": get_element_text,
                    "get_all_links_on_page": get_all_links_on_page,
                    "close_browser": close_browser,
                    "repeat_click": repeat_click,  # 새 함수 추가
                    "repeat_get_element_text": repeat_get_element_text,  # 새 함수 추가
                    "get_elements_text_list": get_elements_text_list,
                    "repeat_get_elements_text_list": repeat_get_elements_text_list,  # 새 함수 추가
                    "get_elements_attribute": get_elements_attribute,
                    "repeat_get_elements_attribute": repeat_get_elements_attribute  # 새 함수 추가
                }

                if function_name in available_functions:
                    tool_function = available_functions[function_name]
                    tool_output = tool_function(**function_args)
                    print(f"[DEBUG] 함수 실행 결과: {tool_output}")

                    final_response = chat.send_message(
                        {"function_response": {
                            "name": function_name,
                            "response": {"output": tool_output}
                        }}
                    )
                    print(f"에이전트: {final_response.text}")
                else:
                    print(f"에이전트: 알 수 없는 함수 호출: {function_name}")
            else:
                print(f"에이전트: {response.text}")

        except Exception as e:
            print(f"오류 발생: {e}")
            close_browser()


if __name__ == "__main__":
    selenium_agent()
