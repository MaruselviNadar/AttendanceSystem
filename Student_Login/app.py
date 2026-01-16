from flask import Flask, request, jsonify, session, render_template
from flask_cors import CORS
from flask_mysqldb import MySQL

app = Flask(__name__, static_url_path='/static', static_folder='static')
app.secret_key = "attendance_secret"

CORS(app, supports_credentials=True)

# ---------------- MYSQL CONFIG ----------------
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '123456'
app.config['MYSQL_DB'] = 'attendance_db'

mysql = MySQL(app)

# ---------------- ERROR HANDLER ----------------
@app.errorhandler(500)
def handle_500(e):
    # Try to get the original exception if available
    original = getattr(e, "original_exception", e)
    return jsonify({"success": False, "error": str(original)}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    return jsonify({"success": False, "error": str(e)}), 500

# ---------------- PAGE ROUTES ----------------
@app.route("/")
def index():
    return render_template("login.html")

@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")

@app.route("/graph")
def graph_page():
    return render_template("graph.html")

# ---------------- HELPERS ----------------
def login_required():
    return 'student_id' in session

# ---------------- LOGIN ----------------
@app.route("/api/student/login", methods=["POST"])
def login():
    data = request.json
    student_id = data.get("student_id")
    password = data.get("password")

    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT * FROM students WHERE student_id=%s AND password=%s",
        (student_id, password)
    )
    student = cur.fetchone()

    if not student:
        return jsonify({"success": False, "error": "Invalid credentials"}), 401

    session['student_id'] = student_id
    return jsonify({"success": True})

# ---------------- LOGOUT ----------------
@app.route("/api/student/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})

# ---------------- STUDENT INFO ----------------
@app.route("/api/student/info")
def student_info():
    if not login_required():
        return jsonify({"error": "Unauthorized"}), 401

    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT name, department, stream, year FROM students WHERE student_id=%s",
        (session['student_id'],)
    )
    data = cur.fetchone()

    return jsonify({
        "name": data[0],
        "department": data[1],
        "stream": data[2],
        "year": data[3],
        "student_id": session['student_id']
    })

# ---------------- SUBJECTS ----------------
@app.route("/api/student/subjects")
def subjects():
    if not login_required():
        return jsonify({"error": "Unauthorized"}), 401

    cur = mysql.connection.cursor()
    cur.execute("SELECT name FROM subjects")
    rows = cur.fetchall()

    return jsonify({
        "subjects": [{"name": r[0]} for r in rows]
    })

# ---------------- MONTHLY ATTENDANCE ----------------
@app.route("/api/student/attendance/monthly")
def monthly():
    if not login_required():
        return jsonify({"error": "Unauthorized"}), 401

    month = request.args.get("month")

    cur = mysql.connection.cursor()
    query = """
    SELECT s.name,
           COUNT(a.id) AS total,
           SUM(a.status='Present') AS attended,
           SUM(a.status='Absent') AS absent
    FROM attendance a
    JOIN subjects s ON a.subject_id = s.id
    WHERE a.student_id=%s AND MONTHNAME(a.date)=%s
    GROUP BY s.name
    """
    cur.execute(query, (session['student_id'], month))
    rows = cur.fetchall()

    result = {}
    for r in rows:
        result[r[0]] = {
            "total": r[1],
            "attended": r[2],
            "absent": r[3]
        }

    return jsonify({"data": result})

# ---------------- SEMESTER ATTENDANCE ----------------
@app.route("/api/student/attendance/semester")
def semester():
    if not login_required():
        return jsonify({"error": "Unauthorized"}), 401

    sem = request.args.get("semester")

    cur = mysql.connection.cursor()
    query = """
    SELECT s.name,
           ROUND(SUM(a.status='Present')/COUNT(*)*100,2)
    FROM attendance a
    JOIN subjects s ON a.subject_id=s.id
    WHERE a.student_id=%s AND a.semester=%s
    GROUP BY s.name
    """
    cur.execute(query, (session['student_id'], sem))
    rows = cur.fetchall()

    return jsonify({
        "data": {r[0]: r[1] for r in rows}
    })

# ---------------- DEFAULTER ----------------
@app.route("/api/student/attendance/defaulter")
def defaulter():
    if not login_required():
        return jsonify({"error": "Unauthorized"}), 401

    sem = request.args.get("semester")
    subject = request.args.get("subject")

    cur = mysql.connection.cursor()
    query = """
    SELECT ROUND(SUM(a.status='Present')/COUNT(*)*100,2)
    FROM attendance a
    JOIN subjects s ON a.subject_id=s.id
    WHERE a.student_id=%s AND a.semester=%s AND s.name=%s
    """
    cur.execute(query, (session['student_id'], sem, subject))
    percent = cur.fetchone()[0] or 0

    return jsonify({
        "attendance_percentage": percent,
        "is_defaulter": percent < 75
    })

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
