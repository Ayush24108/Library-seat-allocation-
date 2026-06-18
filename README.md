# TIET Library Seat Occupancy System

A full-stack, responsive library seat management system built for the UCS310 Database Management System course project. 

The project replicates Oracle SQL sequences, procedures, and trigger logics using a lightweight SQLite database and a Python Flask backend.

---

## 🚀 Technologies Used
* **Frontend**: HTML5, CSS3 (Vanilla), JavaScript (Vanilla, Async Fetch APIs)
* **Backend**: Python 3, Flask, Flask-CORS
* **Database**: SQLite3 (relational database mapping the target Oracle PL/SQL schema)

---

## 🗄️ Database Schema Mapping

The system utilizes five interconnected tables mimicking the primary Oracle design:
1. `student`: Holds student records (`student_id` PK, name, course).
2. `floor`: Manages library floors, capacity limits, and statuses (`floor_id` PK, occupancy counts, floor details).
3. `seat`: Represents individual seats on floors (`seat_id` PK, `floor_id` FK, number, status).
4. `allocation`: Maps active and past student seating history (`allocation_id` PK, references `student` and `seat`, entry/exit timestamps).
5. `scan_log`: Audit trail of scans (`scan_id` PK, student references, scan type, scan time).

---

## ⚙️ Running the Project Locally

### 1. Install Dependencies
Make sure you have Python 3 installed. Install Flask and CORS using pip:
```bash
pip install flask flask-cors
```

### 2. Initialize the Database
Run the setup script to create tables, populate default floors, and seed sample student records:
```bash
python init_db.py
```
This generates the SQLite file `library.db`.

### 3. Run the App
Start the Flask web server:
```bash
python app.py
```

### 4. Open the Interface
Navigate to **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your web browser. Alternatively, you can double-click **`index.html`** directly from your file system.

---

## 📂 Project Structure
```text
├── Code/                      # Academic reports and pdf code versions
├── README.md                  # Project documentation (this file)
├── .gitignore                 # Files excluded from git tracking
├── index.html                 # Dynamic frontend dashboard interface
├── app.py                     # Flask backend API server and DB operations
├── init_db.py                 # SQLite database setup and seeding script
├── library.db                 # SQLite database (generated at runtime, ignored by git)
├── Queries(1).sql             # Original Oracle PL/SQL scripts
└── DBMS-QUERIES.txt           # SQL statements dump
```
