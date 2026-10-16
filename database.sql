
CREATE DATABASE IF NOT EXISTS elearning_analytics;

USE  elearning_analytics;

CREATE TABLE courses (
    course_id INT AUTO_INCREMENT PRIMARY KEY,
    course_name VARCHAR(100) NOT NULL,
    category VARCHAR(50)
);

CREATE TABLE learners (
    learner_id INT AUTO_INCREMENT PRIMARY KEY,
    roll_no VARCHAR(30) UNIQUE
);

CREATE TABLE enrollments (
    enrollment_id INT AUTO_INCREMENT PRIMARY KEY,
    learner_id INT NOT NULL,
    course_id INT NOT NULL,
    enrolled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status ENUM(
        'active',
        'completed',
        'cancelled'
    ) DEFAULT 'active',

    FOREIGN KEY (learner_id)
        REFERENCES learners(learner_id),

    FOREIGN KEY (course_id)
        REFERENCES courses(course_id)
);

CREATE TABLE activities (
    activity_id INT AUTO_INCREMENT PRIMARY KEY,
    enrollment_id INT NOT NULL,
    activity_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    activity_type VARCHAR(50) NOT NULL,
    completed BOOLEAN DEFAULT FALSE,

    FOREIGN KEY (enrollment_id)
        REFERENCES enrollments(enrollment_id)
);

USE elearning_analytics;

INSERT INTO courses (course_name, category)
VALUES
('Python Programming', 'Programming'),
('Java Programming', 'Programming'),
('Web Development', 'Web Technology'),
('Database Management', 'Database');

INSERT INTO learners (roll_no)
VALUES
('CSE001'),
('CSE002'),
('CSE003'),
('CSE004'),
('CSE005');

INSERT INTO enrollments
(learner_id, course_id, enrolled_at, status)
VALUES
(1, 1, '2026-09-01 10:00:00', 'completed'),
(2, 1, '2026-09-05 10:00:00', 'active'),
(3, 2, '2026-09-07 10:00:00', 'completed'),
(4, 3, '2026-09-10 10:00:00', 'active'),
(5, 4, '2026-09-15 10:00:00', 'active');

INSERT INTO activities
(enrollment_id, activity_date, activity_type, completed)
VALUES
(1, '2026-09-02 10:00:00', 'lesson', TRUE),
(1, '2026-09-03 11:00:00', 'quiz', TRUE),
(2, '2026-10-10 12:00:00', 'lesson', TRUE),
(2, '2026-10-12 12:00:00', 'quiz', FALSE),
(3, '2026-09-08 14:00:00', 'lesson', TRUE),
(3, '2026-09-09 14:00:00', 'quiz', TRUE),
(4, '2026-10-13 15:00:00', 'lesson', TRUE);
SELECT * FROM courses;
SELECT * FROM learners;
SELECT * FROM enrollments;
SELECT * FROM activities;
USE elearning_analytics;

SHOW TABLES;

DESCRIBE courses;
DESCRIBE learners;
DESCRIBE enrollments;
DESCRIBE activities;

SELECT * FROM courses;
SELECT * FROM learners;
SELECT * FROM enrollments;
SELECT * FROM activities;
