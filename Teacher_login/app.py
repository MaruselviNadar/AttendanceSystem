from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
)

from flask import send_file, request, jsonify
from openpyxl import Workbook
import mysql.connector
import datetime
import os

from flask_cors import CORS
import mysql.connector

app = Flask(__name__)
app.secret_key = "change_this_to_a_strong_secret_key"

# CORS is not strictly needed if frontend is on same origin,
# but leaving it on is fine.
CORS(app, resources={r"/*": {"origins": "*"}})


def get_db_connection(autocommit=False):
    """Create a new MySQL connection."""
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="123456",
        database="teacher",
        autocommit=autocommit,
    )


# ---------------- LOGIN / DASHBOARD ROUTES ---------------- #

@app.route("/")
def index():
    # Show index page with Teacher / Student options
    return render_template("index.html")


@app.route("/teacher_login")
def teacher_login():
    # Teacher login page
    return render_template("login.html")


@app.route("/student_login")
def student_login():
    # Student login page
    return render_template("student_login.html")



@app.route("/login", methods=["POST"])
def login():
    teacher_id = request.form.get("teacher_id")
    password = request.form.get("password")

    if not teacher_id or not password:
        flash("Please enter both Teacher ID and Password", "error")
        return redirect(url_for("index"))

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute(
        "SELECT id, teacher_id, name, password FROM teachers WHERE teacher_id = %s",
        (teacher_id,),
    )
    user = cur.fetchone()

    cur.close()
    conn.close()

    if user is None:
        flash("Invalid Teacher ID or Password", "error")
        return redirect(url_for("index"))

    # Plain-text password verification
    if user["password"] != password:
        flash("Invalid Teacher ID or Password", "error")
        return redirect(url_for("index"))

    session["teacher_id"] = user["teacher_id"]
    session["teacher_name"] = user["name"]

    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    if "teacher_id" not in session:
        return redirect(url_for("index"))

    # This template should contain your Teacher Dashboard HTML/JS
    return render_template("dashboard.html", name=session["teacher_name"])

#fetch student data
@app.route("/api/students", methods=["GET"])
def get_students_by_dept_year():
    ui_department = request.args.get("department")
    ui_year = request.args.get("year")

    # 🔁 UI → DB mappings
    department_map = {
        "BSCIT": "BSCIT",
        "CS": "CS"
    }

    year_map = {
        "First Year": "1",
        "Second Year": "2",
        "Third Year": "3",
        "FY": "1",
        "SY": "2",
        "TY": "3"
    }

    department = department_map.get(ui_department)
    year = year_map.get(ui_year)

    if not department or not year:
        return jsonify([])

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, name
        FROM students
        WHERE department = %s
          AND year = %s
        ORDER BY roll_no
    """, (department, year))

    students = cursor.fetchall()

    cursor.close()
    db.close()

    return jsonify(students)

@app.route("/api/teacher/subjects")
def get_teacher_subjects():
    if "teacher_id" not in session:
        return jsonify([]), 401

    teacher_id = session["teacher_id"]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            s.id,
            s.subject_name,
            tsm.stream,
            tsm.year,
            tsm.semester
        FROM teacher_subject_mapping tsm
        JOIN subjects s ON s.id = tsm.subject_id
        WHERE tsm.teacher_id = %s
        ORDER BY tsm.stream, tsm.year, s.subject_name
    """, (teacher_id,))

    subjects = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(subjects)

