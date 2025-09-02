-- Espaço VIV Database Schema
-- PostgreSQL initialization script

-- Create database (run as superuser)
-- CREATE DATABASE espacoviv_db;
-- CREATE USER espacoviv_user WITH ENCRYPTED PASSWORD 'your_secure_password';
-- GRANT ALL PRIVILEGES ON DATABASE espacoviv_db TO espacoviv_user;

-- Connect to the database and create tables

-- Users table (massagistas and admins)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    cpf VARCHAR(14) UNIQUE,
    phone VARCHAR(20),
    user_type VARCHAR(20) DEFAULT 'massagista' CHECK (user_type IN ('massagista', 'admin')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Massagista profiles
CREATE TABLE IF NOT EXISTS massagista_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    specialties TEXT, -- JSON string with array of specialties
    unit_preference VARCHAR(50),
    bio TEXT,
    avatar_url VARCHAR(500),
    is_available BOOLEAN DEFAULT TRUE,
    working_hours TEXT, -- JSON string with schedule
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Units (locations)
CREATE TABLE IF NOT EXISTS units (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL, -- sp-perdizes, rj-centro, etc
    name VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(2) NOT NULL,
    address TEXT NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(255),
    working_hours TEXT, -- JSON string
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Service types
CREATE TABLE IF NOT EXISTS service_types (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL, -- shiatsu, relaxante, etc
    name VARCHAR(255) NOT NULL,
    description TEXT,
    duration_minutes INTEGER NOT NULL,
    price INTEGER, -- Price in cents
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Bookings
CREATE TABLE IF NOT EXISTS bookings (
    id SERIAL PRIMARY KEY,
    client_name VARCHAR(255) NOT NULL,
    client_email VARCHAR(255),
    client_phone VARCHAR(20) NOT NULL,
    service VARCHAR(100) NOT NULL,
    appointment_date TIMESTAMP NOT NULL,
    appointment_time VARCHAR(10) NOT NULL, -- HH:MM format
    duration_minutes INTEGER DEFAULT 60,
    unit_id INTEGER REFERENCES units(id) ON DELETE RESTRICT NOT NULL,
    massagista_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'cancelled', 'completed', 'no_show')),
    notes TEXT,
    promotion VARCHAR(255), -- If booking came from promotion
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE
);

-- Availability (optional for advanced scheduling)
CREATE TABLE IF NOT EXISTS availability (
    id SERIAL PRIMARY KEY,
    massagista_id INTEGER REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    unit_id INTEGER REFERENCES units(id) ON DELETE CASCADE NOT NULL,
    date DATE NOT NULL,
    start_time VARCHAR(10) NOT NULL, -- HH:MM
    end_time VARCHAR(10) NOT NULL,   -- HH:MM
    is_available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_cpf ON users(cpf);
CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings(appointment_date);
CREATE INDEX IF NOT EXISTS idx_bookings_unit ON bookings(unit_id);
CREATE INDEX IF NOT EXISTS idx_bookings_massagista ON bookings(massagista_id);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
CREATE INDEX IF NOT EXISTS idx_availability_date ON availability(date);
CREATE INDEX IF NOT EXISTS idx_availability_massagista ON availability(massagista_id);

-- Triggers to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_massagista_profiles_updated_at BEFORE UPDATE ON massagista_profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_units_updated_at BEFORE UPDATE ON units FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_service_types_updated_at BEFORE UPDATE ON service_types FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_bookings_updated_at BEFORE UPDATE ON bookings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_availability_updated_at BEFORE UPDATE ON availability FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert initial data
INSERT INTO units (code, name, city, state, address, phone) VALUES
('sp-perdizes', 'São Paulo - Perdizes', 'São Paulo', 'SP', 'R. Tavares Bastos, 564 – Perdizes, São Paulo – SP, 05012-020', NULL),
('sp-vila-clementino', 'São Paulo - Vila Clementino', 'São Paulo', 'SP', 'R. Dr. Bacelar, 82 – Vila Clementino, São Paulo – SP', NULL),
('sp-ingleses', 'São Paulo - Ingleses [Matriz]', 'São Paulo', 'SP', 'Rua dos Ingleses, 325 – Bela Vista, São Paulo – SP, 01329-030', '(11) 93387-6643'),
('sp-prudente', 'São Paulo - Prudente de Moraes', 'São Paulo', 'SP', 'R. Prudente de Moraes Neto, 81 São Paulo – SP', NULL),
('rj-centro', 'Rio de Janeiro - Centro', 'Rio de Janeiro', 'RJ', 'Av. Rio Branco, 185 - Sala 2103 - Centro, Rio de Janeiro - RJ, 20040-902', '(21) 3178-3233'),
('rj-copacabana', 'Rio de Janeiro - Copacabana', 'Rio de Janeiro', 'RJ', 'R. Barata Ribeiro, 391 - Copacabana, Rio de Janeiro - RJ, 22040-001', NULL),
('bsb-sudoeste', 'Brasília - Sudoeste', 'Brasília', 'DF', 'CCSW 01 Lote 04 Quadra C Loja 09 Edifício Portal Master Sudoeste', '(61) 3264-2277'),
('bsb-asa-sul', 'Brasília - Asa Sul', 'Brasília', 'DF', 'SHS Quadra 1 Bloco A Loja 18 Brasília - DF CEP: 70.311-000', '(61) 3254-0544');

INSERT INTO service_types (code, name, description, duration_minutes, price) VALUES
('shiatsu', 'Shiatsu', 'Técnica japonesa que utiliza pressão com os dedos em pontos específicos do corpo para equilibrar a energia vital e promover relaxamento profundo.', 60, 12000),
('quick', 'Quick Massage', 'Massagem expressa de 15 a 30 minutos focada em aliviar tensões do pescoço, ombros e costas. Ideal para o dia a dia corrido.', 30, 4000),
('relaxante', 'Relaxante', 'Massagem suave e envolvente que promove relaxamento completo, alivia o estresse e melhora a circulação sanguínea.', 60, 10000),
('terapeutica', 'Terapêutica', 'Massagem focada no tratamento de dores específicas e tensões musculares, utilizando técnicas especializadas.', 75, 15000),
('drenagem', 'Drenagem Linfática', 'Técnica específica para estimular o sistema linfático, reduzir inchaços e melhorar a circulação.', 60, 13000),
('pedras', 'Pedras Quentes', 'Massagem utilizando pedras aquecidas para relaxamento profundo e alívio de tensões musculares.', 90, 18000);

-- Create sample admin user (password: admin123)
INSERT INTO users (name, email, password_hash, user_type) VALUES 
('Administrador', 'admin@espacoviv.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LeUKqfmJ82VL5SRMW', 'admin');

-- Grant permissions to user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO espacoviv_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO espacoviv_user;