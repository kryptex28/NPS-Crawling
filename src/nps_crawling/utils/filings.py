from enum import Enum

class Filing:
    """Class abstraction for Filing elements."""

    def __init__(self,
                 _id: str,
                 _index: str,
                 ciks: list[str],
                 period_ending: str,
                 file_num: list[str],
                 display_names: list[str],
                 xsl: str,
                 sequence: str,
                 root_forms: list[str],
                 file_date: str,
                 biz_states: list[str],
                 sics: list[str],
                 form: str,
                 adsh: str,
                 film_num: list[str],
                 biz_locations: list[str],
                 file_type: str,
                 file_description: str,
                 inc_states: list[str],
                 file_path_name: str):
        """Initialize the filing."""
        self._id: str = _id
        self._index: str = _index

        self.ciks: list[str] = ciks
        self.period_ending: str = period_ending
        self.file_num: list[str] = file_num
        self.display_names: list[str] = display_names
        self.xsl: str = xsl
        self.sequence: str = sequence
        self.root_forms: list[str] = root_forms
        self.file_date: str = file_date
        self.biz_states: list[str] = biz_states
        self.sics: list[str] = sics
        self.form: str = form
        self.adsh: str = adsh
        self.film_num: list[str] = film_num
        self.biz_locations: list[str] = biz_locations
        self.file_type: str = file_type
        self.file_description: str = file_description
        self.inc_states: list[str] = inc_states
        self.file_path_name: str = file_path_name

        # Store file type of the document (htm, pdf, ...)
        self.file_container_type: str = self.file_path_name.split('.')[1]

    def get_url(self) -> list:
        """Returns a query list of the filing with all CIKS."""
        urls: list = []
        for cik in self.ciks:
            urls.append(f'https://sec.gov/Archives/edgar/data/{cik}/{self.adsh.replace('-', '')}/{self.file_path_name}')

        return urls

class FilingDateRange(Enum):
    """Enum class to abstract the filing date range."""
    CUSTOM = 'custom'
    ALL = 'all'
    LAST_10_YEARS = '10y'
    LAST_5_YEARS = '5y'
    LAST_1_YEARS = '1y'
    LAST_30_DAYS = '30d'

class FilingsCategoryCollectionCoarse(Enum):
    """Enum class to abstract filing category collection."""
    CUSTOM = 'custom'
    ALL_ANUAL_QUARTERLY_AND_CURRENT_REPORTS = 'form-cat1'
    INSIDER_EQUITY_AWARDS_TRANSACTIONS_AND_OWNERSHIP = 'form-cat2'
    BENEFICIAL_OWNERSHIP_REPORTS = 'form-cat3'
    EXEMPT_OFFERINGS = 'form-cat4'
    REGISTRATION_STATEMENTS_AND_PROSPECTUSES = 'form-cat5'
    FILING_REVIEW_CORRESPONDENCE = 'form-cat6'
    SEC_ORDERS_AND_NOTICES = 'form-cat7'
    PROXY_MATERIALS = 'form-cat8'
    TENDER_OFFERS_AND_GOING_PRIVATE_TRANSACTIONS = 'form-cat9'
    TRUST_INDENTURE_FILINGS = 'form-cat10'

