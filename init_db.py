import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'library.db')

def init_db():
    print(f"Initializing database at: {DB_PATH}")
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # Create tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student (
        student_id TEXT PRIMARY KEY,
        student_name TEXT NOT NULL,
        course TEXT NOT NULL
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS floor (
        floor_id INTEGER PRIMARY KEY,
        floor_name TEXT NOT NULL,
        total_seats INTEGER NOT NULL,
        occupied_seats INTEGER DEFAULT 0,
        priority_order INTEGER NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('OPEN', 'CLOSED'))
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS seat (
        seat_id INTEGER PRIMARY KEY AUTOINCREMENT,
        floor_id INTEGER NOT NULL,
        seat_no INTEGER NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('FREE', 'OCCUPIED')),
        FOREIGN KEY (floor_id) REFERENCES floor(floor_id) ON DELETE CASCADE,
        UNIQUE(floor_id, seat_no)
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS allocation (
        allocation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        seat_id INTEGER NOT NULL,
        entry_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        exit_time TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES student(student_id) ON DELETE CASCADE,
        FOREIGN KEY (seat_id) REFERENCES seat(seat_id) ON DELETE CASCADE
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scan_log (
        scan_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        scan_type TEXT NOT NULL CHECK(scan_type IN ('ENTRY', 'EXIT')),
        scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        floor_id INTEGER,
        FOREIGN KEY (student_id) REFERENCES student(student_id) ON DELETE CASCADE
    );
    """)
    
    # Insert initial data if tables are empty
    cursor.execute("SELECT COUNT(*) FROM floor")
    if cursor.fetchone()[0] == 0:
        print("Inserting initial floors...")
        floors = [
            (1, 'Ground Floor', 30, 0, 1, 'OPEN'),
            (2, 'First Floor', 30, 0, 2, 'OPEN'),
            (3, 'Second Floor', 30, 0, 3, 'OPEN'),
            (4, 'Third Floor', 30, 0, 4, 'OPEN'),
            (5, 'Fourth Floor', 30, 0, 5, 'OPEN')
        ]
        cursor.executemany("INSERT INTO floor VALUES (?, ?, ?, ?, ?, ?)", floors)
        
        # Generate seats (30 seats per floor to match visualization)
        print("Generating seats...")
        seats = []
        for floor_id in range(1, 6):
            for seat_no in range(1, 31):
                seats.append((floor_id, seat_no, 'FREE'))
        cursor.executemany("INSERT INTO seat (floor_id, seat_no, status) VALUES (?, ?, ?)", seats)
    
    cursor.execute("SELECT COUNT(*) FROM student")
    if cursor.fetchone()[0] == 0:
        print("Inserting sample students...")
        students = [
            ('STU101', 'Ayush', 'CSE'),
            ('STU102', 'Rahul', 'CSE'),
            ('STU103', 'Ananya', 'ECE'),
            ('STU104', 'Vihaan', 'ME'),
            ('STU105', 'Diya', 'Civil')
        ]
        cursor.executemany("INSERT INTO student VALUES (?, ?, ?)", students)
        
    conn.commit()
    conn.close()
    print("Database initialization completed successfully.")

if __name__ == "__main__":
    init_db()
