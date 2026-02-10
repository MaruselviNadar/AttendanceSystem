from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import mysql.connector

app = Flask(__name__)
app.secret_key = 'aK9$mP2xL#7qR5nW&8vT3jF6hB!4yC1zA@2eD9gH5iJ8kM3nP7qS4tU6wX1yZ0'

# ---------- DATABASE CONNECTION ----------
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="123456",  # Change to your MySQL password
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

    #  BACKEND SAFETY CHECK
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
    conn = None
    cursor = None

    data = request.json
    teacher_id = data.get("teacher_id")

    print("Deleting teacher:", teacher_id)

    if not teacher_id:
        return jsonify({
             "status": "fail",
    "message": "Delete failed"
        })

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # delete mapping first (FK safe)
        cursor.execute(
            "DELETE FROM teacher_subject_mapping WHERE teacher_id=%s",
            (teacher_id,)
        )

        cursor.execute(
            "DELETE FROM teachers WHERE teacher_id=%s",
            (teacher_id,)
        )

        conn.commit()
        return jsonify({
            "status": "success",
    "message": "Teacher deleted successfully"
        })

    except Exception as e:
        print("Error deleting teacher:", e)
        if conn:
            conn.rollback()
        return jsonify({
            "success": False,
            "message": "Delete failed"
        })

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

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
# ---------- CLASS TEACHER ASSIGNMENT ----------
@app.route("/api/assign-class-teacher", methods=["POST"])
def assign_class_teacher():
   data = request.json
   ay = data["academic_year"]
   if len(ay) == 7 and "-" in ay:
        start, end = ay.split("-")
        data["academic_year"] = f"{start}-20{end}"


   db = get_db_connection()
   cursor = db.cursor()

   try:
        cursor.execute("""
            SELECT 1 FROM class_teacher_assignment
            WHERE teacher_id = %s AND academic_year = %s
            LIMIT 1
        """, (
            data["teacher_id"],
            data["academic_year"]
        ))

        if cursor.fetchone():
            return jsonify({
                "message": "This teacher is already assigned for this academic year"
            }), 400
        cursor.execute("""
           INSERT INTO class_teacher_assignment
           (teacher_id, stream, year, academic_year)
           VALUES (%s, %s, %s, %s)
       """, (
           data["teacher_id"],
           data["stream"],
           data["year"],
           data["academic_year"]
       ))
        db.commit()
        return jsonify({"message": "Class teacher assigned successfully"})

   except mysql.connector.IntegrityError:
       return jsonify({
           "message": "Class teacher already assigned for this class & year"
        })

   finally:
      cursor.close()
      db.close()




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