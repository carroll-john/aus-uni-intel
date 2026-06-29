CREATE TABLE IF NOT EXISTS providers (
    provider_id TEXT PRIMARY KEY,
    provider_name TEXT NOT NULL,
    state TEXT,
    provider_type TEXT NOT NULL,
    is_public BOOLEAN NOT NULL DEFAULT TRUE,
    country TEXT NOT NULL DEFAULT 'AU',
    website TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS provider_aliases (
    alias TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL REFERENCES providers(provider_id),
    source_system TEXT,
    confidence DOUBLE NOT NULL DEFAULT 1.0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS metrics (
    metric_id TEXT PRIMARY KEY,
    metric_name TEXT NOT NULL,
    metric_group TEXT NOT NULL,
    unit TEXT NOT NULL,
    value_type TEXT NOT NULL,
    definition TEXT NOT NULL,
    source_agency TEXT NOT NULL,
    source_dataset TEXT NOT NULL,
    source_table TEXT,
    source_line_item TEXT,
    is_calculated BOOLEAN NOT NULL DEFAULT FALSE,
    calculation_method TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (is_calculated = FALSE OR calculation_method IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS metric_dependencies (
    metric_id TEXT NOT NULL REFERENCES metrics(metric_id),
    depends_on_metric_id TEXT NOT NULL REFERENCES metrics(metric_id),
    dependency_role TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (metric_id, depends_on_metric_id)
);

CREATE TABLE IF NOT EXISTS source_files (
    source_file_id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    local_path TEXT NOT NULL,
    file_format TEXT NOT NULL,
    reporting_year INTEGER,
    downloaded_at TIMESTAMP NOT NULL,
    checksum_sha256 TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    license TEXT,
    publication_date TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS facts (
    fact_id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL REFERENCES providers(provider_id),
    metric_id TEXT NOT NULL REFERENCES metrics(metric_id),
    source_file_id TEXT NOT NULL REFERENCES source_files(source_file_id),
    reporting_year INTEGER NOT NULL,
    period_start DATE,
    period_end DATE,
    dimension_scope TEXT NOT NULL,
    value DOUBLE NOT NULL,
    unit TEXT NOT NULL,
    source_row_number INTEGER NOT NULL,
    source_provider_name TEXT NOT NULL,
    source_line_item TEXT NOT NULL,
    dimensions_json TEXT NOT NULL DEFAULT '{}',
    ingested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (provider_id, metric_id, source_file_id, reporting_year, dimension_scope)
);

CREATE TABLE IF NOT EXISTS source_datasets (
    dataset_id TEXT PRIMARY KEY,
    dataset_name TEXT NOT NULL,
    source_agency TEXT NOT NULL,
    landing_page_url TEXT NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS data_quality_checks (
    check_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    source_file_id TEXT,
    check_name TEXT NOT NULL,
    status TEXT NOT NULL,
    severity TEXT NOT NULL,
    observed_value TEXT,
    expected_value TEXT,
    details TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (status IN ('pass', 'warn', 'fail')),
    CHECK (severity IN ('info', 'warning', 'error'))
);

CREATE TABLE IF NOT EXISTS stg_finance_rows (
    row_number INTEGER NOT NULL,
    source_system TEXT NOT NULL,
    institution_scope TEXT NOT NULL,
    reporting_year INTEGER NOT NULL,
    statement_code TEXT NOT NULL,
    source_provider_name TEXT NOT NULL,
    line_item TEXT NOT NULL,
    raw_value TEXT NOT NULL,
    numeric_value DOUBLE,
    source_file_id TEXT NOT NULL,
    provider_id TEXT,
    metric_id TEXT,
    match_status TEXT NOT NULL,
    match_confidence DOUBLE,
    load_run_id TEXT NOT NULL,
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS stg_student_rows (
    row_number INTEGER NOT NULL,
    source_table TEXT NOT NULL,
    sheet_name TEXT NOT NULL,
    source_provider_name TEXT NOT NULL,
    metric_id TEXT NOT NULL,
    reporting_year INTEGER NOT NULL,
    raw_value TEXT NOT NULL,
    numeric_value DOUBLE,
    source_file_id TEXT NOT NULL,
    provider_id TEXT,
    match_status TEXT NOT NULL,
    match_confidence DOUBLE,
    dimensions_json TEXT NOT NULL DEFAULT '{}',
    load_run_id TEXT NOT NULL,
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS stg_herdc_rows (
    row_number INTEGER NOT NULL,
    hep_code TEXT,
    source_provider_name TEXT NOT NULL,
    metric_id TEXT NOT NULL,
    reporting_year INTEGER NOT NULL,
    raw_value TEXT NOT NULL,
    numeric_value DOUBLE,
    source_file_id TEXT NOT NULL,
    provider_id TEXT,
    match_status TEXT NOT NULL,
    match_confidence DOUBLE,
    dimensions_json TEXT NOT NULL DEFAULT '{}',
    load_run_id TEXT NOT NULL,
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS stg_qilt_rows (
    row_number INTEGER NOT NULL,
    source_table TEXT NOT NULL,
    source_provider_name TEXT NOT NULL,
    metric_id TEXT NOT NULL,
    reporting_year INTEGER NOT NULL,
    raw_value TEXT NOT NULL,
    numeric_value DOUBLE,
    ci_lower DOUBLE,
    ci_upper DOUBLE,
    source_file_id TEXT NOT NULL,
    provider_id TEXT,
    match_status TEXT NOT NULL,
    match_confidence DOUBLE,
    dimensions_json TEXT NOT NULL DEFAULT '{}',
    load_run_id TEXT NOT NULL,
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_facts_provider_year ON facts(provider_id, reporting_year);
CREATE INDEX IF NOT EXISTS idx_facts_metric_year ON facts(metric_id, reporting_year);
CREATE INDEX IF NOT EXISTS idx_stg_finance_source_file ON stg_finance_rows(source_file_id);
CREATE INDEX IF NOT EXISTS idx_stg_student_source_file ON stg_student_rows(source_file_id);
CREATE INDEX IF NOT EXISTS idx_stg_herdc_source_file ON stg_herdc_rows(source_file_id);
CREATE INDEX IF NOT EXISTS idx_stg_qilt_source_file ON stg_qilt_rows(source_file_id);
