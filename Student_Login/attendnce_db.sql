USE attendance_system;
CREATE TABLE `students` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `department` varchar(50) NOT NULL,
  `year` int NOT NULL,
  `roll_no` varchar(50) NOT NULL,
  `password` varchar(255) NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `roll_no` (`roll_no`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------
-- Subjects
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `subjects` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `subject_name` VARCHAR(100) NOT NULL,
    `department` VARCHAR(50) NOT NULL,
    `year` INT NOT NULL,
    `semester` VARCHAR(20) NOT NULL,
    PRIMARY KEY (id)
);

-- --------------------------------------------------------
-- Attendance
-- --------------------------------------------------------

CREATE TABLE `attendance` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `roll_no` VARCHAR(50) NOT NULL,
    `subject_id` INT NOT NULL,
    `status` ENUM('Present','Absent') NOT NULL,
    `date` DATE NOT NULL,
    `semester` VARCHAR(20) NOT NULL,
    FOREIGN KEY (roll_no) REFERENCES students(roll_no),
    FOREIGN KEY (subject_id) REFERENCES subjects(id)
);


-- Students
INSERT INTO `students` (`name`, `department`, `year`, `roll_no`, `password`) VALUES 
('Mani, 'CS', 3, '1', '1234');
-- Subjects (Changed to Sem 3 to match user preference)
INSERT INTO `subjects` (`subject_name`, `department`, `year`, `semester`) VALUES 
('DBMS', 'CS', 3, 'Sem 3'),
('OS', 'CS', 3, 'Sem 3'),
('DSA', 'CS', 3, 'Sem 3'),
('Math', 'CS', 3, 'Sem 3');

-- Sample Attendance for student '1' (Changed to Sem 3)
INSERT INTO `attendance` (`roll_no`, `subject_id`, `status`, `date`, `semester`) VALUES 
('1', 1, 'Present', '2023-01-01', 'Sem 3'),
('1', 1, 'Present', '2023-01-02', 'Sem 3'),
('1', 2, 'Absent', '2023-01-03', 'Sem 3'),
('1', 3, 'Present', '2023-01-04', 'Sem 3'),
('1', 4, 'Present', '2023-01-05', 'Sem 3');
