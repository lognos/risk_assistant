-- Monte Carlo Correlation Support - Full Normalization Schema
-- Migration 001: Add correlation support tables and columns
-- Author: Monte Carlo Engine
-- Date: 2025-08-06

-- =====================================================
-- 1. CREATE LOOKUP TABLES
-- =====================================================

-- Disciplines lookup table
CREATE TABLE IF NOT EXISTS disciplines (
    id SERIAL PRIMARY KEY,
    discipline_name TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert common disciplines
INSERT INTO disciplines (discipline_name, description) VALUES
    ('Mechanical', 'Mechanical engineering and equipment'),
    ('Civil', 'Civil engineering and infrastructure'),
    ('Electrical', 'Electrical systems and components'),
    ('IT', 'Information technology and software'),
    ('Process', 'Process engineering and operations'),
    ('Instrumentation', 'Control and instrumentation systems'),
    ('HSE', 'Health, safety, and environmental'),
    ('General', 'General or uncategorized items')
ON CONFLICT (discipline_name) DO NOTHING;

-- Project phases lookup table
CREATE TABLE IF NOT EXISTS project_phases (
    id SERIAL PRIMARY KEY,
    phase_name TEXT UNIQUE NOT NULL,
    phase_order INTEGER NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert common project phases
INSERT INTO project_phases (phase_name, phase_order, description) VALUES
    ('Initiation', 1, 'Project initiation and feasibility'),
    ('Planning', 2, 'Detailed planning and design'),
    ('Execution', 3, 'Project execution and construction'),
    ('Commissioning', 4, 'Testing and commissioning'),
    ('Closeout', 5, 'Project closeout and handover'),
    ('Phase 1', 10, 'Generic phase 1'),
    ('Phase 2', 20, 'Generic phase 2'),
    ('Phase 3', 30, 'Generic phase 3')
ON CONFLICT (phase_name) DO NOTHING;

-- Locations lookup table
CREATE TABLE IF NOT EXISTS locations (
    id SERIAL PRIMARY KEY,
    location_name TEXT UNIQUE NOT NULL,
    location_type TEXT CHECK (location_type IN ('site', 'facility', 'office', 'warehouse', 'other')),
    parent_location_id INTEGER REFERENCES locations(id),
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert common locations
INSERT INTO locations (location_name, location_type, description) VALUES
    ('Main Site', 'site', 'Primary project site'),
    ('Site A', 'site', 'Site A location'),
    ('Site B', 'site', 'Site B location'),
    ('HQ', 'office', 'Headquarters'),
    ('Remote', 'other', 'Remote or distributed location')
ON CONFLICT (location_name) DO NOTHING;

-- Risk categories lookup table
CREATE TABLE IF NOT EXISTS risk_categories (
    id SERIAL PRIMARY KEY,
    category_name TEXT UNIQUE NOT NULL,
    default_correlation FLOAT CHECK (default_correlation >= 0 AND default_correlation <= 1),
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert risk categories with default correlations
INSERT INTO risk_categories (category_name, default_correlation, description) VALUES
    ('regulatory', 0.6, 'Regulatory and compliance risks'),
    ('weather', 0.7, 'Weather and environmental risks'),
    ('supply_chain', 0.5, 'Supply chain and procurement risks'),
    ('technical', 0.4, 'Technical and engineering risks'),
    ('financial', 0.5, 'Financial and economic risks'),
    ('safety', 0.4, 'Safety and security risks'),
    ('political', 0.6, 'Political and geopolitical risks'),
    ('operational', 0.3, 'Operational and process risks'),
    ('general', 0.2, 'General or uncategorized risks')
ON CONFLICT (category_name) DO NOTHING;

-- =====================================================
-- 2. ADD COLUMNS TO EXISTING TABLES
-- =====================================================

-- Add columns to capex_items
ALTER TABLE capex_items 
ADD COLUMN IF NOT EXISTS discipline_id INTEGER,
ADD COLUMN IF NOT EXISTS phase_id INTEGER,
ADD COLUMN IF NOT EXISTS location_id INTEGER;

-- Add foreign key constraints for capex_items
ALTER TABLE capex_items
ADD CONSTRAINT fk_capex_discipline FOREIGN KEY (discipline_id) REFERENCES disciplines(id) ON DELETE SET NULL,
ADD CONSTRAINT fk_capex_phase FOREIGN KEY (phase_id) REFERENCES project_phases(id) ON DELETE SET NULL,
ADD CONSTRAINT fk_capex_location FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE SET NULL;

-- Add columns to risks
ALTER TABLE risks
ADD COLUMN IF NOT EXISTS risk_log TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS risk_category_id INTEGER;

-- Add foreign key constraint for risks
ALTER TABLE risks
ADD CONSTRAINT fk_risk_category FOREIGN KEY (risk_category_id) REFERENCES risk_categories(id) ON DELETE SET NULL;

-- =====================================================
-- 3. CREATE DEPENDENCIES TABLE
-- =====================================================

CREATE TABLE IF NOT EXISTS item_dependencies (
    id SERIAL PRIMARY KEY,
    from_type TEXT CHECK (from_type IN ('capex', 'risk')) NOT NULL,
    from_id TEXT NOT NULL,
    to_type TEXT CHECK (to_type IN ('capex', 'risk')) NOT NULL,
    to_id TEXT NOT NULL,
    dependency_strength TEXT CHECK (dependency_strength IN ('weak', 'moderate', 'strong')) NOT NULL,
    dependency_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT,
    UNIQUE(from_type, from_id, to_type, to_id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_dependencies_from ON item_dependencies(from_type, from_id);
CREATE INDEX IF NOT EXISTS idx_dependencies_to ON item_dependencies(to_type, to_id);

-- =====================================================
-- 4. CREATE VIEWS FOR EASIER QUERYING
-- =====================================================

-- View for capex items with joined lookup data
CREATE OR REPLACE VIEW v_capex_items_with_lookups AS
SELECT 
    ci.*,
    d.discipline_name,
    pp.phase_name,
    pp.phase_order,
    l.location_name,
    l.location_type
FROM capex_items ci
LEFT JOIN disciplines d ON ci.discipline_id = d.id
LEFT JOIN project_phases pp ON ci.phase_id = pp.id
LEFT JOIN locations l ON ci.location_id = l.id;

-- View for risks with joined lookup data
CREATE OR REPLACE VIEW v_risks_with_lookups AS
SELECT 
    r.*,
    rc.category_name,
    rc.default_correlation
FROM risks r
LEFT JOIN risk_categories rc ON r.risk_category_id = rc.id;

-- View for correlation analysis
CREATE OR REPLACE VIEW v_correlation_pairs AS
SELECT 
    'capex-capex' as pair_type,
    ci1.item_id as item1_id,
    ci1.item_name as item1_name,
    ci2.item_id as item2_id,
    ci2.item_name as item2_name,
    CASE 
        WHEN ci1.item_owner = ci2.item_owner THEN 0.3
        ELSE 0
    END +
    CASE 
        WHEN ci1.discipline_id = ci2.discipline_id THEN 0.4
        ELSE 0
    END +
    CASE 
        WHEN ci1.phase_id = ci2.phase_id THEN 0.2
        ELSE 0
    END +
    CASE 
        WHEN ci1.location_id = ci2.location_id THEN 0.5
        ELSE 0
    END as correlation_coefficient
FROM capex_items ci1
CROSS JOIN capex_items ci2
WHERE ci1.item_id < ci2.item_id
    AND (ci1.item_owner = ci2.item_owner 
         OR ci1.discipline_id = ci2.discipline_id
         OR ci1.phase_id = ci2.phase_id
         OR ci1.location_id = ci2.location_id)

UNION ALL

SELECT 
    'risk-risk' as pair_type,
    r1.risk_id as item1_id,
    r1.risk_name as item1_name,
    r2.risk_id as item2_id,
    r2.risk_name as item2_name,
    CASE 
        WHEN r1.risk_owner = r2.risk_owner THEN 0.3
        ELSE 0
    END +
    CASE 
        WHEN r1.risk_category_id = r2.risk_category_id THEN rc.default_correlation
        ELSE 0
    END as correlation_coefficient
FROM risks r1
CROSS JOIN risks r2
LEFT JOIN risk_categories rc ON r1.risk_category_id = rc.id
WHERE r1.risk_id < r2.risk_id
    AND (r1.risk_owner = r2.risk_owner 
         OR r1.risk_category_id = r2.risk_category_id);

-- =====================================================
-- 5. CREATE HELPER FUNCTIONS
-- =====================================================

-- Function to get discipline ID by name
CREATE OR REPLACE FUNCTION get_discipline_id(p_discipline_name TEXT)
RETURNS INTEGER AS $$
DECLARE
    v_id INTEGER;
BEGIN
    SELECT id INTO v_id FROM disciplines WHERE discipline_name = p_discipline_name;
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get phase ID by name
CREATE OR REPLACE FUNCTION get_phase_id(p_phase_name TEXT)
RETURNS INTEGER AS $$
DECLARE
    v_id INTEGER;
BEGIN
    SELECT id INTO v_id FROM project_phases WHERE phase_name = p_phase_name;
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get location ID by name
CREATE OR REPLACE FUNCTION get_location_id(p_location_name TEXT)
RETURNS INTEGER AS $$
DECLARE
    v_id INTEGER;
BEGIN
    SELECT id INTO v_id FROM locations WHERE location_name = p_location_name;
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get risk category ID by name
CREATE OR REPLACE FUNCTION get_risk_category_id(p_category_name TEXT)
RETURNS INTEGER AS $$
DECLARE
    v_id INTEGER;
BEGIN
    SELECT id INTO v_id FROM risk_categories WHERE category_name = p_category_name;
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 6. MIGRATION HELPERS
-- =====================================================

-- Update triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add triggers to new tables
CREATE TRIGGER update_disciplines_updated_at BEFORE UPDATE ON disciplines
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_project_phases_updated_at BEFORE UPDATE ON project_phases
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_locations_updated_at BEFORE UPDATE ON locations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_risk_categories_updated_at BEFORE UPDATE ON risk_categories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_item_dependencies_updated_at BEFORE UPDATE ON item_dependencies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =====================================================
-- 7. SAMPLE DATA MIGRATION (Optional)
-- =====================================================

-- Example: Migrate existing text data to lookup IDs
-- Uncomment and modify as needed based on existing data patterns

/*
-- Update capex_items with discipline IDs based on existing patterns
UPDATE capex_items SET discipline_id = get_discipline_id('Mechanical') 
WHERE item_name ILIKE '%equipment%' OR item_name ILIKE '%pump%' OR item_name ILIKE '%compressor%';

UPDATE capex_items SET discipline_id = get_discipline_id('Civil') 
WHERE item_name ILIKE '%building%' OR item_name ILIKE '%foundation%' OR item_name ILIKE '%structure%';

UPDATE capex_items SET discipline_id = get_discipline_id('IT') 
WHERE item_name ILIKE '%software%' OR item_name ILIKE '%system%' OR item_name ILIKE '%network%';

-- Set default values for nulls
UPDATE capex_items SET discipline_id = get_discipline_id('General') WHERE discipline_id IS NULL;
UPDATE capex_items SET phase_id = get_phase_id('Phase 1') WHERE phase_id IS NULL;
UPDATE capex_items SET location_id = get_location_id('Main Site') WHERE location_id IS NULL;

-- Update risks with category IDs based on patterns
UPDATE risks SET risk_category_id = get_risk_category_id('weather') 
WHERE risk_name ILIKE '%weather%' OR risk_name ILIKE '%rain%' OR risk_name ILIKE '%storm%';

UPDATE risks SET risk_category_id = get_risk_category_id('supply_chain') 
WHERE risk_name ILIKE '%supply%' OR risk_name ILIKE '%vendor%' OR risk_name ILIKE '%delivery%';

UPDATE risks SET risk_category_id = get_risk_category_id('regulatory') 
WHERE risk_name ILIKE '%regulation%' OR risk_name ILIKE '%compliance%' OR risk_name ILIKE '%permit%';

-- Set default risk log dates to created_at where null
UPDATE risks SET risk_log = created_at WHERE risk_log IS NULL;
*/

-- =====================================================
-- 8. ROLLBACK SCRIPT (Save separately)
-- =====================================================

/*
-- To rollback this migration:

-- Remove views
DROP VIEW IF EXISTS v_correlation_pairs;
DROP VIEW IF EXISTS v_risks_with_lookups;
DROP VIEW IF EXISTS v_capex_items_with_lookups;

-- Remove functions
DROP FUNCTION IF EXISTS get_discipline_id(TEXT);
DROP FUNCTION IF EXISTS get_phase_id(TEXT);
DROP FUNCTION IF EXISTS get_location_id(TEXT);
DROP FUNCTION IF EXISTS get_risk_category_id(TEXT);
DROP FUNCTION IF EXISTS update_updated_at();

-- Remove foreign key constraints
ALTER TABLE capex_items DROP CONSTRAINT IF EXISTS fk_capex_discipline;
ALTER TABLE capex_items DROP CONSTRAINT IF EXISTS fk_capex_phase;
ALTER TABLE capex_items DROP CONSTRAINT IF EXISTS fk_capex_location;
ALTER TABLE risks DROP CONSTRAINT IF EXISTS fk_risk_category;

-- Remove columns
ALTER TABLE capex_items DROP COLUMN IF EXISTS discipline_id;
ALTER TABLE capex_items DROP COLUMN IF EXISTS phase_id;
ALTER TABLE capex_items DROP COLUMN IF EXISTS location_id;
ALTER TABLE risks DROP COLUMN IF EXISTS risk_log;
ALTER TABLE risks DROP COLUMN IF EXISTS risk_category_id;

-- Drop tables
DROP TABLE IF EXISTS item_dependencies;
DROP TABLE IF EXISTS risk_categories;
DROP TABLE IF EXISTS locations;
DROP TABLE IF EXISTS project_phases;
DROP TABLE IF EXISTS disciplines;
*/
