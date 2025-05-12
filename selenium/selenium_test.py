# selenium의 webdriver를 사용하기 위한 import
from selenium import webdriver
# selenium에서 요소를 찾을 때 사용하는 검색 방법을 상수로 정의한 클래스
# from selenium.webdriver.common.by import By
# 페이지 로딩을 기다리는데에 사용할 time 모듈 import
import time

# 별도의 드라이버 설정 없이 바로 Chrome 실행
driver = webdriver.Chrome()
# 크롬 드라이버에 url 주소 넣고 실행
driver.get("https://www.google.com")
# 페이지가 완전히 로딩되도록 3초동안 기다림
time.sleep(3)

#  정보사이트 https://wikidocs.net/149358

# 밑에껀 사이트를 불러와서 링크를 저장하는 방식 (오류있음)
                    if link is None:
                        # original_window = driver.current_window_handle
                        driver.execute_script(
                            "arguments[0].click();", link_element)
                        wait = WebDriverWait(driver, 20)
                        wait.until(EC.new_window_is_opened(
                            driver.window_handles))
                        # 현재 열려있는 모든 창의 핸들을 가져옵니다.
                        all_windows = driver.window_handles
                        new_window_handle = None  # 새 창 핸들을 저장할 변수 초기화

                        # 원래 창이 아닌 다른 핸들을 찾습니다.
                        for window_handle in all_windows:
                            if window_handle != original_window:
                                new_window_handle = window_handle
                                break

                        # 새 창으로 전환합니다.
                        if new_window_handle:  # 새 창이 열렸는지 확인
                            driver.switch_to.window(new_window_handle)
                            # 현재 URL을 가져옵니다.
                            new_url = driver.current_url
                            # 새 창을 닫습니다.
                            driver.close()

                        # 원래 창으로 돌아갑니다.
                        driver.switch_to.window(original_window)

                except NoSuchElementException:
                    pass
                except TimeoutException:
                    current_windows = driver.window_handles
                    for window_handle in current_windows:
                        if window_handle != original_window:
                            driver.switch_to.window(window_handle)
                            driver.close()
                    driver.switch_to.window(original_window)
                    print("err")