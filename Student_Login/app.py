from flask import Flask, request, jsonify, session, render_template
from flask_cors import CORS
import mysql.connector
app = Flask(__name__, static_url_path='/static', static_folder='static')
app.secret_key = "attendance_secret"
CORS(app, supports_credentials=True)

# ---------------- MYSQL CONFIG ----------------
def get_db_connection():

    """Create a new MySQL connection."""
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Sanskruti@13",
        database="attendance_system",
       
    )

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
    return 'roll_no' in session

# ---------------- LOGIN ----------------
@app.route("/api/student/login", methods=["POST"])
def login():
    data = request.json
    roll_no = data.get("roll_no")
    password = data.get("password")
   
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM students WHERE roll_no=%s AND password=%s",
        (roll_no, password)
    )
    student = cur.fetchone()
    cur.close()
    conn.close()
    if not student:
        
        return jsonify({"success": False, "error": "Invalid credentials"}), 401

    session['roll_no'] = roll_no
    cur.close()
    conn.close()
    return jsonify({"success": True})


# ---------------- LOGOUT ----------------
@app.route("/api/student/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})

# ---------------- STUDENT INFO ----------------
@app.route("/api/student/info")
def student_info():
    if 'roll_no' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT name, department, year FROM students WHERE roll_no=%s",
        (session['roll_no'],)
    )
    data = cur.fetchone()
    cur.close()
    conn.close()
   
    return jsonify({
        "name": data['name'],
        "department": data['department'],
        "year": data['year'],
        "roll_no": session['roll_no']
    })


# ---------------- SUBJECTS ----------------
@app.route("/api/student/subjects")
def subjects():
    if not login_required():
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db_connection()
    cur = conn.cursor()
    if semester:
            cur.execute("SELECT subject_name FROM subjects WHERE semester = %s", (semester,))
    else:
            cur.execute("SELECT subject_name FROM subjects")
    rows = cur.fetchall()

    cur.close()
    conn.close()
    return jsonify({
        "subjects": [{"name": r[0]} for r in rows]
    })


# ---------------- MONTHLY ATTENDANCE ----------------
@app.route("/api/student/attendance/monthly")
def monthly():
    if not login_required():
        return jsonify({"error": "Unauthorized"}), 401

    month = request.args.get("month")
    semester = request.args.get("semester")
    roll_no = session['roll_no']

    conn = get_db_connection()
    cur = conn.cursor()
    query = """
    SELECT s.subject_name,
           COUNT(a.id) AS total,
           SUM(a.status='Present') AS attended,
           SUM(a.status='Absent') AS absent
    FROM attendance a
        JOIN subjects s ON a.subject_id = s.id
        WHERE a.roll_no=%s AND LOWER(MONTHNAME(a.date))=LOWER(%s) AND a.semester=%s
        GROUP BY s.subject_name
        """
    cur.execute(query, (roll_no, month, semester))
    rows = cur.fetchall()
    
    result = {}
    for r in rows:
        result[r[0]] = {
                "total": int(r[1]) if r[1] is not None else 0,
                "attended": int(r[2]) if r[2] is not None else 0,
                "absent": int(r[3]) if r[3] is not None else 0
            }
    cur.close()
    conn.close()
    return jsonify({"data": result})

# ---------------- SEMESTER ATTENDANCE ----------------
@app.route("/api/student/attendance/semester")
def semester():
    if not login_required():
        return jsonify({"error": "Unauthorized"}), 401

    sem = request.args.get("semester")
    roll_no = session['roll_no']

    conn = get_db_connection()
    cur = conn.cursor()
    query = """
    SELECT s.subject_name,
               CAST(SUM(a.status='Present')/COUNT(*)*100 AS FLOAT)
        FROM attendance a
        JOIN subjects s ON a.subject_id=s.id
        WHERE a.roll_no=%s AND a.semester=%s
        GROUP BY s.subject_name
        """
    cur.execute(query, (session['roll_no'], sem))
    rows = cur.fetchall()

    cur.close()
    conn.close()
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

    conn = get_db_connection()
    cur = conn.cursor()
    query = """
    SELECT CAST(SUM(a.status='Present')/COUNT(*)*100 AS FLOAT)
    FROM attendance a
    JOIN subjects s ON a.subject_id=s.id
    WHERE a.roll_no=%s AND a.semester=%s AND s.subject_name=%s
    """
    cur.execute(query, (session['roll_no'], sem, subject))
    percent = cur.fetchone()[0] or 0

    cur.close()
    conn.close()
    return jsonify({
        "attendance_percentage": percent,
        "is_defaulter": percent < 75
    })

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
