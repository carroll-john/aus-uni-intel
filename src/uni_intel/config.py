from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
WAREHOUSE_DIR = DATA_DIR / "warehouse"
QUALITY_DIR = DATA_DIR / "quality"
SEED_DIR = DATA_DIR / "seed"
DB_PATH = WAREHOUSE_DIR / "university_intel.duckdb"
SCHEMA_PATH = PROJECT_ROOT / "sql" / "schema.sql"

FINANCE_2024_URL = (
    "https://www.education.gov.au/download/19832/"
    "finance-2024-financial-reports-higher-education-providers/43010/"
    "2024-higher-education-providers-finance-tables/csv"
)
FINANCE_PUBLICATION_URL = (
    "https://www.education.gov.au/higher-education-publications/resources/"
    "finance-2024-financial-reports-higher-education-providers"
)
FINANCE_URLS = {
    2018: (
        "https://www.education.gov.au/download/9022/"
        "finance-2018-financial-reports-higher-education-providers/7408/"
        "2018-higher-education-providers-finance-tables/xlsx"
    ),
    2019: (
        "https://www.education.gov.au/download/12753/"
        "finance-2019-financial-reports-higher-education-providers/12739/"
        "2019-higher-education-providers-finance-tables/xlsx"
    ),
    2020: (
        "https://www.education.gov.au/download/15001/"
        "finance-2020-financial-reports-higher-education-providers/31448/"
        "2020-higher-education-providers-finance-tables/xlsx"
    ),
    2021: (
        "https://www.education.gov.au/download/15002/"
        "finance-2021-financial-reports-higher-education-providers/31456/"
        "2021-higher-education-providers-finance-tables/xlsx"
    ),
    2022: (
        "https://www.education.gov.au/download/17857/"
        "finance-2022-financial-reports-higher-education-providers/36064/"
        "2022-higher-education-providers-finance-tables/csv"
    ),
    2023: (
        "https://www.education.gov.au/download/18872/"
        "finance-2023-financial-reports-higher-education-providers/40112/"
        "2023-higher-education-providers-finance-tables/csv"
    ),
    2024: FINANCE_2024_URL,
}
FINANCE_PUBLICATION_URLS = {
    2018: (
        "https://www.education.gov.au/higher-education-publications/resources/"
        "finance-publication-2018"
    ),
    2019: (
        "https://www.education.gov.au/higher-education-publications/resources/"
        "finance-publication-2019"
    ),
    2020: (
        "https://www.education.gov.au/higher-education-publications/resources/"
        "finance-publication-2020"
    ),
    2021: (
        "https://www.education.gov.au/higher-education-publications/resources/"
        "finance-publication-2021"
    ),
    2022: (
        "https://www.education.gov.au/higher-education-publications/resources/"
        "2022-higher-education-providers-finance-tables"
    ),
    2023: (
        "https://www.education.gov.au/higher-education-publications/resources/"
        "finance-2023-financial-reports-higher-education-providers"
    ),
    2024: FINANCE_PUBLICATION_URL,
}

STUDENT_SUMMARY_2024_URL = (
    "https://www.education.gov.au/download/19478/"
    "2024-student-summary-tables/41926/document/xlsx"
)
STUDENT_COMPLETIONS_2024_URL = (
    "https://www.education.gov.au/download/19502/"
    "2024-section-14-award-course-completions/41967/document/xlsx"
)
STUDENT_PUBLICATION_URL = "https://www.education.gov.au/higher-education-statistics/student-data"
STUDENT_SECTION_YEARS = tuple(range(2018, 2025))
STUDENT_ANNUAL_PAGE_URLS = {
    year: (
        "https://www.education.gov.au/higher-education-statistics/student-data/"
        f"selected-higher-education-statistics-{year}-student-data"
    )
    for year in STUDENT_SECTION_YEARS
}

HERDC_RESEARCH_INCOME_URL = (
    "https://www.education.gov.au/download/3974/"
    "research-and-development-income-time-series/43586/"
    "research-income-time-seris/xlsx"
)
HERDC_PUBLICATION_URL = (
    "https://www.education.gov.au/research-block-grants/resources/"
    "research-income-time-series"
)

QILT_SES_2024_URL = (
    "https://qilt.edu.au/docs/default-source/default-document-library/"
    "ses_2024_national_report_tables.zip?sfvrsn=f1ce2f6e_1"
)
QILT_SES_PUBLICATION_URL = "https://qilt.edu.au/surveys/student-experience-survey-%28ses%29"
