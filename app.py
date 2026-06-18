from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), 'library.db')
STATIC_DIR = os.path.dirname(__file__)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

# Helper functions simulating Oracle Procedures
def db_allocate_seat_floor(student_id, floor_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. Check if student exists
        cursor.execute("SELECT student_name FROM student WHERE student_id = ?", (student_id,))
        student = cursor.fetchone()
        if not student:
            return False, "Student does not exist"
        
        # 2. Check if student is already inside
        cursor.execute("SELECT COUNT(*) FROM allocation WHERE student_id = ? AND exit_time IS NULL", (student_id,))
        inside_count = cursor.fetchone()[0]
        if inside_count > 0:
            return False, f"Student {student_id} ({student['student_name']}) is already inside"
        
        # 3. Check if floor is OPEN
        cursor.execute("SELECT status FROM floor WHERE floor_id = ?", (floor_id,))
        floor = cursor.fetchone()
        if not floor:
            return False, "Floor does not exist"
        if floor['status'] != 'OPEN':
            return False, "Selected floor is currently CLOSED"
            
        # 4. Find the first free seat
        cursor.execute("SELECT seat_id, seat_no FROM seat WHERE floor_id = ? AND status = 'FREE' ORDER BY seat_no LIMIT 1", (floor_id,))
        free_seat = cursor.fetchone()
        if not free_seat:
            return False, "No seats available on selected floor"
            
        seat_id = free_seat['seat_id']
        seat_no = free_seat['seat_no']
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Start transaction (SQLite does this automatically with execute on write, but commit at end)
        # 5. Insert allocation
        cursor.execute("INSERT INTO allocation (student_id, seat_id, entry_time) VALUES (?, ?, ?)", (student_id, seat_id, now_str))
        
        # 6. Update seat status
        cursor.execute("UPDATE seat SET status = 'OCCUPIED' WHERE seat_id = ?", (seat_id,))
        
        # 7. Update floor occupied count
        cursor.execute("UPDATE floor SET occupied_seats = occupied_seats + 1 WHERE floor_id = ?", (floor_id,))
        
        # 8. Log the scan activity
        cursor.execute("INSERT INTO scan_log (student_id, scan_type, scan_time, floor_id) VALUES (?, 'ENTRY', ?, ?)", (student_id, now_str, floor_id))
        
        conn.commit()
        return True, {
            "student_id": student_id,
            "student_name": student['student_name'],
            "floor_id": floor_id,
            "seat_id": seat_id,
            "seat_no": seat_no,
            "time": now_str
        }
    except Exception as e:
        conn.rollback()
        return False, f"Transaction error: {str(e)}"
    finally:
        conn.close()

def db_release_seat(student_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. Check if student exists
        cursor.execute("SELECT student_name FROM student WHERE student_id = ?", (student_id,))
        student = cursor.fetchone()
        if not student:
            return False, "Student does not exist"
            
        # 2. Get active allocation
        cursor.execute("SELECT allocation_id, seat_id FROM allocation WHERE student_id = ? AND exit_time IS NULL", (student_id,))
        alloc = cursor.fetchone()
        if not alloc:
            return False, f"No active seat allocation found for {student_id} ({student['student_name']})"
            
        alloc_id = alloc['allocation_id']
        seat_id = alloc['seat_id']
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 3. Find floor of the seat
        cursor.execute("SELECT floor_id, seat_no FROM seat WHERE seat_id = ?", (seat_id,))
        seat = cursor.fetchone()
        floor_id = seat['floor_id']
        seat_no = seat['seat_no']
        
        # Start updates
        # 4. Mark Exit Time in Allocation
        cursor.execute("UPDATE allocation SET exit_time = ? WHERE allocation_id = ?", (now_str, alloc_id))
        
        # 5. Free the seat
        cursor.execute("UPDATE seat SET status = 'FREE' WHERE seat_id = ?", (seat_id,))
        
        # 6. Decrement Floor occupied seats
        cursor.execute("UPDATE floor SET occupied_seats = occupied_seats - 1 WHERE floor_id = ?", (floor_id,))
        
        # 7. Log scan activity
        cursor.execute("INSERT INTO scan_log (student_id, scan_type, scan_time, floor_id) VALUES (?, 'EXIT', ?, ?)", (student_id, now_str, floor_id))
        
        conn.commit()
        return True, {
            "student_id": student_id,
            "student_name": student['student_name'],
            "floor_id": floor_id,
            "seat_id": seat_id,
            "seat_no": seat_no,
            "time": now_str
        }
    except Exception as e:
        conn.rollback()
        return False, f"Transaction error: {str(e)}"
    finally:
        conn.close()

# API Routes

@app.route('/')
def serve_index():
    return send_from_directory(STATIC_DIR, 'index.html')

@app.route('/api/status', methods=['GET'])
def get_status():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(total_seats), SUM(occupied_seats) FROM floor")
    row = cursor.fetchone()
    total = row[0] or 0
    occupied = row[1] or 0
    free_seats = total - occupied
    conn.close()
    return jsonify({
        "total": total,
        "occupied": occupied,
        "free": free_seats
    })

@app.route('/api/floors', methods=['GET'])
def get_floors():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM floor ORDER BY priority_order")
    floors = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(floors)

@app.route('/api/floors/<int:floor_id>/seats', methods=['GET'])
def get_floor_seats(floor_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM seat WHERE floor_id = ? ORDER BY seat_no", (floor_id,))
    seats = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(seats)

@app.route('/api/students', methods=['GET'])
def get_students():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM student ORDER BY student_id")
    students = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(students)

@app.route('/api/students', methods=['POST'])
def add_student():
    data = request.json
    student_id = data.get('student_id')
    student_name = data.get('student_name')
    course = data.get('course')
    
    if not student_id or not student_name or not course:
        return jsonify({"success": False, "error": "All fields are required"}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO student VALUES (?, ?, ?)", (student_id, student_name, course))
        conn.commit()
        return jsonify({"success": True, "message": f"Student {student_name} added successfully"})
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "error": f"Student ID '{student_id}' already exists"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/students/<student_id>', methods=['DELETE'])
def delete_student(student_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if student exists
        cursor.execute("SELECT student_name FROM student WHERE student_id = ?", (student_id,))
        student = cursor.fetchone()
        if not student:
            return jsonify({"success": False, "error": "Student not found"}), 404
            
        # Check if student is currently checked in (seat occupied)
        cursor.execute("SELECT seat_id FROM allocation WHERE student_id = ? AND exit_time IS NULL", (student_id,))
        alloc = cursor.fetchone()
        if alloc:
            # Release their seat first
            db_release_seat(student_id)
            
        cursor.execute("DELETE FROM student WHERE student_id = ?", (student_id,))
        conn.commit()
        return jsonify({"success": True, "message": f"Student {student['student_name']} deleted successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/logs', methods=['GET'])
def get_logs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT l.scan_id, l.student_id, s.student_name, l.scan_type, l.scan_time, l.floor_id, f.floor_name
        FROM scan_log l
        JOIN student s ON l.student_id = s.student_id
        LEFT JOIN floor f ON l.floor_id = f.floor_id
        ORDER BY l.scan_time DESC, l.scan_id DESC
        LIMIT 100
    """)
    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(logs)

@app.route('/api/scan', methods=['POST'])
def scan_card():
    data = request.json
    student_id = data.get('student_id')
    scan_type = data.get('scan_type')
    floor_id = data.get('floor_id')
    
    if not student_id or not scan_type:
        return jsonify({"success": False, "error": "Missing student_id or scan_type"}), 400
        
    scan_type = scan_type.upper()
    
    if scan_type == 'ENTRY':
        if not floor_id:
            return jsonify({"success": False, "error": "Floor selection is required for entry"}), 400
        success, result = db_allocate_seat_floor(student_id, int(floor_id))
    elif scan_type == 'EXIT':
        success, result = db_release_seat(student_id)
    else:
        return jsonify({"success": False, "error": "Invalid scan type. Use ENTRY or EXIT"}), 400
        
    if success:
        return jsonify({"success": True, "data": result})
    else:
        return jsonify({"success": False, "error": result}), 400

@app.route('/api/floors/<int:floor_id>/seats/total', methods=['POST'])
def update_floor_seats(floor_id):
    data = request.json
    new_total = data.get('total_seats')
    
    if new_total is None or not isinstance(new_total, int) or new_total < 1 or new_total > 500:
        return jsonify({"success": False, "error": "Seat total must be an integer between 1 and 500"}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check floor
        cursor.execute("SELECT total_seats, occupied_seats FROM floor WHERE floor_id = ?", (floor_id,))
        floor = cursor.fetchone()
        if not floor:
            return jsonify({"success": False, "error": "Floor not found"}), 404
            
        old_total = floor['total_seats']
        occupied = floor['occupied_seats']
        
        if new_total == old_total:
            return jsonify({"success": True, "message": "No change in seats count"})
            
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if new_total > old_total:
            # Add new seats
            new_seats = []
            for seat_no in range(old_total + 1, new_total + 1):
                new_seats.append((floor_id, seat_no, 'FREE'))
            cursor.executemany("INSERT INTO seat (floor_id, seat_no, status) VALUES (?, ?, ?)", new_seats)
            cursor.execute("UPDATE floor SET total_seats = ? WHERE floor_id = ?", (new_total, floor_id))
            
        else:
            # Reducing seats: We need to see if any occupied seats are in the cut range (seat_no > new_total)
            # Find occupied seats in the range to be deleted
            cursor.execute("SELECT seat_id, seat_no FROM seat WHERE floor_id = ? AND seat_no > ? AND status = 'OCCUPIED'", (floor_id, new_total))
            occupied_cut = cursor.fetchall()
            
            # For each occupied seat that is being removed, release it first
            for seat_row in occupied_cut:
                # Find active student allocation for this seat
                cursor.execute("SELECT student_id, allocation_id FROM allocation WHERE seat_id = ? AND exit_time IS NULL", (seat_row['seat_id'],))
                alloc = cursor.fetchone()
                if alloc:
                    # Record exit
                    cursor.execute("UPDATE allocation SET exit_time = ? WHERE allocation_id = ?", (now_str, alloc['allocation_id']))
                    cursor.execute("INSERT INTO scan_log (student_id, scan_type, scan_time, floor_id) VALUES (?, 'EXIT', ?, ?)", 
                                   (alloc['student_id'], now_str, floor_id))
            
            # Delete seat records
            cursor.execute("DELETE FROM seat WHERE floor_id = ? AND seat_no > ?", (floor_id, new_total))
            
            # Calculate new occupied count
            cursor.execute("SELECT COUNT(*) FROM seat WHERE floor_id = ? AND status = 'OCCUPIED'", (floor_id,))
            new_occupied = cursor.fetchone()[0]
            
            cursor.execute("UPDATE floor SET total_seats = ?, occupied_seats = ? WHERE floor_id = ?", (new_total, new_occupied, floor_id))
            
        conn.commit()
        return jsonify({"success": True, "message": f"Successfully updated total seats to {new_total}"})
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/reset', methods=['POST'])
def reset_system():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Clear allocations and scan logs
        cursor.execute("DELETE FROM allocation")
        cursor.execute("DELETE FROM scan_log")
        
        # Reset all seats to FREE
        cursor.execute("UPDATE seat SET status = 'FREE'")
        
        # Reset all floors' occupied_seats to 0
        cursor.execute("UPDATE floor SET occupied_seats = 0")
        
        conn.commit()
        return jsonify({"success": True, "message": "System reset completed. All seats cleared."})
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
