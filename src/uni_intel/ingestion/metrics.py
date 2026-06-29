from __future__ import annotations

import re


SOURCE_AGENCY = "Australian Government Department of Education"
FINANCE_SOURCE_DATASET = "Financial Reports of Higher Education Providers"
FINANCE_SOURCE_TABLE = "Annual provider finance tables"
STUDENT_SOURCE_DATASET = "Selected Higher Education Statistics Student Data"
HERDC_SOURCE_DATASET = "Research and Development Income Time Series 1992-2024"
QILT_SOURCE_AGENCY = "QILT"
QILT_SOURCE_DATASET = "Student Experience Survey National Report Tables"


def slugify(value: str) -> str:
    value = value.lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def finance_metric_id(line_item: str) -> str:
    return f"finance_{slugify(line_item)}"


def infer_finance_group(line_item: str) -> str:
    text = line_item.lower()
    if "revenue" in text or "income" in text or "fees" in text:
        return "Finance - revenue"
    if "expense" in text or "expenses" in text or "costs" in text or "loss" in text:
        return "Finance - expenses"
    if "assets" in text:
        return "Finance - assets"
    if "liabilities" in text:
        return "Finance - liabilities"
    if "equity" in text or "result" in text:
        return "Finance - results"
    return "Finance"


def finance_metric_record(line_item: str) -> dict[str, object]:
    return {
        "metric_id": finance_metric_id(line_item),
        "metric_name": line_item,
        "metric_group": infer_finance_group(line_item),
        "unit": "AUD thousands",
        "value_type": "currency",
        "definition": (
            f"Published finance statement line item: {line_item}. Values are "
            "reported as Australian dollars in thousands in the Department of "
            "Education provider finance tables."
        ),
        "source_agency": SOURCE_AGENCY,
        "source_dataset": FINANCE_SOURCE_DATASET,
        "source_table": FINANCE_SOURCE_TABLE,
        "source_line_item": line_item,
        "is_calculated": False,
        "calculation_method": None,
    }


def source_metric_record(
    metric_id: str,
    metric_name: str,
    metric_group: str,
    unit: str,
    value_type: str,
    definition: str,
    source_agency: str,
    source_dataset: str,
    source_table: str,
    source_line_item: str,
) -> dict[str, object]:
    return {
        "metric_id": metric_id,
        "metric_name": metric_name,
        "metric_group": metric_group,
        "unit": unit,
        "value_type": value_type,
        "definition": definition,
        "source_agency": source_agency,
        "source_dataset": source_dataset,
        "source_table": source_table,
        "source_line_item": source_line_item,
        "is_calculated": False,
        "calculation_method": None,
    }


STUDENT_METRICS = [
    source_metric_record(
        "student_commencing_enrolments",
        "Commencing student enrolments",
        "Student - enrolments",
        "students",
        "count",
        "Count of commencing student enrolments reported by institution.",
        SOURCE_AGENCY,
        STUDENT_SOURCE_DATASET,
        "Student section workbooks",
        "Commencing Students",
    ),
    source_metric_record(
        "student_total_enrolments",
        "All student enrolments",
        "Student - enrolments",
        "students",
        "count",
        "Count of all student enrolments reported by institution.",
        SOURCE_AGENCY,
        STUDENT_SOURCE_DATASET,
        "Student section workbooks",
        "All Students",
    ),
    source_metric_record(
        "student_commencing_load_eftsl",
        "Commencing actual student load (EFTSL)",
        "Student - load",
        "EFTSL",
        "number",
        "Actual student load in equivalent full-time student load for commencing students.",
        SOURCE_AGENCY,
        STUDENT_SOURCE_DATASET,
        "Student section workbooks",
        "Commencing Students EFTSL",
    ),
    source_metric_record(
        "student_total_load_eftsl",
        "All actual student load (EFTSL)",
        "Student - load",
        "EFTSL",
        "number",
        "Actual student load in equivalent full-time student load for all students.",
        SOURCE_AGENCY,
        STUDENT_SOURCE_DATASET,
        "Student section workbooks",
        "All Students EFTSL",
    ),
    source_metric_record(
        "student_award_course_completions",
        "Award course completions",
        "Student - completions",
        "completions",
        "count",
        "Award course completions for all students by state and higher education institution.",
        SOURCE_AGENCY,
        STUDENT_SOURCE_DATASET,
        "Section 14 Award Course Completions",
        "Award Course Completions",
    ),
]


HERDC_METRICS = [
    source_metric_record(
        "herdc_research_income_total",
        "HERDC total research income",
        "Research - income",
        "AUD",
        "currency",
        "Total research and development income reported through HERDC.",
        SOURCE_AGENCY,
        HERDC_SOURCE_DATASET,
        "Summary by Category",
        "Total",
    ),
    *[
        source_metric_record(
            f"herdc_research_income_category_{category}",
            f"HERDC category {category} research income",
            "Research - income",
            "AUD",
            "currency",
            f"Research and development income reported through HERDC Category {category}.",
            SOURCE_AGENCY,
            HERDC_SOURCE_DATASET,
            "Summary by Category",
            f"Category {category}",
        )
        for category in range(1, 5)
    ],
]


