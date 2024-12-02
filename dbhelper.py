from sqlite3 import connect, Row, Error

database: str = "libroco.db"

def postprocess(sql: str, params: tuple) -> bool:
    try:
        db = connect(database, timeout=30, check_same_thread=False)  # Adding timeout and thread safety
        cursor = db.cursor()
        cursor.execute(sql, params)
        db.commit()  # Commit changes
        ok: bool = True if cursor.rowcount > 0 else False
        return ok
    except Error as e:
        print(f"SQLite error: {e}")
        db.rollback()  # Rollback in case of an error
        return False
    finally:
        db.close()  # Ensure the connection is closed even if there's an error

def getprocess(sql: str, params: tuple = ()) -> list:
    try:
        db = connect(database, timeout=30, check_same_thread=False)  # Adding timeout and thread safety
        db.row_factory = Row  # Ensure that rows are returned as dictionaries
        cursor = db.cursor()
        cursor.execute(sql, params)
        data = cursor.fetchall()  # Fetch the data
        return data
    except Error as e:
        print(f"SQLite error: {e}")
        return []
    finally:
        db.close()  # Ensure the connection is closed

def add_record(table: str, **kwargs):
    keys = list(kwargs.keys())
    values = list(kwargs.values())
    
    # Build the SQL query
    flds = ",".join([f"`{key}`" for key in keys])  # Column names part
    vals = ",".join(["?" for _ in values])  # Placeholders part
    sql = f"INSERT INTO `{table}` ({flds}) VALUES ({vals})"
    
    return postprocess(sql, tuple(values))  # Pass the values as a tuple

def getall_records(table: str) -> list:
    try:
        db = connect(database, timeout=30, check_same_thread=False)
        db.row_factory = Row  # Ensures rows are returned as Row objects
        cursor = db.cursor()
        sql = f"SELECT * FROM `{table}`"
        cursor.execute(sql)
        data = cursor.fetchall()
        
        # Convert each Row to a dictionary
        return [dict(row) for row in data]  
    except Error as e:
        print(f"SQLite error: {e}")
        return []
    finally:
        db.close()  # Ensure the connection is closed


def insert_request(user_id: int, book_id: int):
    data = {
        "user_id": user_id,
        "book_id": book_id,
    }
    return add_record("requests", **data)  # Use add_record to insert a new request

def get_pending_requests():
    sql = '''
    SELECT books.book_title, books.author, books.genre, requests.request_date, users.username
    FROM requests
    JOIN books ON requests.book_id = books.book_id
    JOIN users ON requests.user_id = users.user_id
    WHERE requests.status = 'Pending'  -- You can filter requests based on status (e.g., Pending, Approved)
    '''
    return getprocess(sql)
