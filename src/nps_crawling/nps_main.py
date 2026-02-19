"""Main module to run the NPS crawling spiders."""
import os

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from nps_crawling.crawler.spiders.better_spider import BetterSpider

os.environ['SCRAPY_SETTINGS_MODULE'] = 'nps_crawling.crawler.settings'

settings = get_project_settings()


def run():
    """Run the NPS crawling spider with specified settings."""
    print("=== Active Scrapy Settings ===")
    for name, value in settings.items():
        print(f"{name}: {value}")
    print("=== End of Settings ===\n")

    # Run spider
    process = CrawlerProcess(settings)

    # ============================================
    # OPTION 1: Crawl ALL companies (SLOW!)
    # ============================================
    # WARNING: This will take DAYS and download GIGABYTES of data
    # Uncomment to use:
    """
    process.crawl(
        SECNpsSpider,
        crawler_name='sec_nps_all_companies',
        form_types=["S-1", "S-1/A", "DEF 14A", "424B4"],
        keywords=[
            "net promoter score",
            "nps score",
            "nps of",
            "customer satisfaction score",
        ],
        context_window=500,
        use_all_companies=True,  # Crawl everything!
        max_companies=100,  # Limit to first 100 companies for testing
        allowed_domains=["sec.gov"],
        output_format='json',
        output_path='./data',
    )
    """

    # ============================================
    # OPTION 2: Crawl specific tickers
    # ============================================
    # This is more practical - specify companies you're interested in
    # process.crawl(
    #     SECNpsSpider,
    #     crawler_name='sec_nps_specific',
    #     form_types=["S-1", "S-1/A", "DEF 14A", "424B4", "10-K"],
    #     keywords=[
    #         "net promoter score",
    #         "nps score",
    #         "nps of",
    #         "customer satisfaction score",
    #         "customer loyalty metric",
    #         "likelihood to recommend",
    #     ],
    #     context_window=500,
    #     ticker_list=[
    #         "crm",      # Salesforce
    #         "snow",     # Snowflake
    #         "hubs",     # HubSpot
    #         "zm",       # Zoom
    #         "now",      # ServiceNow
    #         "team",     # Atlassian
    #         "twlo",     # Twilio
    #         "ddog",     # Datadog
    #         "okta",     # Okta
    #         "zs",       # Zscaler
    #         "docu",     # DocuSign
    #         "wday",     # Workday
    #         "crwd",     # CrowdStrike
    #         "net",      # Cloudflare
    #         "s",        # SentinelOne
    #     ],
    #     allowed_domains=["sec.gov"],
    #     output_format='json',
    #     output_path='./data',
    # )

    process.crawl(
        BetterSpider,
    )

    # ============================================
    # OPTION 3: Crawl specific CIKs (if you already know them)
    # ============================================
    """
    process.crawl(
        SECNpsSpider,
        crawler_name='sec_nps_ciks',
        form_types=["S-1", "S-1/A", "DEF 14A"],
        keywords=["net promoter score", "nps score"],
        context_window=500,
        cik_list=[
            "0001467623",  # Salesforce
            "0001534675",  # HubSpot
            "0001588717",  # Zoom
        ],
        allowed_domains=["sec.gov"],
        output_format='json',
        output_path='./data',
    )
    """

    process.start()
