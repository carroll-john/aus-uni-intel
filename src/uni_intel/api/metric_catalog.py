from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogMetric:
    item_id: str
    label: str
    catalog_group: str
    metric_id: str | None
    preferred_scope: str | None
    source_status: str
    source_note: str


def available(
    item_id: str,
    label: str,
    catalog_group: str,
    metric_id: str,
    preferred_scope: str,
    source_note: str,
) -> CatalogMetric:
    return CatalogMetric(
        item_id=item_id,
        label=label,
        catalog_group=catalog_group,
        metric_id=metric_id,
        preferred_scope=preferred_scope,
        source_status="available",
        source_note=source_note,
    )


def unavailable(
    item_id: str,
    label: str,
    catalog_group: str,
    source_status: str,
    source_note: str,
) -> CatalogMetric:
    return CatalogMetric(
        item_id=item_id,
        label=label,
        catalog_group=catalog_group,
        metric_id=None,
        preferred_scope=None,
        source_status=source_status,
        source_note=source_note,
    )


CURATED_METRIC_CATALOG: list[CatalogMetric] = [
    available("total_enrolments", "Total enrolments", "Students and load", "student_total_enrolments", "Student", "Department student Section 2 provider table."),
    available("total_student_load", "Total student load (EFTSL)", "Students and load", "student_total_load_eftsl", "Student", "Department student Section 4 provider table."),
    unavailable("undergraduate_load", "Undergraduate load (EFTSL)", "Students and load", "missing", "Requires level-of-course student load parsing."),
    unavailable("postgraduate_load", "Postgraduate load (EFTSL)", "Students and load", "missing", "Requires level-of-course student load parsing."),
    unavailable("pg_coursework_load", "PG coursework load (EFTSL)", "Students and load", "missing", "Requires level-of-course student load parsing."),
    unavailable("pg_research_load", "PG research load (EFTSL)", "Students and load", "missing", "Requires level-of-course student load parsing."),
    unavailable("csp_load", "Commonwealth-supported load (EFTSL)", "Students and load", "missing", "Requires liability-status student load parsing."),
    unavailable("women_share_enrolments", "Women share of enrolments %", "Students and load", "missing", "Requires gender student enrolment parsing and calculation."),
    unavailable("part_time_share", "Part-time share of students (headcount) %", "Students and load", "missing", "Requires attendance-mode enrolment parsing and calculation."),
    unavailable("international_share_load", "International share of student load %", "Students and load", "missing", "Requires overseas/domestic student load parsing and calculation."),
    unavailable("overseas_student_load", "Overseas student load (EFTSL)", "Students and load", "missing", "Requires overseas student load parsing."),
    unavailable("overseas_commencing_load", "Overseas commencing load (EFTSL)", "Students and load", "missing", "Requires overseas commencing load parsing."),
    unavailable("international_onshore_load", "International load, onshore (EFTSL)", "Students and load", "missing", "Requires overseas residence/location breakdown parsing."),
    unavailable("international_offshore_load", "International load, offshore: campuses + TNE (EFTSL)", "Students and load", "missing", "Requires offshore/TNE load source selection."),
    unavailable("offshore_share_load", "Offshore share of student load %", "Students and load", "missing", "Requires offshore load and total load denominator."),
    unavailable("undergraduate_applicants", "Undergraduate applicants (TAC, domestic)", "Demand", "missing", "Requires applications/offers source ingestion."),
    unavailable("undergraduate_offers", "Undergraduate offers (TAC, domestic)", "Demand", "missing", "Requires applications/offers source ingestion."),
    unavailable("undergraduate_offer_rate", "Undergraduate offer rate %", "Demand", "missing", "Requires applicants and offers calculation."),
    unavailable("attrition_rate", "Attrition rate (domestic commencing bachelor) %", "Student outcomes", "missing", "Requires attrition/success/retention student outcome tables."),
    unavailable("retention_rate", "Retention rate %", "Student outcomes", "missing", "Requires attrition/success/retention student outcome tables."),
    unavailable("four_year_completion_rate", "Four-year completion rate %", "Student outcomes", "missing", "Requires completion-rate cohort tables."),
    unavailable("six_year_completion_rate", "Six-year completion rate %", "Student outcomes", "missing", "Requires completion-rate cohort tables."),
    unavailable("nine_year_completion_rate", "Nine-year completion rate %", "Student outcomes", "missing", "Requires completion-rate cohort tables."),
    unavailable("first_year_persister_completion", "Completion among first-year persisters %", "Student outcomes", "missing", "Requires completion-rate cohort tables."),
    unavailable("low_ses_share", "Low-SES share of domestic commencers %", "Equity", "missing", "Requires equity performance data parsing."),
    unavailable("first_nations_share", "First Nations share of domestic commencers %", "Equity", "missing", "Requires First Nations student equity parsing."),
    unavailable("regional_remote_share", "Regional + remote share of domestic commencers %", "Equity", "missing", "Requires regional/remoteness equity parsing."),
    unavailable("cald_nesb_share", "CALD (NESB) share of domestic commencers %", "Equity", "missing", "Requires language/background equity parsing."),
    unavailable("disability_share", "Disability share of domestic commencers %", "Equity", "missing", "Requires disability equity parsing."),
    available("total_revenue", "Total revenue (continuing operations) $", "Finance and funding", "finance_total_revenues_from_continuing_operations_including_deferred_superannuation", "Total Institution", "Department provider finance tables."),
    available("total_expenses", "Total expenses (continuing operations) $", "Finance and funding", "finance_total_expenses_from_continuing_operations_including_deferred_superannuation", "Total Institution", "Department provider finance tables."),
    available("operating_margin", "Operating margin %", "Finance and funding", "calc_operating_margin", "Calculated", "Calculated from operating result and total revenue."),
    available("net_operating_result", "Net operating result $", "Finance and funding", "finance_operating_result_from_continuing_operations", "Total Institution", "Department provider finance tables."),
    unavailable("surplus_before_da_finance_costs", "Surplus before D&A and finance costs $", "Finance and funding", "calculated_needed", "Requires calculated metric from operating result, depreciation/amortisation, and finance costs."),
    unavailable("surplus_before_da_finance_costs_pct", "Surplus before D&A and finance costs %", "Finance and funding", "calculated_needed", "Requires surplus before D&A and finance costs divided by revenue."),
    available("cgs_other_grants", "Commonwealth Grants Scheme + other grants $", "Finance and funding", "finance_commonwealth_grants_scheme_and_other_grants", "Total Institution", "Department provider finance tables."),
    available("hecs_help_revenue", "HECS-HELP revenue (Govt + upfront) $", "Finance and funding", "finance_hecs_help_australian_government_payments_total", "Total Institution", "Department provider finance tables."),
    available("overseas_fee_income", "Overseas student fee income $", "Finance and funding", "finance_fee_paying_overseas_students", "Total Institution", "Department provider finance tables."),
    unavailable("international_fee_share", "International fee share of revenue %", "Finance and funding", "calculated_needed", "Requires overseas student fee income divided by total revenue."),
    available("australian_government_assistance", "Australian Government assistance $", "Revenue lines", "finance_australian_government_financial_assistance", "Total Institution", "Department provider finance tables."),
    unavailable("government_assistance_real_2024", "Government assistance (real 2024 $) $", "Revenue lines", "missing", "Requires CPI deflator or real-dollar source."),
    available("state_local_government_assistance", "State and local government assistance $", "Revenue lines", "finance_state_and_local_government_financial_assistance", "Total Institution", "Department provider finance tables."),
    available("fees_charges_revenue", "Fees and charges revenue $", "Revenue lines", "finance_fees_and_charges", "Total Institution", "Department provider finance tables."),
    available("investment_income", "Investment income $", "Revenue lines", "finance_investment_income", "Total Institution", "Department provider finance tables."),
    available("consultancy_contracts_revenue", "Consultancy and contracts revenue $", "Revenue lines", "finance_consultancy_and_contracts", "Total Institution", "Department provider finance tables."),
    available("other_income", "Other income $", "Revenue lines", "finance_other_income", "Total Institution", "Department provider finance tables."),
    available("employee_benefits_on_costs", "Employee benefits and on-costs $", "Expense lines", "finance_employee_benefits_and_on_costs", "Total Institution", "Department provider finance tables."),
    available("depreciation_amortisation", "Depreciation and amortisation $", "Expense lines", "finance_depreciation_and_amortisation", "Total Institution", "Department provider finance tables."),
    available("repairs_maintenance", "Repairs and maintenance $", "Expense lines", "finance_repairs_and_maintenance", "Total Institution", "Department provider finance tables."),
    available("finance_costs", "Finance costs $", "Expense lines", "finance_finance_costs", "Total Institution", "Department provider finance tables."),
    available("other_expenses", "Other expenses $", "Expense lines", "finance_other_expenses", "Total Institution", "Department provider finance tables."),
    unavailable("total_salary_expenditure", "Total salary expenditure $", "Salaries", "calculated_needed", "Requires academic plus non-academic salaries calculation."),
    available("academic_salaries", "Academic salaries $", "Salaries", "finance_academic_salaries", "Total Institution", "Department provider finance tables."),
    available("non_academic_salaries", "Non-academic salaries $", "Salaries", "finance_non_academic_salaries", "Total Institution", "Department provider finance tables."),
    available("net_assets", "Net assets (equity) $", "Financial sustainability", "finance_net_assets", "Total Institution", "Department provider finance tables."),
    available("total_assets", "Total assets $", "Financial sustainability", "finance_total_assets", "Total Institution", "Department provider finance tables."),
    available("total_liabilities", "Total liabilities $", "Financial sustainability", "finance_total_liabilities", "Total Institution", "Department provider finance tables."),
    available("borrowings", "Borrowings (interest-bearing debt) $", "Financial sustainability", "finance_interest_bearing", "Total Institution", "Department provider finance tables."),
    available("cash_equivalents", "Cash and equivalents $", "Financial sustainability", "finance_cash_and_cash_equivalents", "Total Institution", "Department provider finance tables."),
    available("operating_cash_flow", "Operating cash flow $", "Financial sustainability", "finance_net_cash_inflow_outflow_from_operating_activities", "Total Institution", "Department provider finance tables."),
    unavailable("current_ratio", "Current ratio (liquidity)", "Financial sustainability", "calculated_needed", "Requires current assets divided by current liabilities."),
    unavailable("liabilities_share_assets", "Liabilities as a share of assets %", "Financial sustainability", "calculated_needed", "Requires total liabilities divided by total assets."),
    available("herdc_research_income", "HERDC research income (Cat 1-4) $", "Research", "herdc_research_income_total", "HERDC", "HERDC research income time series."),
    unavailable("research_income_per_academic_fte", "Research income per academic FTE $", "Research", "missing", "Requires academic FTE staff denominator."),
    unavailable("competitive_research_grants", "Competitive research grants (ARC, NHMRC, MRFF)", "Research", "missing", "Requires competitive grant source beyond current HERDC extract."),
    unavailable("arc_grants", "ARC competitive grant funding", "Research", "missing", "Requires ARC grant source or grant category mapping."),
    unavailable("nhmrc_grants", "NHMRC grant funding", "Research", "missing", "Requires NHMRC grant source."),
    unavailable("mrff_grants", "MRFF grant funding", "Research", "missing", "Requires MRFF grant source."),
    unavailable("research_block_grants", "Research block grants $", "Research", "missing", "Requires research block grant allocation source."),
    unavailable("herd_research_expenditure", "HERD research expenditure", "Research", "missing", "Requires HERD expenditure source."),
    unavailable("research_degree_completions", "Research-degree completions (PhD and research masters)", "Research", "missing", "Requires research-degree completions parsing."),
    unavailable("nosc", "Indicative overseas commencement allocation (NOSC)", "International and workforce alignment", "missing", "Requires NOSC allocation source."),
    unavailable("faster_than_market_fields", "Graduates in faster-than-market fields %", "International and workforce alignment", "missing", "Requires field-of-education completions and labour-market mapping."),
    unavailable("shortage_exposure", "Shortage exposure of domestic completions mix %", "International and workforce alignment", "missing", "Requires domestic completions field mix and shortage mapping."),
    available("qilt_overall_experience", "Overall educational experience positive rating", "Student experience", "qilt_overall_educational_experience_positive_rating", "QILT undergraduate", "QILT SES provider-level tables."),
    available("qilt_skills_development", "Skills development positive rating", "Student experience", "qilt_skills_development_positive_rating", "QILT undergraduate", "QILT SES provider-level tables."),
    available("qilt_teaching_quality", "Teaching quality and engagement positive rating", "Student experience", "qilt_teaching_quality_engagement_positive_rating", "QILT undergraduate", "QILT SES provider-level tables."),
    available("qilt_peer_engagement", "Peer engagement positive rating", "Student experience", "qilt_peer_engagement_positive_rating", "QILT undergraduate", "QILT SES provider-level tables."),
    available("qilt_learning_resources", "Learning resources positive rating", "Student experience", "qilt_learning_resources_positive_rating", "QILT undergraduate", "QILT SES provider-level tables."),
    available("qilt_student_support", "Student support and services positive rating", "Student experience", "qilt_student_support_services_positive_rating", "QILT undergraduate", "QILT SES provider-level tables."),
]
