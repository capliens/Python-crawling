import sqlite3
import os
import glob


def merge_sqlite_databases_with_explicit_schema(source_folder, target_db_path, table_name):
    """
    특정 폴더 내의 모든 SQLite 데이터베이스 파일에서 지정된 테이블의 데이터를 읽어와
    새로운 대상 SQLite 데이터베이스 파일의 동일한 테이블에 합칩니다.
    대상 테이블 스키마를 명시적으로 정의하며, 'id'는 자동 할당,
    'product_code'는 NULL 허용, UNIQUE 제약 조건 충돌 시 'INSERT OR IGNORE'를 사용합니다.
    디버깅을 위해 상세한 로그를 출력합니다.

    Args:
        source_folder (str): SQLite DB 파일들이 있는 폴더 경로.
        target_db_path (str): 합쳐진 데이터가 저장될 대상 SQLite DB 파일 경로.
        table_name (str): 합칠 테이블의 이름 (예: 'insurance_docs').
    """

    print(f"--- 데이터베이스 병합 시작 ---")
    print(f"소스 폴더: '{source_folder}'")
    print(f"대상 DB 파일: '{target_db_path}'")
    print(f"병합할 테이블: '{table_name}'")

    # 1. 대상 데이터베이스 연결 (없으면 생성)
    target_conn = sqlite3.connect(target_db_path)
    target_cursor = target_conn.cursor()

    # 2. 대상 테이블 스키마 명시적 정의
    # 사용자님이 제공해주신 스키마를 기반으로 작성.
    # id는 AUTOINCREMENT, product_code는 NOT NULL 없음.
    # UNIQUE 제약 조건 포함.
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT,
        product_name TEXT,
        product_code TEXT,
        document_type TEXT,
        sales_period TEXT,
        scraped_at TIMESTAMP,
        link TEXT,
        UNIQUE(company_name, product_name, product_code, document_type, sales_period, link)
    );
    """
    try:
        target_cursor.execute(create_table_sql)
        target_conn.commit()
        print(f"\n대상 DB에 '{table_name}' 테이블이 생성되었거나 이미 존재합니다.")
        print(f"새로운 'id' 값은 자동으로 할당됩니다.")
        print(f"UNIQUE 제약 조건 충돌 시 행은 무시됩니다 (INSERT OR IGNORE).")
    except sqlite3.Error as e:
        print(f"오류: 대상 테이블 '{table_name}' 생성 중 발생: {e}")
        target_conn.close()
        return

    # 3. 소스 폴더의 모든 SQLite DB 파일 찾기
    extensions = ["*.db", "*.sqlite", "*.sqlite3"]
    db_files = []
    for ext in extensions:
        db_files.extend(glob.glob(os.path.join(source_folder, ext)))

    db_files.sort()  # 파일 목록을 정렬하여 처리 순서를 예측 가능하게 함

    if not db_files:
        print(f"경고: '{source_folder}' 폴더에 지원되는 확장자를 가진 SQLite DB 파일이 없습니다. (지원: {', '.join(extensions)})")
        target_conn.close()
        return

    print(f"\n총 {len(db_files)}개의 SQLite DB 파일 발견:")
    for i, f in enumerate(db_files):
        print(f"  {i + 1}. {os.path.basename(f)}")

    # 4. 삽입을 위한 컬럼 이름 및 플레이스홀더 준비
    # id 컬럼은 자동 할당되므로, 삽입 시에는 제외합니다.
    columns_for_insert = [
        "company_name", "product_name", "product_code", "document_type",
        "sales_period", "scraped_at", "link"
    ]
    placeholders = ', '.join(['?' for _ in columns_for_insert])
    insert_sql = f"INSERT OR IGNORE INTO {table_name} ({', '.join(columns_for_insert)}) VALUES ({placeholders})"

    # 5. 각 소스 DB에서 데이터 읽어와 대상 DB에 삽입
    total_rows_read_overall = 0
    total_rows_inserted_overall = 0  # 실제로 삽입된 행 (UNIQUE 제약 조건으로 인해 무시될 수 있음)

    for i, db_file in enumerate(db_files):
        print(f"\n--- {i + 1}/{len(db_files)} 처리 중: '{os.path.basename(db_file)}' ---")
        try:
            source_conn = sqlite3.connect(db_file)
            source_cursor = source_conn.cursor()

            # 테이블이 존재하는지 확인
            source_cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
            if not source_cursor.fetchone():
                print(f"  경고: '{os.path.basename(db_file)}'에 테이블 '{table_name}'이(가) 존재하지 않습니다. 이 파일은 스킵합니다.")
                source_conn.close()
                continue

            # 데이터 추출 (id 컬럼 제외, 순서가 중요하므로 명시적으로 컬럼 나열)
            select_columns_sql = ', '.join(columns_for_insert)
            source_cursor.execute(f"SELECT {select_columns_sql} FROM {table_name}")
            rows_to_insert = source_cursor.fetchall()

            if rows_to_insert:
                print(f"  '{os.path.basename(db_file)}'에서 총 {len(rows_to_insert)}개의 행을 읽었습니다.")
                total_rows_read_overall += len(rows_to_insert)

                # INSERT OR IGNORE 실행
                target_cursor.executemany(insert_sql, rows_to_insert)
                target_conn.commit()

                # INSERT OR IGNORE 후 실제로 삽입된 행 수를 정확히 알기 어려움
                # 여기서는 삽입 시도된 행 수를 출력하고, 최종 카운트로 확인
                print(f"  '{len(rows_to_insert)}' 행 삽입 시도 완료 (UNIQUE 충돌 시 무시).")
                # total_rows_inserted_overall은 최종 확인에서 업데이트될 것임

            else:
                print(f"  '{os.path.basename(db_file)}'의 '{table_name}'에는 삽입할 데이터가 없습니다.")

        except sqlite3.Error as e:
            print(f"  오류: '{os.path.basename(db_file)}' 처리 중 발생: {e}")
        finally:
            if 'source_conn' in locals() and source_conn:
                source_conn.close()

    # 최종적으로 대상 DB의 행 수를 확인
    target_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    final_row_count = target_cursor.fetchone()[0]

    print(f"\n--- 병합 완료 보고서 ---")
    print(f"소스 DB에서 읽어와 삽입 시도된 총 행 수: {total_rows_read_overall}")
    print(f"최종 '{target_db_path}'의 '{table_name}'에는 총 {final_row_count} 행이 있습니다.")
    print(f"--- 데이터베이스 병합 종료 ---")


# --- 실제 사용 부분 (이 부분만 실행하세요) ---
if __name__ == "__main__":
    # 이 부분만 사용자 환경에 맞게 수정하세요.
    source_directory = "DB모음"  # DB 파일들이 있는 폴더 경로 (스크립트 기준 상대 경로)
    output_database = "link2.db"     # 합쳐진 데이터가 저장될 DB 파일 이름 (스크립트 기준 상대 경로)
    table_to_merge = "insurance_docs"  # 합칠 테이블 이름

    # 기존 link2.db 파일이 있다면 삭제 (새로운 병합을 위해)
    if os.path.exists(output_database):
        os.remove(output_database)
        print(f"기존 '{output_database}' 삭제 완료.")

    # 병합 함수 호출
    merge_sqlite_databases_with_explicit_schema(source_directory, output_database, table_to_merge)

    # 합쳐진 DB 내용 확인 (선택 사항)
    print("\n--- 합쳐진 데이터베이스 내용 확인 (샘플 10개) ---")
    try:
        conn_merged = sqlite3.connect(output_database)
        cursor_merged = conn_merged.cursor()
        cursor_merged.execute(f"SELECT * FROM {table_to_merge} ORDER BY id LIMIT 10")
        merged_data = cursor_merged.fetchall()
        for row in merged_data:
            print(row)
        print(f"총 {table_to_merge} 테이블의 행 수: {cursor_merged.execute(f'SELECT COUNT(*) FROM {table_to_merge}').fetchone()[0]}")
    except sqlite3.Error as e:
        print(f"최종 DB 확인 중 오류 발생: {e}")
    finally:
        if 'conn_merged' in locals() and conn_merged:
            conn_merged.close()