def get_class_teacher_assignment():
    if 'teacher_id' not in session:
        return None

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT stream, year, academic_year
        FROM class_teacher_assignment
        WHERE teacher_id = %s
    """, (session['teacher_id'],))

    result = cur.fetchone()

    cur.close()
    conn.close()

    return result

#basic routing for class teacher
@app.route("/api/teacher/class-teacher-info")
def class_teacher_info():
    info = get_class_teacher_assignment()

    if not info:
        return jsonify({"is_class_teacher": False})

    return jsonify({
        "is_class_teacher": True,
        "stream": info["stream"],
        "year": info["year"],
        "academic_year": info["academic_year"]
    })





@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ---------------- ATTENDANCE API ROUTE ---------------- #

def normalize_datetime(dt_str: str) -> str:
    """
    Convert HTML datetime-local value ('2025-12-05T21:54')
    into MySQL DATETIME format ('2025-12-05 21:54:00').
    """
    if not dt_str:
        return None
    dt_str = dt_str.replace("T", " ")
    if len(dt_str) == 16:  # 'YYYY-MM-DD HH:MM'
        dt_str += ":00"
    return dt_str


"""@app.route("/save_attendance", methods=["POST", "OPTIONS"])
def save_attendance():
    if request.method == "OPTIONS":
        return "", 200

    data = request.get_json()

    lecture_key = data["lecture_key"]
    subject = data["subject"]
    year = data["year"]
    stream = data["stream"]
    lecture_date_time = normalize_datetime(data["lecture_date_time"])
    attendance = data["attendance"]

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            
            INSERT INTO lectures (lecture_key, subject, year, stream, lecture_date_time)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
              subject = VALUES(subject),
              year = VALUES(year),
              stream = VALUES(stream),
              lecture_date_time = VALUES(lecture_date_time)
            ,
            (lecture_key, subject, year, stream, lecture_date_time),
        )

        cur.execute("DELETE FROM attendance WHERE lecture_key = %s", (lecture_key,))

        for student_id, status in attendance.items():
          status = 'P' if status.lower() == 'present' else 'A'
          cur.execute(
        
        INSERT INTO attendance (lecture_key, student_id, status)
        VALUES (%s, %s, %s)
        ,
        (lecture_key, int(student_id), status),
    )


        conn.commit()
        return jsonify({"message": "Attendance saved successfully!"})

    except Exception as e:
        conn.rollback()
        return jsonify({"message": "Error saving attendance", "error": str(e)}), 500

    finally:
        cur.close()
        conn.close()"""
@app.route("/save_attendance", methods=["POST", "OPTIONS"])
def save_attendance():
    if request.method == "OPTIONS":
        return "", 200

    # 1️⃣ Login check
    if "teacher_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()

    lecture_key = data["lecture_key"]
    subject = data["subject"]
    year = (data["year"])
    stream = data["stream"]
    lecture_date_time = normalize_datetime(data["lecture_date_time"])
    attendance = data["attendance"]

    conn = get_db_connection()
    cur = conn.cursor()

    # 2️⃣ ✅ VERIFY subject belongs to teacher
    """cur.execute(
        SELECT 1
        FROM teacher_subject_mapping tsm
        JOIN subjects s ON s.id = tsm.subject_id
        WHERE tsm.teacher_id = %s
          AND s.subject_name = %s
          AND tsm.stream = %s
          AND tsm.year = %s
    , (session["teacher_id"], subject, stream, year))"""
    cur.execute("""
    SELECT 1
    FROM teacher_subject_mapping tsm
    JOIN subjects s ON s.id = tsm.subject_id
    WHERE tsm.teacher_id = %s
      AND s.subject_name = %s
""", (session["teacher_id"], subject))


    if not cur.fetchone():
        cur.close()
        conn.close()
        return jsonify({"error": "Not authorized for this subject"}), 403

    try:
        cur.execute("""
            INSERT INTO lectures (lecture_key, subject, year, stream, lecture_date_time)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                subject = VALUES(subject),
                year = VALUES(year),
                stream = VALUES(stream),
                lecture_date_time = VALUES(lecture_date_time)
        """, (lecture_key, subject, year, stream, lecture_date_time))

        cur.execute("DELETE FROM attendance WHERE lecture_key = %s", (lecture_key,))

        for student_id, status in attendance.items():
            status = 'P' if status.lower() == 'present' else 'A'
            cur.execute("""
                INSERT INTO attendance (lecture_key, student_id, status)
                VALUES (%s, %s, %s)
            """, (lecture_key, int(student_id), status))

        conn.commit()
        return jsonify({"message": "Attendance saved successfully!"})

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()



# ---------------- MAIN ---------------- #


# Database connection
@app.route('/api/monthly_student_report', methods=['POST'])
def monthly_student_report():
    try:
        data = request.json
        month = int(data['month'])
        year = int(data['year'])
        subject = data.get('subject')
        stream = data.get('stream')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
        SELECT 
            s.name AS student,
            COUNT(*) AS total_lectures,
            SUM(a.status='P') AS present,
            SUM(a.status='A') AS absent,
            ROUND(SUM(a.status='P') / COUNT(*) * 100, 2) AS percentage
        FROM attendance a
        JOIN students s ON s.id = a.student_id
        WHERE MONTH(a.date) = %s
          AND YEAR(a.date) = %s
          AND s.stream = %s
          AND a.lecture_key LIKE %s
        GROUP BY s.id, s.name
        """

        lecture_key_pattern = f"{subject}%{stream}%"
        cursor.execute(query, (month, year, stream, lecture_key_pattern))
        results = cursor.fetchall()

        return jsonify(results)

    except Exception as e:
        print("Monthly report error:", e)
        return jsonify({"error": str(e)}), 500

#--------Defaulter--------#

