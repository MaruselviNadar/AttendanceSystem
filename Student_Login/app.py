
from flask import Flask, request, jsonify, session, render_template, redirect, url_for, flash
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production-12345'

# Enable CORS
CORS(app, supports_credentials=True, origins=['http://localhost:*', 'http://127.0.0.1:*', 'file://*'])

# ==================== DATABASE CONNECTION ====================

def get_db_connection():
    """Create MySQL database connection"""
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='123456',
            database='teacher',
            autocommit=False
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# ==================== DECORATORS ====================

def student_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'student_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

def teacher_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'teacher_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

# ==================== STUDENT ROUTES (For student frontend) ====================

@app.route('/api/student/login', methods=['POST'])
def student_login():
    """Student login - works with login2(sies).html"""
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        password = data.get('password')
        stream = data.get('stream')
        year = data.get('year')
        
        if not all([student_id, password, stream, year]):
            return jsonify({'error': 'All fields required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """SELECT id, student_id, name, stream, year, password_hash, course 
               FROM students 
               WHERE student_id = %s AND stream = %s AND year = %s""",
            (student_id, stream, year)
        )
        student = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not student:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Check password
        if not check_password_hash(student['password_hash'], password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        session['student_id'] = student['id']
        session['student_name'] = student['name']
        session.permanent = True
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'student': {
                'name': student['name'],
                'course': student['course'] or f"BSc {student['stream']}",
                'stream': student['stream'],
                'year': student['year']
            }
        })
    except Exception as e:
        print(f"Student login error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/student/logout', methods=['POST'])
def student_logout():
    """Student logout"""
    session.clear()
    return jsonify({'success': True})

@app.route('/api/student/info', methods=['GET'])
@student_login_required
def get_student_info():
    """Get student info - works with graph.html"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT name, course, stream, year FROM students WHERE id = %s",
            (session['student_id'],)
        )
        student = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not student:
            return jsonify({'error': 'Student not found'}), 404
        
        return jsonify({
            'name': student['name'],
            'course': student['course'] or f"BSc {student['stream']}",
            'stream': student['stream'],
            'year': student['year']
        })
    except Exception as e:
        print(f"Error getting student info: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/student/subjects', methods=['GET'])
@student_login_required
def get_student_subjects():
    """Get subjects for student"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Get student's stream and year
        cursor.execute(
            "SELECT stream, year FROM students WHERE id = %s",
            (session['student_id'],)
        )
        student = cursor.fetchone()
        
        if not student:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Student not found'}), 404
        
        # Get subjects for this stream and year
        cursor.execute(
            """SELECT name, code FROM subjects 
               WHERE stream = %s AND year = %s""",
            (student['stream'], student['year'])
        )
        subjects = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            'subjects': [{'name': s['name'], 'code': s['code']} for s in subjects]
        })
    except Exception as e:
        print(f"Error getting subjects: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/student/attendance/monthly', methods=['GET'])
@student_login_required
def get_monthly_attendance():
    """Get monthly attendance - works with graph.html"""
    try:
        month = request.args.get('month', datetime.now().strftime('%B'))
        year = request.args.get('year', datetime.now().year, type=int)
        
        # Convert month name to number
        month_num = datetime.strptime(month, '%B').month
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Get student's stream and year
        cursor.execute(
            "SELECT stream, year FROM students WHERE id = %s",
            (session['student_id'],)
        )
        student = cursor.fetchone()
        
        # Get subjects
        cursor.execute(
            "SELECT name FROM subjects WHERE stream = %s AND year = %s",
            (student['stream'], student['year'])
        )
        subjects = cursor.fetchall()
        
        result = {}
        
        for subject in subjects:
            subject_name = subject['name']
            
            # Get attendance for this subject and month
            cursor.execute(
                """SELECT status FROM attendance a
                   JOIN lectures l ON a.lecture_key = l.lecture_key
                   WHERE a.student_id = %s 
                   AND l.subject = %s
                   AND MONTH(a.date) = %s 
                   AND YEAR(a.date) = %s""",
                (session['student_id'], subject_name, month_num, year)
            )
            records = cursor.fetchall()
            
            total = len(records)
            present = sum(1 for r in records if r['status'] == 'P')
            absent = total - present
            
            result[subject_name] = {
                'total': total,
                'attended': present,
                'absent': absent
            }
        
        cursor.close()
        conn.close()
        
        return jsonify({'data': result, 'month': month})
    except Exception as e:
        print(f"Error getting monthly attendance: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/student/attendance/semester', methods=['GET'])
@student_login_required
def get_semester_attendance():
    """Get semester attendance - works with graph.html"""
    try:
        semester = request.args.get('semester', 'Sem 3')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Get student's stream and year
        cursor.execute(
            "SELECT stream, year FROM students WHERE id = %s",
            (session['student_id'],)
        )
        student = cursor.fetchone()
        
        # Get subjects for this semester
        cursor.execute(
            """SELECT name FROM subjects 
               WHERE stream = %s AND year = %s AND semester = %s""",
            (student['stream'], student['year'], semester)
        )
        subjects = cursor.fetchall()
        
        result = {}
        
        for subject in subjects:
            subject_name = subject['name']
            
            # Get all attendance for this subject
            cursor.execute(
                """SELECT status FROM attendance a
                   JOIN lectures l ON a.lecture_key = l.lecture_key
                   WHERE a.student_id = %s AND l.subject = %s""",
                (session['student_id'], subject_name)
            )
            records = cursor.fetchall()
            
            total = len(records)
            if total > 0:
                present = sum(1 for r in records if r['status'] == 'P')
                percentage = round((present / total) * 100, 2)
                result[subject_name] = f"{percentage}%"
            else:
                result[subject_name] = "0%"
        
        cursor.close()
        conn.close()
        
        return jsonify({'data': result, 'semester': semester})
    except Exception as e:
        print(f"Error getting semester attendance: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/student/attendance/defaulter', methods=['GET'])
@student_login_required
def get_defaulter_status():
    """Get defaulter status - works with graph.html"""
    try:
        semester = request.args.get('semester', 'Sem 3')
        subject_name = request.args.get('subject')
        
        if not subject_name:
            return jsonify({'error': 'Subject required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Get attendance for this subject
        cursor.execute(
            """SELECT status FROM attendance a
               JOIN lectures l ON a.lecture_key = l.lecture_key
               WHERE a.student_id = %s AND l.subject = %s""",
            (session['student_id'], subject_name)
        )
        records = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        total = len(records)
        if total > 0:
            present = sum(1 for r in records if r['status'] == 'P')
            percentage = round((present / total) * 100, 2)
        else:
            percentage = 0
            present = 0
        
        return jsonify({
            'subject': subject_name,
            'semester': semester,
            'attendance_percentage': percentage,
            'is_defaulter': percentage < 75,
            'total_classes': total,
            'attended': present
        })
    except Exception as e:
        print(f"Error getting defaulter status: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# ==================== TEACHER ROUTES ====================

@app.route('/')
def index():
    """Home page with Teacher/Student options"""
    return render_template('index.html')

@app.route('/teacher_login')
def teacher_login_page():
    """Teacher login page"""
    return render_template('login.html')

@app.route('/student_login')
def student_login_page():
    """Student login page"""
    return render_template('student_login.html')

@app.route('/login', methods=['POST'])
def teacher_login():
    """Teacher login (form-based for your dashboard)"""
    teacher_id = request.form.get('teacher_id')
    password = request.form.get('password')
    
    if not teacher_id or not password:
        flash('Please enter both Teacher ID and Password', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    if not conn:
        flash('Database connection failed', 'error')
        return redirect(url_for('index'))
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, teacher_id, name, password_hash FROM teachers WHERE teacher_id = %s",
        (teacher_id,)
    )
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not user:
        flash('Invalid Teacher ID or Password', 'error')
        return redirect(url_for('index'))
    
    # Check password (supports both hashed and plain text for backward compatibility)
    if user['password_hash'].startswith('pbkdf2:sha256:') or user['password_hash'].startswith('scrypt:'):
        password_valid = check_password_hash(user['password_hash'], password)
    else:
        password_valid = (user['password_hash'] == password)
    
    if not password_valid:
        flash('Invalid Teacher ID or Password', 'error')
        return redirect(url_for('index'))
    
    session['teacher_id'] = user['id']
    session['teacher_name'] = user['name']
    session['teacher_username'] = user['teacher_id']
    
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    """Teacher dashboard"""
    if 'teacher_id' not in session:
        return redirect(url_for('index'))
    return render_template('dashboard.html', name=session['teacher_name'])

@app.route('/logout')
def logout():
    """Logout (both teacher and student)"""
    session.clear()
    return redirect(url_for('index'))

@app.route('/api/teacher/login', methods=['POST'])
def api_teacher_login():
    """Teacher login API (for teacher_login.html if you create it)"""
    try:
        data = request.get_json()
        teacher_id = data.get('teacher_id')
        password = data.get('password')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, teacher_id, name, password_hash FROM teachers WHERE teacher_id = %s",
            (teacher_id,)
        )
        teacher = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not teacher:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Check password
        if teacher['password_hash'].startswith('pbkdf2:sha256:') or teacher['password_hash'].startswith('scrypt:'):
            password_valid = check_password_hash(teacher['password_hash'], password)
        else:
            password_valid = (teacher['password_hash'] == password)
        
        if not password_valid:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        session['teacher_id'] = teacher['id']
        session['teacher_name'] = teacher['name']
        session.permanent = True
        
        return jsonify({
            'success': True,
            'teacher': {
                'name': teacher['name'],
                'teacher_id': teacher['teacher_id']
            }
        })
    except Exception as e:
        print(f"Teacher API login error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/teacher/logout', methods=['POST'])
def api_teacher_logout():
    """Teacher logout API"""
    session.clear()
    return jsonify({'success': True})

@app.route('/api/teacher/info', methods=['GET'])
@teacher_login_required
def get_teacher_info():
    """Get teacher info"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT name, teacher_id FROM teachers WHERE id = %s",
            (session['teacher_id'],)
        )
        teacher = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not teacher:
            return jsonify({'error': 'Teacher not found'}), 404
        
        return jsonify({
            'name': teacher['name'],
            'teacher_id': teacher['teacher_id']
        })
    except Exception as e:
        print(f"Error getting teacher info: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/subjects', methods=['GET'])
def get_all_subjects():
    """Get all subjects"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT name, code, stream, year, semester FROM subjects")
        subjects = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({'subjects': subjects})
    except Exception as e:
        print(f"Error getting subjects: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/students', methods=['GET'])
def get_students():
    """Get students by stream and year"""
    try:
        stream = request.args.get('stream')
        year = request.args.get('year')
        
        if not stream or not year:
            return jsonify({'error': 'Stream and year required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT student_id, name, stream, year FROM students WHERE stream = %s AND year = %s",
            (stream, year)
        )
        students = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({'students': students})
    except Exception as e:
        print(f"Error getting students: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/save_attendance', methods=['POST', 'OPTIONS'])
def save_attendance():
    """Save attendance from teacher dashboard"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        lecture_key = data['lecture_key']
        subject = data['subject']
        year = data['year']
        stream = data['stream']
        lecture_date_time = data['lecture_date_time']
        attendance = data['attendance']
        
        # Normalize datetime
        lecture_date_time = lecture_date_time.replace('T', ' ')
        if len(lecture_date_time) == 16:
            lecture_date_time += ':00'
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        try:
            # Insert or update lecture
            cursor.execute(
                """INSERT INTO lectures (lecture_key, subject, year, stream, lecture_date_time)
                   VALUES (%s, %s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE
                   subject = VALUES(subject),
                   year = VALUES(year),
                   stream = VALUES(stream),
                   lecture_date_time = VALUES(lecture_date_time)""",
                (lecture_key, subject, year, stream, lecture_date_time)
            )
            
            # Delete existing attendance
            cursor.execute("DELETE FROM attendance WHERE lecture_key = %s", (lecture_key,))
            
            # Insert new attendance
            for student_id, status in attendance.items():
                status_code = 'P' if status.lower() == 'present' else 'A'
                
                # Get the database ID for this student
                cursor.execute("SELECT id FROM students WHERE student_id = %s", (student_id,))
                result = cursor.fetchone()
                
                if result:
                    db_student_id = result[0]
                    cursor.execute(
                        """INSERT INTO attendance (lecture_key, student_id, status, date)
                           VALUES (%s, %s, %s, DATE(%s))""",
                        (lecture_key, db_student_id, status_code, lecture_date_time)
                    )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({'message': 'Attendance saved successfully!'})
            
        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            print(f"Save attendance error: {e}")
            return jsonify({'message': 'Error saving attendance', 'error': str(e)}), 500
            
    except Exception as e:
        print(f"Save attendance outer error: {e}")
        return jsonify({'message': 'Error processing request', 'error': str(e)}), 500

@app.route('/api/monthly_student_report', methods=['POST'])
def monthly_student_report():
    """Monthly report for teacher dashboard"""
    try:
        data = request.json
        month = int(data['month'])
        year_val = int(data['year'])
        subject = data.get('subject')
        stream = data.get('stream')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
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
        JOIN lectures l ON l.lecture_key = a.lecture_key
        WHERE MONTH(a.date) = %s
          AND YEAR(a.date) = %s
          AND s.stream = %s
          AND l.subject = %s
        GROUP BY s.id, s.name
        """
        
        cursor.execute(query, (month, year_val, stream, subject))
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify(results)
        
    except Exception as e:
        print(f"Monthly report error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def health():
    """Health check"""
    return jsonify({'status': 'healthy', 'database': 'MySQL'})

# ==================== INITIALIZATION ====================

def init_database():
    """Initialize database with tables and demo data"""
    conn = get_db_connection()
    if not conn:
        print("❌ Cannot connect to MySQL. Please check:")
        print("   1. MySQL is running")
        print("   2. Database 'teacher' exists")
        print("   3. Username/password are correct (root/123456)")
        return
    
    cursor = conn.cursor()
    
    try:
        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                stream VARCHAR(20) NOT NULL,
                year VARCHAR(10) NOT NULL,
                password_hash VARCHAR(200) NOT NULL,
                course VARCHAR(100)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teachers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                teacher_id VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                password_hash VARCHAR(200) NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                code VARCHAR(20) UNIQUE NOT NULL,
                stream VARCHAR(20) NOT NULL,
                year VARCHAR(10) NOT NULL,
                semester VARCHAR(10) NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lectures (
                id INT AUTO_INCREMENT PRIMARY KEY,
                lecture_key VARCHAR(100) UNIQUE NOT NULL,
                subject VARCHAR(100) NOT NULL,
                year VARCHAR(10) NOT NULL,
                stream VARCHAR(20) NOT NULL,
                lecture_date_time DATETIME NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INT AUTO_INCREMENT PRIMARY KEY,
                lecture_key VARCHAR(100) NOT NULL,
                student_id INT NOT NULL,
                status CHAR(1) NOT NULL,
                date DATE NOT NULL,
                FOREIGN KEY (lecture_key) REFERENCES lectures(lecture_key),
                FOREIGN KEY (student_id) REFERENCES students(id)
            )
        """)
        
        conn.commit()
        print("✅ Database tables created successfully")
        
        # Check if demo data exists
        cursor.execute("SELECT COUNT(*) FROM students")
        if cursor.fetchone()[0] == 0:
            print("🔄 Inserting demo data...")
            
            # Insert students
            students = [
                ('S001', 'John Doe', 'CS', 'SY', generate_password_hash('password123'), 'BSc Computer Science'),
                ('S002', 'Jane Smith', 'CS', 'SY', generate_password_hash('password123'), 'BSc Computer Science'),
                ('1', 'Alice Johnson', 'CS', 'SY', generate_password_hash('password123'), 'BSc Computer Science'),
                ('2', 'Bob Williams', 'CS', 'SY', generate_password_hash('password123'), 'BSc Computer Science'),
            ]
            cursor.executemany(
                "INSERT INTO students (student_id, name, stream, year, password_hash, course) VALUES (%s, %s, %s, %s, %s, %s)",
                students
            )
            
            # Insert teacher
            cursor.execute(
                "INSERT INTO teachers (teacher_id, name, password_hash) VALUES (%s, %s, %s)",
                ('T001', 'Prof. Anderson', generate_password_hash('teacher123'))
            )
            
            # Insert subjects
            subjects = [
                ('DBMS', 'CS301', 'CS', 'SY', 'Sem 3'),
                ('OS', 'CS302', 'CS', 'SY', 'Sem 3'),
                ('DSA', 'CS303', 'CS', 'SY', 'Sem 3'),
                ('Math', 'MA301', 'CS', 'SY', 'Sem 3'),
            ]
            cursor.executemany(
                "INSERT INTO subjects (name, code, stream, year, semester) VALUES (%s, %s, %s, %s, %s)",
                subjects
            )
            
            conn.commit()
            print("✅ Demo data inserted successfully!")
            print("\n📝 Demo Credentials:")
            print("   Student: S001 / CS / SY / password123")
            print("   Teacher: T001 / teacher123")
            print("   Teacher Dashboard IDs: 1, 2")
        else:
            print("✅ Demo data already exists")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        cursor.close()
        conn.close()

if __name__ == '__main__':
    print("🔄 Initializing MySQL database...")
    init_database()
    print("\n🚀 Starting Flask server on http://localhost:5000")
    print("📍 Student Portal: Open login2(sies).html")
    print("📍 Teacher Portal: http://localhost:5000/teacher_login")
    app.run(debug=True, host='0.0.0.0', port=5000)
