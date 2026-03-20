-- =============================================================
-- Walk-in Interview Booking Platform
-- Database Schema — AWS RDS MySQL 8.0
-- File: backend/migrations/schema.sql
-- =============================================================

CREATE DATABASE IF NOT EXISTS interview_platform
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE interview_platform;

-- =============================================================
-- TABLE: users
-- Stores candidate/user accounts (linked to Cognito)
-- =============================================================
CREATE TABLE users (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    cognito_sub     VARCHAR(128)    NOT NULL UNIQUE,   -- Cognito user pool sub (UUID)
    email           VARCHAR(255)    NOT NULL UNIQUE,
    full_name       VARCHAR(150)    NOT NULL,
    phone           VARCHAR(20),
    role            ENUM('user', 'admin') NOT NULL DEFAULT 'user',
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_users_email      (email),
    INDEX idx_users_cognito    (cognito_sub)
) ENGINE=InnoDB;


-- =============================================================
-- TABLE: companies
-- Stores company/recruiter accounts (linked to Cognito)
-- =============================================================
CREATE TABLE companies (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    cognito_sub     VARCHAR(128)    NOT NULL UNIQUE,
    company_name    VARCHAR(200)    NOT NULL,
    email           VARCHAR(255)    NOT NULL UNIQUE,
    industry        VARCHAR(100),
    website         VARCHAR(255),
    logo_url        VARCHAR(500),   -- S3 URL for company logo
    is_verified     BOOLEAN         NOT NULL DEFAULT FALSE,
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_companies_email  (email),
    INDEX idx_companies_sub    (cognito_sub)
) ENGINE=InnoDB;


-- =============================================================
-- TABLE: jobs
-- Walk-in interview postings made by companies
-- =============================================================
CREATE TABLE jobs (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    company_id          INT UNSIGNED    NOT NULL,
    role_title          VARCHAR(200)    NOT NULL,
    job_description     TEXT            NOT NULL,
    requirements        TEXT,
    package_lpa         DECIMAL(10, 2)  NOT NULL,       -- Salary in LPA
    experience_min_yrs  DECIMAL(4, 1)   NOT NULL DEFAULT 0,
    experience_max_yrs  DECIMAL(4, 1),
    interview_date      DATE            NOT NULL,
    venue_address       TEXT,
    total_slots         INT UNSIGNED    NOT NULL DEFAULT 0,  -- Sum of all slot capacities
    booked_slots        INT UNSIGNED    NOT NULL DEFAULT 0,  -- Running count of bookings
    candidates_required INT UNSIGNED    NOT NULL DEFAULT 1,
    status              ENUM('draft', 'active', 'closed', 'cancelled')
                                        NOT NULL DEFAULT 'active',
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_jobs_company
        FOREIGN KEY (company_id) REFERENCES companies(id)
        ON DELETE CASCADE,

    INDEX idx_jobs_company     (company_id),
    INDEX idx_jobs_date        (interview_date),
    INDEX idx_jobs_status      (status)
) ENGINE=InnoDB;


-- =============================================================
-- TABLE: slots
-- Individual time slots within a job posting
-- =============================================================
CREATE TABLE slots (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    job_id          INT UNSIGNED    NOT NULL,
    start_time      TIME            NOT NULL,   -- e.g. 10:00:00
    end_time        TIME            NOT NULL,   -- e.g. 11:00:00
    capacity        INT UNSIGNED    NOT NULL DEFAULT 1,  -- Max candidates per slot
    booked_count    INT UNSIGNED    NOT NULL DEFAULT 0,
    status          ENUM('available', 'full', 'cancelled')
                                    NOT NULL DEFAULT 'available',
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_slots_job
        FOREIGN KEY (job_id) REFERENCES jobs(id)
        ON DELETE CASCADE,

    INDEX idx_slots_job    (job_id),
    INDEX idx_slots_status (status),

    -- Prevent duplicate time ranges for the same job
    UNIQUE KEY uq_slot_time (job_id, start_time, end_time)
) ENGINE=InnoDB;