@app.route("/api/defaulter_report", methods=["POST"])
def defaulter_report():
    try:
        data = request.json
        print("DEF DATA:", data)

        if not data.get("from_date") or not data.get("to_date"):
            return jsonify({"error": "Date range required"}), 400

        year = int(data.get("year"))
        stream = data.get("stream")
        threshold = int(data.get("threshold", 75))

        from_date = data["from_date"]+" 00:00:00"
        to_date   = data["to_date"]+" 23:59:59"

        subject = data.get("subject")
        if not subject:
            return jsonify({"error": "Subject required"}), 400


        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
        SELECT
        s.id AS student_id,
        s.name AS student_name,
        COUNT(a.status) AS total_lectures,
        SUM(a.status = 'P') AS present_count,
        ROUND(SUM(a.status = 'P') / COUNT(a.status) * 100, 2) AS percentage
        FROM students s
        JOIN attendance a ON a.student_id = s.id
        JOIN lectures l ON l.lecture_key = a.lecture_key
        WHERE s.year = %s
        AND s.department = %s
        AND l.subject = %s             
        AND l.lecture_date_time BETWEEN %s AND %s
        GROUP BY s.id, s.name
        HAVING percentage < %s
        ORDER BY percentage;    
        """

        cursor.execute(
            query,
            (year, stream, subject, from_date, to_date, threshold)
        )

        result = cursor.fetchall()
        print("DEF RESULT:", result)

        cursor.close()
        conn.close()

        return jsonify(result)

    except Exception as e:
        print("DEF ERROR:", e)
        return jsonify({"error": str(e)}), 500



#--------OverAll Defaulter--------#        

@app.route("/api/Overall_defaulter_report", methods=["POST"])
def OverAll_defaulter_report():
    try:
        data = request.json
        print("DEF DATA:", data)

        if not data.get("from_date") or not data.get("to_date"):
            return jsonify({"error": "Date range required"}), 400

        year = int(data.get("year"))
        stream = data.get("stream")
        threshold = int(data.get("threshold", 75))

        from_date = data["from_date"]+" 00:00:00"
        to_date   = data["to_date"]+" 23:59:59"

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
        SELECT
            s.id AS student_id,
            s.name AS student_name,
            COUNT(a.status) AS total_lectures,
            SUM(a.status='P') AS present_count,
            ROUND(SUM(a.status='P')/COUNT(a.status)*100, 2) AS percentage
        FROM students s
        JOIN attendance a ON a.student_id = s.id
        WHERE s.year = %s
          AND s.department = %s
          AND STR_TO_DATE(
                SUBSTRING_INDEX(a.lecture_key, '_', -1),
                '%Y-%m-%dT%H:%i'
              ) BETWEEN %s AND %s
        GROUP BY s.id, s.name
        HAVING percentage < %s
        """

        cursor.execute(
            query,
            (year, stream, from_date, to_date, threshold)
        )

        result = cursor.fetchall()
        print("DEF RESULT:", result)

        cursor.close()
        conn.close()

        return jsonify(result)

    except Exception as e:
        print("DEF ERROR:", e)
        return jsonify({"error": str(e)}), 500


#---Overall Defaulter Excel Genrator---

@app.route("/api/export_overall_defaulter", methods=["POST"])
def export_overall_defaulter():

    data = request.json
    year = data["year"]
    stream = data["stream"]
    from_date = data["from_date"] + " 00:00:00"
    to_date   = data["to_date"] + " 23:59:59"

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    #Get all subjects
    cursor.execute("""
        SELECT DISTINCT SUBSTRING_INDEX(a.lecture_key,'_TY_',1) AS subject
        FROM attendance a
        JOIN students s ON s.id=a.student_id
        WHERE s.year=%s AND s.department=%s
    """, (year,stream))

    subjects = [r["subject"] for r in cursor.fetchall()]

    #Get attendance data
    cursor.execute("""
        SELECT 
            s.name,
            s.roll_no,
            SUBSTRING_INDEX(a.lecture_key,'_TY_',1) AS subject,
            COUNT(*) AS total,
            SUM(a.status='P') AS present
        FROM students s
        JOIN attendance a ON s.id=a.student_id
        WHERE s.year=%s AND s.department=%s
          AND STR_TO_DATE(SUBSTRING_INDEX(a.lecture_key,'_',-1),'%Y-%m-%dT%H:%i')
              BETWEEN %s AND %s
        GROUP BY s.id, subject
    """, (year,stream,from_date,to_date))

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    students = {}

    for r in rows:
        key = r["roll_no"]

        if key not in students:
            students[key] = {
                "name": r["name"],
                "roll": r["roll_no"],
                "subjects": {s:0 for s in subjects},
                "total_present":0,
                "total_lectures":0
            }

        students[key]["subjects"][r["subject"]] = r["present"]
        students[key]["total_present"] += r["present"]
        students[key]["total_lectures"] += r["total"]

    #Create Excel
    wb = Workbook()
    ws = wb.active

    header = ["Student Name","Roll No"] + subjects + ["Grand Total","Grand %"]
    ws.append(header)

    for s in students.values():
        if s["total_lectures"] == 0:
            continue

        percent = round(s["total_present"]/s["total_lectures"]*100,2)

        if percent < 75:   # only defaulters
            row = [s["name"], s["roll"]]
            for sub in subjects:
                row.append(s["subjects"][sub])
            row.append(s["total_present"])
            row.append(percent)
            ws.append(row)

    filename = "Overall_Defaulters.xlsx"
    wb.save(filename)

    return send_file(filename, as_attachment=True)


