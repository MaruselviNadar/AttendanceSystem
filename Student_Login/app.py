from flask import Flask, render_template,request, jsonify
from flask_cors import CORS
from datetime import datetime
from collections import defaultdict


app = Flask(__name__)
CORS(app) # Initialize CORS once.


MOCK_STUDENTS = {
    "S1001": {"name": "John Doe", "stream": "BSc Computer Science", "semester": "Sem 3", "password": "pass"},
    "S1002": {"name": "Jane Smith", "stream": "BSc Computer Science", "semester": "Sem 3", "password": "pass"},
}

MOCK_SUBJECTS = {
    "Sem 3": ["DBMS", "OS", "DSA", "Math"],
}

MOCK_CLASSES = {
    # DBMS Classes in January
    "C101": {"subject": "DBMS", "date": datetime(2025, 1, 5), "attended": ["S1001", "S1002"]},
    "C102": {"subject": "DBMS", "date": datetime(2025, 1, 12), "attended": ["S1001"]},
    "C103": {"subject": "DBMS", "date": datetime(2025, 1, 19), "attended": ["S1001", "S1002"]},
    "C104": {"subject": "DBMS", "date": datetime(2025, 1, 26), "attended": ["S1002"]},
    # OS Classes in January
    "C201": {"subject": "OS", "date": datetime(2025, 1, 6), "attended": ["S1001", "S1002"]},
    "C202": {"subject": "OS", "date": datetime(2025, 1, 13), "attended": ["S1001"]},
    "C203": {"subject": "OS", "date": datetime(2025, 1, 20), "attended": ["S1001", "S1002"]},
    "C204": {"subject": "OS", "date": datetime(2025, 1, 27), "attended": ["S1001"]},
    # DSA Classes (low attendance for 'S1001')
    "C301": {"subject": "DSA", "date": datetime(2025, 1, 7), "attended": ["S1002"]},
    "C302": {"subject": "DSA", "date": datetime(2025, 1, 14), "attended": ["S1002"]},
    "C303": {"subject": "DSA", "date": datetime(2025, 1, 21), "attended": ["S1002"]},
    "C304": {"subject": "DSA", "date": datetime(2025, 1, 28), "attended": ["S1002"]},
}


@app.route('/')
def final():
    # This requires 'render_template' to be imported
    return render_template('final.html', title='Student Attendance Portal')
@app.route('/')
def graph():
    # This requires 'render_template' to be imported
    return render_template('graph.html', title='Student Attendance graph')


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    student_id = data.get('student_id')
    password = data.get('password')

    student = MOCK_STUDENTS.get(student_id)

    if student and student['password'] == password:
        return jsonify({
            "message": "Login successful", 
            "token": f"mock-jwt-for-{student_id}",
            "student_id": student_id,
            "name": student['name']
        }), 200
    
    return jsonify({"message": "Invalid Student ID or Password"}), 401

@app.route('/api/student/profile/<student_id>', methods=['GET'])
def get_student_profile(student_id):
    student = MOCK_STUDENTS.get(student_id)
    if student:
        return jsonify({
            "name": student['name'],
            "stream": student['stream'],
            "current_semester": student['semester']
        }), 200
    return jsonify({"message": "Student not found"}), 404

@app.route('/api/attendance/month-report', methods=['POST'])
def get_month_report():
    data = request.get_json()
    student_id = data.get('student_id')
    month = data.get('month')
    year = data.get('year')

    if not all([student_id, month, year]):
        return jsonify({"message": "Missing parameters"}), 400

    attendance_data = defaultdict(lambda: {'attended': 0, 'total': 0})

    for class_id, class_info in MOCK_CLASSES.items():
        class_date = class_info['date']
        
        if class_date.month == month and class_date.year == year:
            subject = class_info['subject']
            
            attendance_data[subject]['total'] += 1
            
            if student_id in class_info['attended']:
                attendance_data[subject]['attended'] += 1

    report = []
    for subject, counts in attendance_data.items():
        attended = counts['attended']
        total = counts['total']
        absent = total - attended
        
        if total > 0:
            report.append({
                "subject": subject,
                "attended": attended,
                "absent": absent,
                "total": total
            })

    return jsonify(report), 200


@app.route('/api/attendance/semester-report', methods=['POST'])
def get_semester_report():
    data = request.get_json()
    student_id = data.get('student_id')
    semester = data.get('semester')
    
    if not all([student_id, semester]):
        return jsonify({"message": "Missing parameters"}), 400
    
    attendance_data = defaultdict(lambda: {'attended': 0, 'total': 0})

    
    
    for class_id, class_info in MOCK_CLASSES.items():
        subject = class_info['subject']
        
        attendance_data[subject]['total'] += 1
        
        if student_id in class_info['attended']:
            attendance_data[subject]['attended'] += 1

    report = []
    for subject, counts in attendance_data.items():
        attended = counts['attended']
        total = counts['total']
        
        attendance_percent = round((attended / total) * 100) if total > 0 else 0
        
        report.append({
            "subject": subject,
            "attendance_percent": attendance_percent
        })

    return jsonify(report), 200

@app.route('/api/attendance/defaulter-status', methods=['POST'])
def get_defaulter_status():
    data = request.get_json()
    student_id = data.get('student_id')
    subject_code = data.get('subject')

    if not all([student_id, subject_code]):
        return jsonify({"message": "Missing parameters"}), 400
    
    ATTENDANCE_THRESHOLD = 75 
    attended_count = 0
    total_count = 0

    for class_id, class_info in MOCK_CLASSES.items():
        if class_info['subject'] == subject_code:
            total_count += 1
            if student_id in class_info['attended']:
                attended_count += 1
    
    attendance_percent = round((attended_count / total_count) * 100) if total_count > 0 else 0
    is_defaulter = "YES" if attendance_percent < ATTENDANCE_THRESHOLD else "NO"

    return jsonify({
        "subject": subject_code,
        "attendance_percent": attendance_percent,
        "is_defaulter": is_defaulter,
        "threshold": ATTENDANCE_THRESHOLD
    }), 200

if __name__ == '_main_':
    # You are running on the default port 5000
    app.run(debug=True)