-- =============================================================
-- TABLE: bookings
-- A user's booking for a specific job slot
-- Core constraint: one active booking per user at a time
-- =============================================================
CREATE TABLE bookings (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id             INT UNSIGNED    NOT NULL,
    job_id              INT UNSIGNED    NOT NULL,
    slot_id             INT UNSIGNED    NOT NULL,
    status              ENUM(
                            'confirmed',    -- Active booking
                            'cancelled',    -- User or company cancelled
                            'completed',    -- Interview done
                            'no_show'       -- User did not attend
                        ) NOT NULL DEFAULT 'confirmed',
    confirmation_code   VARCHAR(32)     NOT NULL UNIQUE,  -- e.g. "WI-2024-ABCD1234"
    email_sent          BOOLEAN         NOT NULL DEFAULT FALSE,
    notes               TEXT,
    booked_at           TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_bookings_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_bookings_job
        FOREIGN KEY (job_id) REFERENCES jobs(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_bookings_slot
        FOREIGN KEY (slot_id) REFERENCES slots(id)
        ON DELETE CASCADE,

    -- Prevent a user from booking the same slot twice
    UNIQUE KEY uq_user_slot (user_id, slot_id),

    INDEX idx_bookings_user   (user_id),
    INDEX idx_bookings_job    (job_id),
    INDEX idx_bookings_slot   (slot_id),
    INDEX idx_bookings_status (status),
    INDEX idx_bookings_code   (confirmation_code)
) ENGINE=InnoDB;


-- =============================================================
-- TABLE: interview_sessions
-- AI mock interview sessions (AWS Bedrock powered)
-- =============================================================
CREATE TABLE interview_sessions (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNSIGNED    NOT NULL,
    job_id          INT UNSIGNED,               -- Optional: practice for a specific job
    session_title   VARCHAR(200),
    transcript      LONGTEXT,                   -- Full JSON conversation history
    score           TINYINT UNSIGNED,           -- AI-generated score 0–100
    feedback        TEXT,                       -- AI-generated feedback summary
    topics_covered  JSON,                       -- Array of topics e.g. ["DSA","System Design"]
    status          ENUM('in_progress', 'completed', 'abandoned')
                                    NOT NULL DEFAULT 'in_progress',
    started_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at        TIMESTAMP,

    CONSTRAINT fk_sessions_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_sessions_job
        FOREIGN KEY (job_id) REFERENCES jobs(id)
        ON DELETE SET NULL,

    INDEX idx_sessions_user   (user_id),
    INDEX idx_sessions_job    (job_id),
    INDEX idx_sessions_status (status)
) ENGINE=InnoDB;


-- =============================================================
-- STORED PROCEDURE: sp_book_slot
-- Atomically books a slot with all constraint checks:
--   1. User has no other active (confirmed) booking
--   2. Slot is available and not full
--   3. Job is still active
-- Returns: 0 = success, 1..4 = specific error codes
-- =============================================================
DELIMITER $$

CREATE PROCEDURE sp_book_slot(
    IN  p_user_id           INT UNSIGNED,
    IN  p_job_id            INT UNSIGNED,
    IN  p_slot_id           INT UNSIGNED,
    IN  p_confirmation_code VARCHAR(32),
    OUT p_result            TINYINT         -- 0=OK, 1=already booked, 2=slot full, 3=job closed, 4=duplicate
)
BEGIN
    DECLARE v_active_bookings   INT DEFAULT 0;
    DECLARE v_slot_available    INT DEFAULT 0;
    DECLARE v_job_active        INT DEFAULT 0;

    -- Start transaction for atomicity
    START TRANSACTION;

    -- Check 1: Does user already have an active (confirmed) booking?
    SELECT COUNT(*) INTO v_active_bookings
    FROM bookings
    WHERE user_id = p_user_id
      AND status = 'confirmed';

    IF v_active_bookings > 0 THEN
        SET p_result = 1;   -- User already has an active booking
        ROLLBACK;
    ELSE
        -- Check 2: Is the job still active?
        SELECT COUNT(*) INTO v_job_active
        FROM jobs
        WHERE id = p_job_id AND status = 'active';

        IF v_job_active = 0 THEN
            SET p_result = 3;   -- Job is not active
            ROLLBACK;
        ELSE
            -- Check 3: Is the slot available (with row lock to prevent race conditions)?
            SELECT COUNT(*) INTO v_slot_available
            FROM slots
            WHERE id = p_slot_id
              AND job_id = p_job_id
              AND status = 'available'
              AND booked_count < capacity
            FOR UPDATE;  -- Row-level lock prevents overbooking

            IF v_slot_available = 0 THEN
                SET p_result = 2;   -- Slot is full or unavailable
                ROLLBACK;
            ELSE
                -- All checks pass — perform the booking
                INSERT INTO bookings (user_id, job_id, slot_id, confirmation_code)
                VALUES (p_user_id, p_job_id, p_slot_id, p_confirmation_code);

                -- Increment slot booked_count
                UPDATE slots
                SET booked_count = booked_count + 1,
                    status = IF(booked_count + 1 >= capacity, 'full', 'available')
                WHERE id = p_slot_id;

                -- Increment job booked_slots
                UPDATE jobs
                SET booked_slots = booked_slots + 1
                WHERE id = p_job_id;

                SET p_result = 0;   -- Success
                COMMIT;
            END IF;
        END IF;
    END IF;
END$$

DELIMITER ;


-- =============================================================
-- SEED: Insert default admin user (update cognito_sub after deploy)
-- =============================================================
INSERT INTO users (cognito_sub, email, full_name, role)
VALUES ('REPLACE_WITH_COGNITO_SUB', 'admin@platform.com', 'Platform Admin', 'admin');