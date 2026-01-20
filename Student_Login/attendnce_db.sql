USE attendance_system;
CREATE TABLE students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    roll_no VARCHAR(50) UNIQUE NOT NULL,
    department VARCHAR(50) NOT NULL,
    year VARCHAR(50) NOT NULL,
    password VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subjects (
    id INT NOT NULL AUTO_INCREMENT,
    subject_name VARCHAR(100) NOT NULL,
    department VARCHAR(50) NOT NULL,
    year VARCHAR(50) NOT NULL,
    semester VARCHAR(20) NOT NULL,
    PRIMARY KEY (id)
);

-- --------------------------------------------------------
-- Attendance
-- --------------------------------------------------------

CREATE TABLE attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    roll_no VARCHAR(50) NOT NULL,
    subject_id INT NOT NULL,
    status ENUM('Present','Absent') NOT NULL,
    date DATE NOT NULL,
    semester VARCHAR(20) NOT NULL,
    FOREIGN KEY (roll_no) REFERENCES students(roll_no),
    FOREIGN KEY (subject_id) REFERENCES subjects(id)
);
CREATE TABLE IF NOT EXISTS admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- Students
INSERT INTO students (roll_no, department, year, password) VALUES 
('1', 'CS', 'TY', '1234');

-- Subjects (Changed to Sem 3 to match user preference)
INSERT INTO subjects (subject_name, department, year, semester) VALUES 
('DBMS', 'CS', 'TY', 'Sem 3'),
('OS', 'CS', 'TY', 'Sem 3'),
('DSA', 'CS', 'TY', 'Sem 3'),
('Math', 'CS', 'TY', 'Sem 3');

-- Sample Attendance for student '1' (Changed to Sem 3)
INSERT INTO attendance (roll_no, subject_id, status, date, semester) VALUES 
('1', 1, 'Present', '2023-01-01', 'Sem 3'),
('1', 1, 'Present', '2023-01-02', 'Sem 3'),
('1', 2, 'Absent', '2023-01-03', 'Sem 3'),
('1', 3, 'Present', '2023-01-04', 'Sem 3'),
('1', 4, 'Present', '2023-01-05', 'Sem 3');
