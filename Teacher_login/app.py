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
        "SELECT id, teacher_id, name, password_hash FROM teachers WHERE teacher_id = %s",
        (teacher_id,),
    )
    user = cur.fetchone()
    cur.close()
    conn.close()

    if user is None:
        flash("Invalid Teacher ID or Password", "error")
        return redirect(url_for("index"))

    # Simple password check (plain text). If you later use hashes,
    # replace this with check_password_hash.
    if user["password_hash"] != password:
        flash("Invalid Teacher ID or Password", "error")
        return redirect(url_for("index"))

    # Successful login → store in session
    session["teacher_id"] = user["teacher_id"]
    session["teacher_name"] = user["name"]

    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    if "teacher_id" not in session:
        return redirect(url_for("index"))

    # This template should contain your Teacher Dashboard HTML/JS
    return render_template("dashboard.html", name=session["teacher_name"])


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


@app.route("/save_attendance", methods=["POST", "OPTIONS"])
def save_attendance():
    # Handle preflight CORS
    if request.method == "OPTIONS":
        return "", 200

    data = request.get_json()

    lecture_key = data["lecture_key"]
    subject = data["subject"]
    year = data["year"]
    stream = data["stream"]
    lecture_date_time = normalize_datetime(data["lecture_date_time"])
    attendance = data["attendance"]  # dict: { "1": "present", "2": "absent", ... }

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Insert / update lecture
        cur.execute(
            """
            INSERT INTO lectures (lecture_key, subject, year, stream, lecture_date_time)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
              subject = VALUES(subject),
              year = VALUES(year),
              stream = VALUES(stream),
              lecture_date_time = VALUES(lecture_date_time)
            """,
            (lecture_key, subject, year, stream, lecture_date_time),
        )

        # Clear existing attendance for this lecture
        cur.execute("DELETE FROM attendance WHERE lecture_key = %s", (lecture_key,))

         # Insert fresh attendance records
        for student_id, status in attendance.items():
         status = 'P' if status.lower() == 'present' else 'A'
         cur.execute(
        """
        INSERT INTO attendance (lecture_key, student_id, status, date)
        VALUES (%s, %s, %s, DATE(%s))
        """,
        (lecture_key, int(student_id), status, lecture_date_time),
    )

        conn.commit()
        return jsonify({"message": "Attendance saved successfully!"})

    except Exception as e:
        conn.rollback()
        return (
            jsonify({"message": "Error saving attendance", "error": str(e)}),
            500,
        )

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


@app.route('/api/defaulter_report', methods=['POST'])
def defaulter_report():
    try:
        data = request.json

        subject = data['subject']
        year = int(data['year'])           
        stream = data['stream']
        from_date = data['from_date']      
        to_date = data['to_date']          
        threshold = int(data.get('threshold', 75))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
        SELECT
            s.id AS student_id,
            s.name AS student_name,
            COUNT(a.id) AS total_lectures,
            SUM(a.status = 'present') AS present_count,
            ROUND(
                (SUM(a.status = 'present') / COUNT(a.id)) * 100, 2
            ) AS percentage
        FROM students s
        JOIN attendance a ON s.id = a.student_id
        WHERE s.stream = %s
          AND s.year = %s
          AND a.subject = %s
          AND DATE(a.lecture_date) BETWEEN %s AND %s
        GROUP BY s.id, s.name
        HAVING percentage < %s
        ORDER BY percentage ASC
        """

        cursor.execute(
            query,
            (
                stream,
                year,
                subject,
                from_date,
                to_date,
                threshold
            )
        )

        result = cursor.fetchall()
        return jsonify(result)

    except Exception as e:
        print("Defaulter error:", e)
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()




if __name__ == "__main__":
    app.run(debug=True)