from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import mysql.connector

app = Flask(__name__)
app.secret_key = 'aK9$mP2xL#7qR5nW&8vT3jF6hB!4yC1zA@2eD9gH5iJ8kM3nP7qS4tU6wX1yZ0'

# ---------- DATABASE CONNECTION ----------
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",  # Change to your MySQL password
        database="teacher"
    )

# ---------- ADMIN ROUTES ----------

@app.route("/")
def admin_page():
    return render_template("admin_login.html")

@app.route("/admin/login", methods=["POST"])
def admin_login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM admins WHERE username=%s AND password=%s", (username, password))
    admin = cursor.fetchone()
    cursor.close()
    db.close()
    
    if admin:
        session['admin_logged_in'] = True
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "fail"})

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_page'))
    return render_template("admin_dashboard.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_page'))

# ---------- TEACHER MANAGEMENT ----------

# @app.route("/add_teacher", methods=["POST"])
# def add_teacher():
#     data = request.json
#     db = get_db_connection()
#     cursor = db.cursor()
#     
#     try:
#         cursor.execute(
#             "INSERT INTO teachers (name, department, teacher_id, password) VALUES (%s,%s,%s,%s)",
#             (data["name"], data["department"], data["teacher_id"], data["password"])
#         )
#         db.commit()
#         message = "Teacher added successfully"
#     except mysql.connector.IntegrityError:
#         message = "Teacher ID already exists"
#     finally:
#         cursor.close()
#         db.close()
#     
#     return jsonify({"message": message})
@app.route("/add_teacher", methods=["POST"])
def add_teacher():
    data = request.json

    # ✅ BACKEND SAFETY CHECK
    if not data.get("name") or not data.get("department") or not data.get("teacher_id") or not data.get("password"):
        return jsonify({
            "status": "fail",
            "message": "Fill all the fields"
        })

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute(
            "INSERT INTO teachers (name, department, teacher_id, password) VALUES (%s,%s,%s,%s)",
            (data["name"], data["department"], data["teacher_id"], data["password"])
        )
        db.commit()
        return jsonify({
            "status": "success",
            "message": "Teacher added successfully"
        })

    except mysql.connector.IntegrityError:
        return jsonify({
            "status": "fail",
            "message": "Teacher ID already exists"
        })

    finally:
        cursor.close()
        db.close()


@app.route("/get_teachers")
def get_teachers():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT name, department, teacher_id FROM teachers")
    teachers = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify(teachers)

@app.route("/delete_teacher", methods=["POST"])
def delete_teacher():
    data = request.json
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("DELETE FROM teachers WHERE teacher_id=%s", (data["teacher_id"],))
    db.commit()
    cursor.close()
    db.close()
    return jsonify({"message": "Teacher deleted successfully"})

@app.route("/update_teacher", methods=["POST"])
def update_teacher():
    data = request.json

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("""
        UPDATE teachers
        SET name=%s, department=%s
        WHERE teacher_id=%s
    """, (
        data["name"],
        data["department"],
        data["teacher_id"]
    ))

    db.commit()
    cursor.close()
    db.close()

    return jsonify({"message": "Teacher updated successfully"})

# ---------- SUBJECT ASSIGNMENT ----------

@app.route("/api/teachers")
def get_teachers_api():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT teacher_id, name as teacher_name FROM teachers")
    data = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify(data)

@app.route("/api/subjects")
def get_subjects():
    stream = request.args.get("stream")
    year = request.args.get("year")
    semester = request.args.get("semester")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    query = """
        SELECT id, subject_name
        FROM subjects
        WHERE stream=%s AND year=%s AND semester=%s
    """
    cursor.execute(query, (stream, year, semester))
    subjects = cursor.fetchall()

    cursor.close()
    db.close()

    return jsonify(subjects)

@app.route("/api/assign-subject", methods=["POST"])
def assign_subject():
    data = request.json

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO teacher_subject_mapping
        (teacher_id, subject_id, stream, year, semester)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        data["teacher_id"],
        data["subject_id"],
        data["stream"],
        data["year"],
        data["semester"]
    ))

    db.commit()
    cursor.close()
    db.close()
    return jsonify({"message": "Subject assigned successfully"})

# ---------- STUDENT MANAGEMENT ----------

# @app.route("/add_student", methods=["POST"])
# def add_student():
#     data = request.json
#     db = get_db_connection()
#     cursor = db.cursor()
    
#     try:
#         cursor.execute(
#             "INSERT INTO students (name,department, year, roll_no, password) VALUES (%s,%s,%s,%s,%s)",
#             (data["name"],data["department"], data["year"], data["roll_no"], data["password"])
#         )
#         db.commit()
#         message = "Student added successfully"
#     except mysql.connector.IntegrityError:
#         message = "Roll number already exists"
#     finally:
#         cursor.close()
#         db.close()
    
#     return jsonify({"message": message})
@app.route("/add_student", methods=["POST"])
def add_student():
    data = request.json

    # ✅ BACKEND VALIDATION
    if (not data.get("name") or not data.get("department")
        or not data.get("year") or not data.get("roll_no")
        or not data.get("password")):

        return jsonify({
            "status": "fail",
            "message": "Fill all the fields"
        })

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute(
            "INSERT INTO students (name, department, year, roll_no, password) VALUES (%s,%s,%s,%s,%s)",
            (
                data["name"],
                data["department"],
                data["year"],
                data["roll_no"],
                data["password"]
            )
        )
        db.commit()

        return jsonify({
            "status": "success",
            "message": "Student added successfully"
        })

    except mysql.connector.IntegrityError:
        return jsonify({
            "status": "fail",
            "message": "Roll number already exists"
        })

    finally:
        cursor.close()
        db.close()


@app.route("/get_students")
def get_students():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT department, year, roll_no FROM students")
    students = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify(students)

@app.route("/delete_student", methods=["POST"])
def delete_student():
    data = request.json
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("DELETE FROM students WHERE roll_no=%s", (data["roll_no"],))
    db.commit()
    cursor.close()
    db.close()
    return jsonify({"message": "Student deleted successfully"})

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True, port=5000)