class FilingCategoryCollection:
    """Collection of parameter values for categories."""
    filing_categories: dict = {
        FilingsCategoryCollectionCoarse.ALL_ANUAL_QUARTERLY_AND_CURRENT_REPORTS:
        [
            '10-K', '10-KT', '10-Q', '10-QT', '11-K', '11-KT',
            '13F-HR', '13F-NT', '15-12B', '15-12G', '15-15D', '15F-12B',
            '15F-12G', '15F-15D', '18-K', '20-F', '24F-2NT', '25',
            '25-NSE', '40-17F2', '40-17G', '40-F', '6-K', '8-K',
            '8-K12G3', '8-K15D5', 'ABS-15G', 'ABS-EE', 'ANNLRPT', 'DSTRBRPT',
            'IRANNOTICE', 'N-30B-2', 'N-30D', 'N-CEN', 'N-CSR', 'N-CSRS',
            'N-MFP', 'N-MFP1', 'N-MFP2', 'N-PX', 'N-Q', 'NPORT-EX',
            'NSAR-A', 'NSAR-B', 'NSAR-U', 'NT 10-D', 'NT 10-K', 'NT 10-Q',
            'NT 11-K', 'NT 20-F', 'QRTLYRPT', 'SD', 'SP 15D2'
        ],

        FilingsCategoryCollectionCoarse.INSIDER_EQUITY_AWARDS_TRANSACTIONS_AND_OWNERSHIP:
        [
            '3', '4', '5'
        ],

        FilingsCategoryCollectionCoarse.BENEFICIAL_OWNERSHIP_REPORTS:
        [
            'SC 13D', 'SC 13G', 'SCHEDULE 13D', 'SCHEDULE 13G'
        ],

        FilingsCategoryCollectionCoarse.EXEMPT_OFFERINGS:
        [
            '1-A', '1-A POS', '1-A-W', '253G1', '253G2', '253G3',
            '253G4', 'C', 'D', 'DOS'
        ],

        FilingsCategoryCollectionCoarse.REGISTRATION_STATEMENTS_AND_PROSPECTUSES:
        [
            '10-12B', '10-12G', '18-12B', '20FR12B', '20FR12G', '40-24B2',
            '40FR12B', '40FR12G', '424A', '424B1', '424B2', '424B3',
            '424B4', '424B5', '424B7', '424B8', '424H', '425',
            '485APOS', '485BPOS', '485BXT', '487', '497', '497J',
            '497K', '8-A12B', '8-A12G', 'AW', 'AW WD', 'DEL AM',
            'DRS', 'F-1', 'F-10', 'F-10EF', 'F-10POS', 'F-3',
            'F-3ASR', 'F-3D', 'F-3DPOS', 'F-3MEF', 'F-4', 'F-4 POS',
            'F-4MEF', 'F-6', 'F-6 POS', 'F-6EF', 'F-7', 'F-7 POS',
            'F-8', 'F-8 POS', 'F-80', 'F-80POS', 'F-9', 'F-9 POS',
            'F-N', 'F-X', 'FWP', 'N-2', 'POS AM', 'POS EX',
            'POS462B', 'POS462C', 'POSASR', 'RW', 'RW WD', 'S-1',
            'S-11', 'S-11MEF', 'S-1MEF', 'S-20', 'S-3', 'S-3ASR',
            'S-3D', 'S-3DPOS', 'S-3MEF', 'S-4', 'S-4 POS', 'S-4EF',
            'S-4MEF', 'S-6', 'S-8', 'S-8 POS', 'S-B', 'S-BMEF',
            'SF-1', 'SF-3', 'SUPPL', 'UNDER',
        ],

        FilingsCategoryCollectionCoarse.FILING_REVIEW_CORRESPONDENCE:
        [
            'CORRESP', 'DOSLTR', 'DRSLTR', 'UPLOAD ',
        ],

        FilingsCategoryCollectionCoarse.SEC_ORDERS_AND_NOTICES:
        [
            '40-APP', 'CT ORDER', 'EFFECT', 'QUALIF', 'REVOKED',
        ],

        FilingsCategoryCollectionCoarse.PROXY_MATERIALS:
        [
            'ARS', 'DEF 14A', 'DEF 14C', 'DEFA14A', 'DEFA14C', 'DEFC14A',
            'DEFC14C', 'DEFM14A', 'DEFM14C', 'DEFN14A', 'DEFR14A', 'DEFR14C',
            'DFAN14A', 'DFRN14A', 'PRE 14A', 'PRE 14C', 'PREC14A', 'PREC14C',
            'PREM14A', 'PREM14C', 'PREN14A', 'PRER14A', 'PRER14C', 'PRRN14A',
            'PX14A6G', 'PX14A6N', 'SC 14N ',
        ],

        FilingsCategoryCollectionCoarse.TENDER_OFFERS_AND_GOING_PRIVATE_TRANSACTIONS:
        [
            'CB', 'SC 13E1', 'SC 13E3', 'SC 14D9', 'SC 14F1', 'SC TO-C',
            'SC TO-I', 'SC TO-T', 'SC13E4F', 'SC14D1F', 'SC14D9C', 'SC14D9F ',
        ],

        FilingsCategoryCollectionCoarse.TRUST_INDENTURE_FILINGS:
        [
            '305B2', 'T-3 ',
        ]
    }

class CompanyTicker:
    """Class abstraction for ticker/cik mapping."""
    def __init__(self,
                 cik: str,
                 ticker: list[str],
                 title: str):
        self.cik = cik
        self.ticker = ticker
        self.title = title

    def create_entity_name(self) -> str:
        """Creates query string for request."""
        return f'{self.title} ({', '.join(self.ticker)}) (CIK {self.cik})'