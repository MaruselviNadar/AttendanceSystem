CREATE DATABASE IF NOT EXISTS attendance_db;
USE attendance_db;

-- --------------------------------------------------------
-- Users/Students
-- --------------------------------------------------------
DROP TABLE IF EXISTS students;
CREATE TABLE students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100),
    department VARCHAR(50),
    year VARCHAR(5),
    roll_no VARCHAR(50) UNIQUE NOT NULL,
    stream VARCHAR(10),
    password VARCHAR(100)
);

-- --------------------------------------------------------
-- Subjects
-- --------------------------------------------------------
DROP TABLE IF EXISTS subjects;
CREATE TABLE subjects (
    id INT NOT NULL AUTO_INCREMENT,
    subject_name VARCHAR(100) NOT NULL,
    stream VARCHAR(50) NOT NULL,
    year VARCHAR(5) NOT NULL,
    semester VARCHAR(20) NOT NULL,
    PRIMARY KEY (id)
);

-- --------------------------------------------------------
-- Attendance
-- --------------------------------------------------------
DROP TABLE IF EXISTS attendance;
CREATE TABLE attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(20),
    subject_id INT,
    status ENUM('Present', 'Absent'),
    date DATE,
    semester VARCHAR(20),
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (subject_id) REFERENCES subjects(id)
);

-- --------------------------------------------------------
-- Seed Data
-- --------------------------------------------------------

-- Students
INSERT INTO students (student_id, name, department, year, roll_no, stream, password) VALUES 
('1', 'Nidhi', 'CS', 'TY', '101', 'CS', '1234');

-- Subjects
INSERT INTO subjects (name) VALUES 
('DBMS'), ('OS'), ('DSA'), ('Math');

-- Sample Attendance for student '1'
-- Assume IDs 1,2,3,4 for subjects
INSERT INTO attendance (student_id, subject_id, status, date, semester) VALUES 
('1', 1, 'Present', '2023-01-01', 'Sem 3'),
('1', 1, 'Present', '2023-01-02', 'Sem 3'),
('1', 2, 'Absent', '2023-01-03', 'Sem 3'),
('1', 3, 'Present', '2023-01-04', 'Sem 3'),
('1', 4, 'Present', '2023-01-05', 'Sem 3');
