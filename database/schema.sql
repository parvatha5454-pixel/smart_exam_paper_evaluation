-- ============================================================
-- AI-Powered Offline Exam Answer Analysis System
-- Database Schema
-- ============================================================

CREATE DATABASE IF NOT EXISTS exam_analysis_db
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE exam_analysis_db;

-- ------------------------------------------------------------
-- Table: admin
-- Stores admin login credentials (passwords are hashed, never
-- stored in plain text — see utils/security.py)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin (
    admin_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    last_login DATETIME NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Table: students
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS students (
    student_id INT AUTO_INCREMENT PRIMARY KEY,
    roll_number VARCHAR(30) NOT NULL UNIQUE,
    full_name VARCHAR(100) NOT NULL,
    department VARCHAR(100),
    semester VARCHAR(20),
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Table: subjects
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS subjects (
    subject_id INT AUTO_INCREMENT PRIMARY KEY,
    subject_code VARCHAR(30) NOT NULL UNIQUE,
    subject_name VARCHAR(150) NOT NULL,
    department VARCHAR(100),
    semester VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Table: answer_keys
-- One row per exam/answer-key "set" (metadata container)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS answer_keys (
    answer_key_id INT AUTO_INCREMENT PRIMARY KEY,
    subject_id INT NOT NULL,
    exam_name VARCHAR(150) NOT NULL,
    department VARCHAR(100),
    semester VARCHAR(20),
    question_paper_path VARCHAR(500),
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES admin(admin_id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Table: questions
-- Individual questions belonging to an answer key
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS questions (
    question_id INT AUTO_INCREMENT PRIMARY KEY,
    answer_key_id INT NOT NULL,
    question_number VARCHAR(10) NOT NULL,
    expected_answer TEXT NOT NULL,
    keywords TEXT,
    max_marks DECIMAL(5,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (answer_key_id) REFERENCES answer_keys(answer_key_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Table: scanned_sheets
-- Uploaded/scanned answer sheet images (per student, per exam)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scanned_sheets (
    sheet_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    answer_key_id INT NOT NULL,
    original_image_path VARCHAR(500) NOT NULL,
    processed_image_path VARCHAR(500),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (answer_key_id) REFERENCES answer_keys(answer_key_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Table: ocr_results
-- Extracted text per question, per scanned sheet
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ocr_results (
    ocr_id INT AUTO_INCREMENT PRIMARY KEY,
    sheet_id INT NOT NULL,
    question_id INT NOT NULL,
    extracted_text TEXT,
    corrected_text TEXT,
    ocr_confidence DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sheet_id) REFERENCES scanned_sheets(sheet_id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(question_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Table: evaluations
-- Scoring result per question, per scanned sheet
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS evaluations (
    evaluation_id INT AUTO_INCREMENT PRIMARY KEY,
    sheet_id INT NOT NULL,
    question_id INT NOT NULL,
    similarity_score DECIMAL(5,2),
    keyword_score DECIMAL(5,2),
    marks_awarded DECIMAL(5,2),
    remarks VARCHAR(50),
    evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sheet_id) REFERENCES scanned_sheets(sheet_id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(question_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Table: reports
-- Generated report files (PDF/Excel) per sheet
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reports (
    report_id INT AUTO_INCREMENT PRIMARY KEY,
    sheet_id INT NOT NULL,
    report_type ENUM('pdf', 'excel') NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    total_marks DECIMAL(6,2),
    percentage DECIMAL(5,2),
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sheet_id) REFERENCES scanned_sheets(sheet_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Table: activity_logs
-- Tracks admin actions for auditing
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS activity_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT,
    action VARCHAR(255) NOT NULL,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES admin(admin_id) ON DELETE SET NULL
) ENGINE=InnoDB;
