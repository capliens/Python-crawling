import sqlite3
from datetime import datetime


class DatabaseManager:
    def __init__(self, db_name="_web_data.db"):
        self.db_name = db_name
        self.conn = None
        self.cursor = None

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        self._create_table_if_not_exists()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.commit()
            self.conn.close()

    def _create_table_if_not_exists(self):
        if self.cursor:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS insurance_docs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT,
                    product_name TEXT,
                    product_code TEXT,
                    document_type TEXT,
                    sales_period TEXT,
                    scraped_at TIMESTAMP,
                    link TEXT,
                    UNIQUE(company_name, product_name, product_code,
                           document_type, sales_period, link)
                );
            """)

    def save_data(self, structured_rows):
        if self.cursor and structured_rows:
            try:
                self.cursor.executemany("""
                    INSERT OR IGNORE INTO insurance_docs (
                        company_name, product_name, product_code,
                        document_type, sales_period, scraped_at, link
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, structured_rows)
                print(f"{len(structured_rows)}건 저장 완료")
                return len(structured_rows)
            except sqlite3.Error as e:
                print(f"DB 저장 중 오류 발생: {e}")
                return 0
        elif not structured_rows:
            print("저장할 데이터가 없습니다.")
            return 0
        else:
            print("DB 연결이 초기화되지 않았습니다.")
            return 0


# ------------------- 예시 사용법 -------------------
# 이 부분은 DatabaseManager 클래스를 사용하는 예시이며,
# 실제 다른 스크립트에서는 이 클래스를 import 하여 사용합니다.
if __name__ == '__main__':
    # 예시 데이터 (원래 코드의 DB손해보험 데이터 처리 로직을 모방)
    all_data_example = [
        ("상품A", "2025-01-01~2025-12-31", ("약관", "http://example.com/docA"), ("설명서", "http://example.com/descA")),
        ("상품B", "2025-06-01~", ("약관", "http://example.com/docB"))
    ]

    structured_rows_example = []
    scraped_time_example = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for row_example in all_data_example:
        if len(row_example) < 2:
            continue
        title_example, date_example = row_example[:2]
        for item_example in row_example[2:]:
            if isinstance(item_example, tuple):
                doc_type_example, link_example = item_example
                structured_rows_example.append([
                    "예시회사",         # company_name
                    title_example,     # product_name
                    "EX001",           # product_code (예시)
                    doc_type_example,  # document_type
                    date_example,      # sales_period
                    scraped_time_example,
                    link_example
                ])

    # DatabaseManager 사용
    with DatabaseManager(db_name="example_usage.db") as db_manager:
        db_manager.save_data(structured_rows_example)

    # 다른 스크립트에서 상속하여 사용하는 예시
    class MyDataSaver(DatabaseManager):
        def __init__(self, db_name="my_custom_data.db"):
            super().__init__(db_name)

        def process_and_save_my_data(self, my_raw_data):
            # 여기에서 my_raw_data를 structured_rows 형태로 가공하는 로직을 구현
            processed_data = []
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for item in my_raw_data:
                # 예시: item이 (회사명, 상품명, 링크) 형태라고 가정
                if len(item) == 3:
                    processed_data.append([
                        item[0],  # company_name
                        item[1],  # product_name
                        "N/A",   # product_code
                        "일반문서",  # document_type
                        "상시",  # sales_period
                        current_time,
                        item[2]  # link
                    ])

            # 부모 클래스의 save_data 메서드 호출
            with self as db:  # __enter__ 및 __exit__ 활용
                return db.save_data(processed_data)

    # MyDataSaver 사용 예시
    custom_data_to_save = [
        ("커스텀회사1", "커스텀상품1", "http://custom.com/1"),
        ("커스텀회사2", "커스텀상품2", "http://custom.com/2"),
    ]

    saver = MyDataSaver()
    save_count = saver.process_and_save_my_data(custom_data_to_save)
    if save_count > 0:
        print(f"MyDataSaver를 통해 {save_count}건 저장 완료.")

    print("\n이제 다른 Python 스크립트에서 from neoali.DB_save import DatabaseManager 와 같이 import 한 후,")
    print("DatabaseManager 클래스를 직접 사용하거나 상속받아 사용할 수 있습니다.")
    print("예: class SpecificScraperDB(DatabaseManager): ...")
