"""
    Smoke test for SEC query function.

    This test case shall cover the mirrored functionality of the SEC.gov
    website. 
"""

from nps_crawling.utils.sec_params import SecParams
from nps_crawling.utils.sec_query import SecQuery
from nps_crawling.utils.filings import Filing, CompanyTicker, FilingsCategoryCollectionCoarse, FilingCategoryCollection

EXPECTED_RESULTS = 6
EXPECTED_RESULTS_COUNT = 6

EXPECTED_RESULTS_2 = 818
EXPECTED_RESULTS_COUNT_2 = 818

params1 = SecParams (
    query_base = "https://efts.sec.gov/LATEST/search-index?",
    keyword = "net promoter",
    from_date = "2001-01-01",
    to_date = "2026-03-26",
    date_range = "all",
    individual_search = CompanyTicker(
        cik = "0001341439",
        ticker = "ORCL, ORCL-PD",
        title = "ORACLE CORP"
    ),
    filing_category = FilingsCategoryCollectionCoarse.ALL_ANUAL_QUARTERLY_AND_CURRENT_REPORTS,
    filing_categories = FilingCategoryCollection.filing_categories[FilingsCategoryCollectionCoarse.ALL_ANUAL_QUARTERLY_AND_CURRENT_REPORTS]
)
params2 = SecParams (
    query_base = "https://efts.sec.gov/LATEST/search-index?",
    keyword = "net promoter",
    from_date = "2026-02-24",
    to_date = "2026-03-26",
    date_range = "30d",
)
def run():
    sq = SecQuery (
        sec_params = params1
    )
    sq.fetch_filings()

    filings = sq.keyword_filings
    total = sq.results

    print(f"Total results reported by EDGAR : {total}")
    print(f"Filings fetched : {len(filings)}")
    
    assert total == EXPECTED_RESULTS, (
        f"Expected {EXPECTED_RESULTS} results, got {total}"
    )
    assert len(filings) == EXPECTED_RESULTS_COUNT, (
        f"Expected {EXPECTED_RESULTS_COUNT} results, got {len(filings)}"
    )

    sq2 = SecQuery (
        sec_params = params2
    )

    sq2.fetch_filings()

    filings = sq2.keyword_filings
    total = sq2.results

    print(f"Total results reported by EDGAR : {total}")
    print(f"Filings fetched : {len(filings)}")
    
    assert total == EXPECTED_RESULTS_2, (
        f"Expected {EXPECTED_RESULTS_2} results, got {total}"
    )
    assert len(filings) == EXPECTED_RESULTS_COUNT_2, (
        f"Expected {EXPECTED_RESULTS_COUNT_2} results, got {len(filings)}"
    )

    print("\nAll smoke checks passed.")

if __name__ == "__main__":
    run()