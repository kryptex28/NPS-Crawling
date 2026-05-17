"""
Dimensions varied here:
- length: short keyword string vs. one sentence vs. paragraph
- register: dictionary definition vs. financial-disclosure prose vs. bag-of-keywords
- topic focus: pure NPS vs. NPS + adjacent customer-experience metrics
                vs. NPS in management/KPI/disclosure context (proxy-statement-like)

"""

REFERENCE_TEXTS: dict[str, str] = {
    # v1: current production default — paragraph, mixes definition + disclosure register.
    "v1_current": (
        "Net Promoter Score (NPS) is a key performance indicator (KPI) and customer "
        "loyalty metric used by management to measure customer satisfaction, brand "
        "health, and the likelihood of customers to recommend a company's products "
        "or services. Companies track NPS scores to predict customer retention and "
        "churn, report NPS improvements to investors as an indicator of future organic "
        "growth, and benchmark NPS against competitors to evaluate market position."
    ),

    # v2: terse one-sentence definition.
    "v2_short_definition": (
        "Net Promoter Score (NPS) is a customer loyalty metric measuring how likely "
        "customers are to recommend a company's products or services."
    ),

    # v3: bag of NPS-adjacent keywords, no grammar — tests whether prose structure helps.
    "v3_keywords": (
        "net promoter score NPS customer loyalty customer satisfaction "
        "recommend promoters detractors customer experience"
    ),

    # v4: management / KPI / disclosure register — most filings mention NPS in
    # proxy statements as a performance metric tied to executive compensation.
    "v4_kpi_management": (
        "Net Promoter Score is used by management as a key performance indicator "
        "tied to executive compensation and short-term incentive plans. The Company "
        "tracks NPS as a non-financial performance measure, sets annual NPS targets, "
        "and reports NPS results to the Board to evaluate progress on customer "
        "experience strategy."
    ),

    # v5: NPS + adjacent customer-experience metrics — broader anchor, may help
    # recall but risks pulling in CSAT-only contexts. Useful ablation.
    "v5_nps_plus_adjacent": (
        "Customer experience metrics including Net Promoter Score (NPS), customer "
        "satisfaction (CSAT), customer effort score, customer retention, churn rate, "
        "and brand loyalty are tracked to measure the quality of customer relationships "
        "and predict future revenue growth."
    ),

    # v6: pure dictionary-style definition, no business framing.
    "v6_definition_minimal": (
        "Net Promoter Score is a metric calculated from a survey question asking "
        "customers how likely they are, on a scale from 0 to 10, to recommend a "
        "company to a friend or colleague."
    ),
}
