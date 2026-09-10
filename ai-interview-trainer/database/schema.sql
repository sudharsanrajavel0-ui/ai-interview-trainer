CREATE DATABASE IF NOT EXISTS ai_interview
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE ai_interview;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_email (email)
);

CREATE TABLE IF NOT EXISTS interviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    job_role VARCHAR(100) NOT NULL,
    interview_type VARCHAR(50) NOT NULL,
    difficulty VARCHAR(20) NOT NULL,
    total_questions INT NOT NULL,
    current_question INT DEFAULT 0,
    total_score FLOAT DEFAULT 0.0,
    status VARCHAR(20) DEFAULT 'in_progress',
    overall_feedback TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_status (status)
);

CREATE TABLE IF NOT EXISTS questions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    interview_id INT NOT NULL,
    question_number INT NOT NULL,
    question_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (interview_id) REFERENCES interviews(id) ON DELETE CASCADE,
    INDEX idx_interview_id (interview_id)
);

CREATE TABLE IF NOT EXISTS answers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question_id INT NOT NULL,
    candidate_answer TEXT NOT NULL,
    score FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
    INDEX idx_question_id (question_id)
);

CREATE TABLE IF NOT EXISTS feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    answer_id INT NOT NULL,
    strengths TEXT,
    weaknesses TEXT,
    suggestions TEXT,
    model_answer TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (answer_id) REFERENCES answers(id) ON DELETE CASCADE,
    INDEX idx_answer_id (answer_id)
);
