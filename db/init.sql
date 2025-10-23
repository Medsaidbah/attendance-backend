-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Students table
CREATE TABLE students (
    id SERIAL PRIMARY KEY,
    matricule VARCHAR(50) UNIQUE NOT NULL,
    nom VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Geofences table with PostGIS geography column
CREATE TABLE geofences (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    polygon GEOGRAPHY(POLYGON, 4326) NOT NULL,
    margin_m INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create GIST spatial index on geofences polygon
CREATE INDEX idx_geofences_polygon ON geofences USING GIST (polygon);

-- Time windows table
CREATE TABLE time_windows (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Events table (presence check results)
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES students(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL CHECK (status IN ('present', 'late', 'absent', 'outside')),
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    geofence_id INTEGER REFERENCES geofences(id) ON DELETE SET NULL,
    method VARCHAR(20) NOT NULL CHECK (method IN ('manual', 'auto')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on (student_id, created_at) for efficient queries
CREATE INDEX idx_events_student_created ON events (student_id, created_at);

-- Attendances table (decisions - processed attendance records)
CREATE TABLE attendances (
    id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES students(id) ON DELETE CASCADE,
    event_id INTEGER REFERENCES events(id) ON DELETE CASCADE,
    time_window_id INTEGER REFERENCES time_windows(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL CHECK (status IN ('present', 'late', 'absent', 'outside')),
    geofence_id INTEGER REFERENCES geofences(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit logs table
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    record_id INTEGER NOT NULL,
    action VARCHAR(20) NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    old_values JSONB,
    new_values JSONB,
    user_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample data
INSERT INTO students (matricule, nom, prenom) VALUES 
('STU001', 'Dupont', 'Jean'),
('STU002', 'Martin', 'Marie'),
('STU003', 'Bernard', 'Pierre');

INSERT INTO time_windows (name, start_time, end_time) VALUES 
('Entrée', '08:00:00', '08:30:00'),
('Pause', '10:15:00', '10:30:00'),
('Sortie', '17:00:00', '17:30:00');

-- Insert a sample geofence (campus polygon around Paris)
INSERT INTO geofences (name, polygon, margin_m) VALUES 
('Campus Principal', 
 ST_GeogFromText('POLYGON((2.3522 48.8566, 2.3522 48.8576, 2.3532 48.8576, 2.3532 48.8566, 2.3522 48.8566))'),
 50);

