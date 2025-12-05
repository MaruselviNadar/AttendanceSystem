from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector

app = Flask(__name__)

# Allow requests from your frontend (127.0.0.1:8000, etc.)
CORS(app, resources={r"/*": {"origins": "*"}})


def get_connection():
    """
    Create a new MySQL connection.
    Change user/password/database to match your setup.
    """
    return mysql.connector.connect(
        host="localhost",
        user="root",                 # <-- your MySQL username
        password="root",             # <-- your MySQL password
        database="teacher",          # <-- your database name
        autocommit=False
    )


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

    # 1. Read JSON payload from frontend
    lecture_key = data["lecture_key"]
    subject = data["subject"]
    year = data["year"]
    stream = data["stream"]
    lecture_date_time = normalize_datetime(data["lecture_date_time"])
    attendance = data["attendance"]  # dict: { "1": "present", "2": "absent", ... }

    conn = get_connection()
    cur = conn.cursor()

    try:
        # 2. Insert / update lectures table
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

        # 3. Clear existing attendance for this lecture (if any)
        cur.execute("DELETE FROM attendance WHERE lecture_key = %s", (lecture_key,))

        # 4. Insert fresh attendance records
        for student_id, status in attendance.items():
            cur.execute(
                """
                INSERT INTO attendance (lecture_key, student_id, status)
                VALUES (%s, %s, %s)
                """,
                (lecture_key, int(student_id), status),
            )

        conn.commit()
        return jsonify({"message": "Attendance saved successfully!"})

    except Exception as e:
        conn.rollback()
        # Return error so you see it in browser console
        return jsonify({"message": "Error saving attendance", "error": str(e)}), 500

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    # Flask backend on port 5000
    app.run(debug=True)
