
from flask import Flask, render_template, request, jsonify
import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",        # your XAMPP MySQL password (empty = default)
        database="school"
    )


app = Flask(__name__)

# ------------------ ADMIN LOGIN PAGE --------------------
@app.route('/')
def login_page():
    return render_template('admin_login.html')  # your original HTML

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")  

    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT * FROM admin WHERE username=%s AND password=%s",
                (username, password))
    admin = cur.fetchone()

    cur.close()
    con.close()

    if admin:
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "fail"})


# ------------------ ADMIN DASHBOARD --------------------
@app.route('/dashboard')
def dashboard():
    return render_template('admin_dashboard.html')  # your original HTML


# ------------------ ADD TEACHER --------------------
@app.route('/add_teacher', methods=['POST'])
def add_teacher():
    data = request.get_json()

    name = data.get("name")
    dept = data.get("department")
    tid = data.get("teacher_id")
    password = data.get("password")

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO teachers (teacher_name, department, teacher_id, password) VALUES (%s, %s, %s, %s)",
            (name, dept, tid, password)
        )
        conn.commit()
        return jsonify({"message": "Teacher added successfully!"})
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"})
    finally:
        cursor.close()
        conn.close()






# ------------------ VIEW TEACHERS --------------------
@app.route('/get_teachers', methods=['GET'])
def get_teachers():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT teacher_name AS name, department, teacher_id FROM teachers")
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(rows)




# ------------------ DELETE TEACHER --------------------
@app.route('/delete_teacher', methods=['POST'])
def delete_teacher():
    data = request.get_json()
    teacher_id = data.get('teacher_id')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM teachers WHERE teacher_id = %s", (teacher_id,))
    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"message": "Teacher deleted successfully"})

# ------------------ ASSIGN SUBJECT --------------------

@app.route("/api/teachers")
def get_teachers_api():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT teacher_id, teacher_name FROM teachers")
    data = cur.fetchall()
    conn.close()
    return jsonify(data)

@app.route("/api/subjects")
def get_subjects():
    stream = request.args.get("stream")
    year = request.args.get("year")
    semester = request.args.get("semester")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT id, subject_name
        FROM subjects
        WHERE stream=%s AND year=%s AND semester=%s
    """
    cursor.execute(query, (stream, year, semester))
    subjects = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(subjects)



@app.route("/api/assign-subject", methods=["POST"])
def assign_subject():
    data = request.json

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
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

    conn.commit()
    conn.close()
    return jsonify({"message": "Subject assigned successfully"})





if __name__ == "__main__":

    app.run(debug=True)

   