#---Overall Report----

@app.route("/api/Overall_report", methods=["POST"])
def OverAll_report():
    try:
        data = request.json
        print("DEF DATA:", data)

        if not data.get("from_date") or not data.get("to_date"):
            return jsonify({"error": "Date range required"}), 400

        year = int(data.get("year"))
        stream = data.get("stream")

        from_date = data["from_date"]+" 00:00:00"
        to_date   = data["to_date"]+" 23:59:59"

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
        SELECT
            s.id AS student_id,
            s.name AS student_name,
            COUNT(a.status) AS total_lectures,
            SUM(a.status='P') AS present_count,
            ROUND(SUM(a.status='P')/COUNT(a.status)*100, 2) AS percentage
        FROM students s
        JOIN attendance a ON a.student_id = s.id
        WHERE s.year = %s
          AND s.department = %s
          AND STR_TO_DATE(
                SUBSTRING_INDEX(a.lecture_key, '_', -1),
                '%Y-%m-%dT%H:%i'
              ) BETWEEN %s AND %s
        GROUP BY s.id, s.name
        """

        cursor.execute(
            query,
            (year, stream, from_date, to_date)
        )

        result = cursor.fetchall()
        print("DEF RESULT:", result)

        cursor.close()
        conn.close()

        return jsonify(result)

    except Exception as e:
        print("DEF ERROR:", e)
        return jsonify({"error": str(e)}), 500

#---Overall Report Excel---

@app.route("/api/export_overall_report", methods=["POST"])
def export_overall_report():

    data = request.json
    year = data["year"]
    stream = data["stream"]
    from_date = data["from_date"] + " 00:00:00"
    to_date   = data["to_date"] + " 23:59:59"

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    #Get all subjects
    cursor.execute("""
        SELECT DISTINCT SUBSTRING_INDEX(a.lecture_key,'_TY_',1) AS subject
        FROM attendance a
        JOIN students s ON s.id=a.student_id
        WHERE s.year=%s AND s.department=%s
    """, (year,stream))

    subjects = [r["subject"] for r in cursor.fetchall()]

    #Get attendance data
    cursor.execute("""
        SELECT 
            s.name,
            s.roll_no,
            SUBSTRING_INDEX(a.lecture_key,'_TY_',1) AS subject,
            COUNT(*) AS total,
            SUM(a.status='P') AS present
        FROM students s
        JOIN attendance a ON s.id=a.student_id
        WHERE s.year=%s AND s.department=%s
          AND STR_TO_DATE(SUBSTRING_INDEX(a.lecture_key,'_',-1),'%Y-%m-%dT%H:%i')
              BETWEEN %s AND %s
        GROUP BY s.id, subject
    """, (year,stream,from_date,to_date))

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    students = {}

    for r in rows:
        key = r["roll_no"]

        if key not in students:
            students[key] = {
                "name": r["name"],
                "roll": r["roll_no"],
                "subjects": {s:0 for s in subjects},
                "total_present":0,
                "total_lectures":0
            }

        students[key]["subjects"][r["subject"]] = r["present"]
        students[key]["total_present"] += r["present"]
        students[key]["total_lectures"] += r["total"]

    #Create Excel
    wb = Workbook()
    ws = wb.active

    header = ["Student Name","Roll No"] + subjects + ["Grand Total","Grand %"]
    ws.append(header)

    for s in students.values():
        if s["total_lectures"] == 0:
            continue

        percent = round(s["total_present"]/s["total_lectures"]*100,2)
        row = [s["name"], s["roll"]]
        for sub in subjects:
            row.append(s["subjects"][sub])
        row.append(s["total_present"])
        row.append(percent)
        ws.append(row)

    filename = "Overall_Defaulters.xlsx"
    wb.save(filename)

    return send_file(filename, as_attachment=True)




if __name__ == "__main__":
    app.run(debug=True)