QILT_METRICS = [
    source_metric_record(
        "qilt_skills_development_positive_rating",
        "Skills development positive rating",
        "QILT - student experience",
        "percent",
        "percentage",
        "Percentage positive rating for QILT Student Experience Survey skills development focus area.",
        QILT_SOURCE_AGENCY,
        QILT_SOURCE_DATASET,
        "SES provider-level institution tables",
        "Skills Development",
    ),
    source_metric_record(
        "qilt_peer_engagement_positive_rating",
        "Peer engagement positive rating",
        "QILT - student experience",
        "percent",
        "percentage",
        "Percentage positive rating for QILT Student Experience Survey peer engagement focus area.",
        QILT_SOURCE_AGENCY,
        QILT_SOURCE_DATASET,
        "SES provider-level institution tables",
        "Peer Engagement",
    ),
    source_metric_record(
        "qilt_teaching_quality_engagement_positive_rating",
        "Teaching quality and engagement positive rating",
        "QILT - student experience",
        "percent",
        "percentage",
        "Percentage positive rating for QILT Student Experience Survey teaching quality and engagement focus area.",
        QILT_SOURCE_AGENCY,
        QILT_SOURCE_DATASET,
        "SES provider-level institution tables",
        "Teaching Quality and Engagement",
    ),
    source_metric_record(
        "qilt_student_support_services_positive_rating",
        "Student support and services positive rating",
        "QILT - student experience",
        "percent",
        "percentage",
        "Percentage positive rating for QILT Student Experience Survey student support and services focus area.",
        QILT_SOURCE_AGENCY,
        QILT_SOURCE_DATASET,
        "SES provider-level institution tables",
        "Student Support and Services",
    ),
    source_metric_record(
        "qilt_learning_resources_positive_rating",
        "Learning resources positive rating",
        "QILT - student experience",
        "percent",
        "percentage",
        "Percentage positive rating for QILT Student Experience Survey learning resources focus area.",
        QILT_SOURCE_AGENCY,
        QILT_SOURCE_DATASET,
        "SES provider-level institution tables",
        "Learning Resources",
    ),
    source_metric_record(
        "qilt_overall_educational_experience_positive_rating",
        "Overall educational experience positive rating",
        "QILT - student experience",
        "percent",
        "percentage",
        "Percentage positive rating for QILT Student Experience Survey quality of entire educational experience item.",
        QILT_SOURCE_AGENCY,
        QILT_SOURCE_DATASET,
        "SES provider-level institution tables",
        "Quality of entire educational experience",
    ),
]


CALCULATED_METRICS = [
    {
        "metric_id": "calc_operating_margin",
        "metric_name": "Operating margin",
        "metric_group": "Calculated - finance",
        "unit": "percent",
        "value_type": "percentage",
        "definition": "Operating result from continuing operations divided by total revenues from continuing operations.",
        "source_agency": "Derived from Australian Government Department of Education source metrics",
        "source_dataset": "Calculated metrics",
        "source_table": "facts",
        "source_line_item": "Operating Result from Continuing Operations / Total Revenues from Continuing Operations",
        "is_calculated": True,
        "calculation_method": (
            "100 * finance_operating_result_from_continuing_operations / "
            "finance_total_revenues_from_continuing_operations_including_deferred_superannuation"
        ),
    },
    {
        "metric_id": "calc_research_income_share_of_revenue",
        "metric_name": "Research income share of revenue",
        "metric_group": "Calculated - research",
        "unit": "percent",
        "value_type": "percentage",
        "definition": "HERDC total research income divided by total revenues from continuing operations.",
        "source_agency": "Derived from Australian Government Department of Education source metrics",
        "source_dataset": "Calculated metrics",
        "source_table": "facts",
        "source_line_item": "HERDC total research income / finance total revenues",
        "is_calculated": True,
        "calculation_method": (
            "100 * herdc_research_income_total / "
            "(finance_total_revenues_from_continuing_operations_including_deferred_superannuation * 1000)"
        ),
    },
    {
        "metric_id": "calc_research_income_per_enrolment",
        "metric_name": "Research income per enrolment",
        "metric_group": "Calculated - research",
        "unit": "AUD per student",
        "value_type": "currency",
        "definition": "HERDC total research income divided by all student enrolments.",
        "source_agency": "Derived from Australian Government Department of Education source metrics",
        "source_dataset": "Calculated metrics",
        "source_table": "facts",
        "source_line_item": "HERDC total research income / all student enrolments",
        "is_calculated": True,
        "calculation_method": "herdc_research_income_total / student_total_enrolments",
    },
]
