"""Filings and type abstraction module with utility functions."""
from enum import Enum
from typing import Optional


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
        self.id: str = _id
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
            urls.append(f'https://sec.gov/Archives/edgar/data/{cik}/{self.adsh.replace("-", "")}/{self.file_path_name}')

        return urls

    def to_json(self) -> dict:
        data: dict = {
            'ciks': self.ciks,
            'filing_id': self.id,
            'url': self.get_url()[0],
            'display_names': self.display_names,
            'form': self.form,
            'status': 'Crawled'
        }
        return data


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
    ALL = ''

    @classmethod
    def from_string(cls, type_str: str) -> Optional["FilingsCategoryCollectionCoarse"]:
        """Convert a string to an enum."""
        try:
            return cls[type_str]
        except KeyError:
            return cls.ALL

    def to_string(self) -> str:
        """Convert an enum to a string."""
        return self.name


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
            'NT 11-K', 'NT 20-F', 'QRTLYRPT', 'SD', 'SP 15D2',
        ],

        FilingsCategoryCollectionCoarse.INSIDER_EQUITY_AWARDS_TRANSACTIONS_AND_OWNERSHIP:
        [
            '3', '4', '5',
        ],

        FilingsCategoryCollectionCoarse.BENEFICIAL_OWNERSHIP_REPORTS:
        [
            'SC 13D', 'SC 13G', 'SCHEDULE 13D', 'SCHEDULE 13G',
        ],

        FilingsCategoryCollectionCoarse.EXEMPT_OFFERINGS:
        [
            '1-A', '1-A POS', '1-A-W', '253G1', '253G2', '253G3',
            '253G4', 'C', 'D', 'DOS',
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
        ],

        FilingsCategoryCollectionCoarse.ALL:
        [

        ],
    }


class CompanyTicker:
    """Class abstraction for ticker/cik mapping."""
    def __init__(self,
                 cik: str,
                 ticker: list[str],
                 title: str):
        """Initializes CompanyTicker class."""
        self.cik = cik
        self.ticker = ticker
        self.title = title

    def create_entity_name(self) -> str:
        """Creates query string for request."""
        return f'{self.title} ({", ".join(self.ticker)}) (CIK {self.cik})'

class ExecutiveOfficeIn(Enum):
    ALABAMA = 'AL',
    ALASKA = 'AK',
    ARIZONA = 'AZ',
    ARKANSAS = 'AR',
    CALIFORNIA = 'CA',
    COLORADO = 'CO',
    CONNECTICUT = 'CT',
    DELAWARE = 'DE',
    DISTRICT_OF_COLUMBIA = 'DC',
    FLORIDA = 'FL',
    GEORGIA = 'GA',
    HAWAII = 'HI',
    IDAHO = 'ID',
    ILLINOIS = 'IL',
    INDIANA = 'IN',
    IOWA = 'IA',
    KANSAS = 'KS',
    KENTUCKY = 'KY',
    LOUISIANA = 'LA',
    MAINE = 'ME',
    MARYLAND = 'MD',
    MASSACHUSETTS = 'MA',
    MICHIGAN = 'MI',
    MINNESOTA = 'MN',
    MISSISSIPPI = 'MS',
    MISSOURI = 'MO',
    MONTANA = 'MT',
    NEBRASKA = 'NE',
    NEVADA = 'NV',
    NEW_HAMPSHIRE = 'NH',
    NEW_JERSEY = 'NJ',
    NEW_MEXICO = 'NM',
    NEW_YORK = 'NY',
    NORTH_CAROLINA = 'NC',
    NORTH_DAKOTA = 'ND',
    OHIO = 'OH',
    OKLAHOMA = 'OK',
    OREGON = 'OR',
    PENNSYLVANIA = 'PA',
    RHODE_ISLAND = 'RI',
    SOUTH_CAROLINA = 'SC',
    SOUTH_DAKOTA = 'SD',
    TENNESSEE = 'TN',
    TEXAS = 'TX',
    UNITED_STATES = 'X1',
    UTAH = 'UT',
    VERMONT = 'VT',
    VIRGINIA = 'VA',
    WASHINGTON = 'WA',
    WEST_VIRGINIA = 'WV',
    WISCONSIN = 'WI',
    WYOMING = 'WY',
    ALBERTA_CANADA = 'A0',
    BRITISH_COLUMBIA_CANADA = 'A1',
    CANADA_FEDERAL_LEVEL = 'Z4',
    MANITOBA_CANADA = 'A2',
    NEW_BRUNSWICK_CANADA = 'A3',
    NEWFOUNDLAND_CANADA = 'A4',
    NOVA_SCOTIA_CANADA = 'A5',
    ONTARIO_CANADA = 'A6',
    PRINCE_EDWARD_ISLAND_CANADA = 'A7',
    QUEBEC_CANADA = 'A8',
    SASKATCHEWAN_CANADA = 'A9',
    YUKON_CANADA = 'B0',
    AFGHANISTAN = 'B2',
    ALAND_ISLANDS = 'Y6',
    ALBANIA = 'B3',
    ALGERIA = 'B4',
    AMERICAN_SAMOA = 'B5',
    ANDORRA = 'B6',
    ANGOLA = 'B7',
    ANGUILLA = '1A',
    ANTARCTICA = 'B8',
    ANTIGUA_AND_BARBUDA = 'B9',
    ARGENTINA = 'C1',
    ARMENIA = '1B',
    ARUBA = '1C',
    AUSTRALIA = 'C3',
    AUSTRIA = 'C4',
    AZERBAIJAN = '1D',
    BAHAMAS = 'C5',
    BAHRAIN = 'C6',
    BANGLADESH = 'C7',
    BARBADOS = 'C8',
    BELARUS = '1F',
    BELGIUM = 'C9',
    BELIZE = 'D1',
    BENIN = 'G6',
    BERMUDA = 'D0',
    BHUTAN = 'D2',
    BOLIVIA = 'D3',
    BOSNIA_AND_HERZEGOVINA = '1E',
    BOTSWANA = 'B1',
    BOUVET_ISLAND = 'D4',
    BRAZIL = 'D5',
    BRITISH_INDIAN_OCEAN_TERRITORY = 'D6',
    BRUNEI_DARUSSALAM = 'D9',
    BULGARIA = 'E0',
    BURKINA_FASO = 'X2',
    BURUNDI = 'E2',
    CAMBODIA = 'E3',
    CAMEROON = 'E4',
    CAPE_VERDE = 'E8',
    CAYMAN_ISLANDS = 'E9',
    CENTRAL_AFRICAN_REPUBLIC = 'F0',
    CHAD = 'F2',
    CHILE = 'F3',
    CHINA = 'F4',
    CHRISTMAS_ISLAND = 'F6',
    COCOS_KEELING_ISLANDS = 'F7',
    COLOMBIA = 'F8',
    COMOROS = 'F9',
    CONGO = 'G0',
    CONGO_THE_DEMOCRATIC_REPUBLIC_OF_THE = 'Y3',
    COOK_ISLANDS = 'G1',
    COSTA_RICA = 'G2',
    COTE_D_IVOIRE = 'L7',
    CROATIA = '1M',
    CUBA = 'G3',
    CYPRUS = 'G4',
    CZECH_REPUBLIC = '2N',
    DENMARK = 'G7',
    DJIBOUTI = '1G',
    DOMINICA = 'G9',
    DOMINICAN_REPUBLIC = 'G8',
    ECUADOR = 'H1',
    EGYPT = 'H2',
    EL_SALVADOR = 'H3',
    EQUATORIAL_GUINEA = 'H4',
    ERITREA = '1J',
    ESTONIA = '1H',
    ETHIOPIA = 'H5',
    FALKLAND_ISLANDS_MALVINAS = 'H7',
    FAROE_ISLANDS = 'H6',
    FIJI = 'H8',
    FINLAND = 'H9',
    FRANCE = 'I0',
    FRENCH_GUIANA = 'I3',
    FRENCH_POLYNESIA = 'I4',
    FRENCH_SOUTHERN_TERRITORIES = '2C',
    GABON = 'I5',
    GAMBIA = 'I6',
    GEORGIA_COUNTRY = '2Q',
    GERMANY = '2M',
    GHANA = 'J0',
    GIBRALTAR = 'J1',
    GREECE = 'J3',
    GREENLAND = 'J4',
    GRENADA = 'J5',
    GUADELOUPE = 'J6',
    GUAM = 'GU',
    GUATEMALA = 'J8',
    GUERNSEY = 'Y7',
    GUINEA = 'J9',
    GUINEA_BISSAU = 'S0',
    GUYANA = 'K0',
    HAITI = 'K1',
    HEARD_ISLAND_AND_MCDONALD_ISLANDS = 'K4',
    HOLY_SEE_VATICAN_CITY_STATE = 'X4',
    HONDURAS = 'K2',
    HONG_KONG = 'K3',
    HUNGARY = 'K5',
    ICELAND = 'K6',
    INDIA = 'K7',
    INDONESIA = 'K8',
    IRAN_ISLAMIC_REPUBLIC_OF = 'K9',
    IRAQ = 'L0',
    IRELAND = 'L2',
    ISLE_OF_MAN = 'Y8',
    ISRAEL = 'L3',
    ITALY = 'L6',
    JAMAICA = 'L8',
    JAPAN = 'M0',
    JERSEY = 'Y9',
    JORDAN = 'M2',
    KAZAKHSTAN = '1P',
    KENYA = 'M3',
    KIRIBATI = 'J2',
    KOREA_DEMOCRATIC_PEOPLES_REPUBLIC_OF = 'M4',
    KOREA_REPUBLIC_OF = 'M5',
    KUWAIT = 'M6',
    KYRGYZSTAN = '1N',
    LAO_PEOPLES_DEMOCRATIC_REPUBLIC = 'M7',
    LATVIA = '1R',
    LEBANON = 'M8',
    LESOTHO = 'M9',
    LIBERIA = 'N0',
    LIBYAN_ARAB_JAMAHIRIYA = 'N1',
    LIECHTENSTEIN = 'N2',
    LITHUANIA = '1Q',
    LUXEMBOURG = 'N4',
    MACAU = 'N5',
    MACEDONIA_THE_FORMER_YUGOSLAV_REPUBLIC_OF = '1U',
    MADAGASCAR = 'N6',
    MALAWI = 'N7',
    MALAYSIA = 'N8',
    MALDIVES = 'N9',
    MALI = 'O0',
    MALTA = 'O1',
    MARSHALL_ISLANDS = '1T',
    MARTINIQUE = 'O2',
    MAURITANIA = 'O3',
    MAURITIUS = 'O4',
    MAYOTTE = '2P',
    MEXICO = 'O5',
    MICRONESIA_FEDERATED_STATES_OF = '1K',
    MOLDOVA_REPUBLIC_OF = '1S',
    MONACO = 'O9',
    MONGOLIA = 'P0',
    MONTENEGRO = 'Z5',
    MONTSERRAT = 'P1',
    MOROCCO = 'P2',
    MOZAMBIQUE = 'P3',
    MYANMAR = 'E1',
    NAMIBIA = 'T6',
    NAURU = 'P5',
    NEPAL = 'P6',
    NETHERLANDS = 'P7',
    NETHERLANDS_ANTILLES = 'P8',
    NEW_CALEDONIA = '1W',
    NEW_ZEALAND = 'Q2',
    NICARAGUA = 'Q3',
    NIGER = 'Q4',
    NIGERIA = 'Q5',
    NIUE = 'Q6',
    NORFOLK_ISLAND = 'Q7',
    NORTHERN_MARIANA_ISLANDS = '1V',
    NORWAY = 'Q8',
    OMAN = 'P4',
    PAKISTAN = 'R0',
    PALAU = '1Y',
    PALESTINIAN_TERRITORY_OCCUPIED = '1X',
    PANAMA = 'R1',
    PAPUA_NEW_GUINEA = 'R2',
    PARAGUAY = 'R4',
    PERU = 'R5',
    PHILIPPINES = 'R6',
    PITCAIRN = 'R8',
    POLAND = 'R9',
    PORTUGAL = 'S1',
    PUERTO_RICO = 'PR',
    QATAR = 'S3',
    REUNION = 'S4',
    ROMANIA = 'S5',
    RUSSIAN_FEDERATION = '1Z',
    RWANDA = 'S6',
    SAINT_BARTHELEMY = 'Z0',
    SAINT_HELENA = 'U8',
    SAINT_KITTS_AND_NEVIS = 'U7',
    SAINT_LUCIA = 'U9',
    SAINT_MARTIN = 'Z1',
    SAINT_PIERRE_AND_MIQUELON = 'V0',
    SAINT_VINCENT_AND_THE_GRENADINES = 'V1',
    SAMOA = 'Y0',
    SAN_MARINO = 'S8',
    SAO_TOME_AND_PRINCIPE = 'S9',
    SAUDI_ARABIA = 'T0',
    SENEGAL = 'T1',
    SERBIA = 'Z2',
    SEYCHELLES = 'T2',
    SIERRA_LEONE = 'T8',
    SINGAPORE = 'U0',
    SLOVAKIA = '2B',
    SLOVENIA = '2A',
    SOLOMON_ISLANDS = 'D7',
    SOMALIA = 'U1',
    SOUTH_AFRICA = 'T3',
    SOUTH_GEORGIA_AND_THE_SOUTH_SANDWICH_ISLANDS = '1L',
    SPAIN = 'U3',
    SRI_LANKA = 'F1',
    SUDAN = 'V2',
    SURINAME = 'V3',
    SVALBARD_AND_JAN_MAYEN = 'L9',
    SWAZILAND = 'V6',
    SWEDEN = 'V7',
    SWITZERLAND = 'V8',
    SYRIAN_ARAB_REPUBLIC = 'V9',
    TAIWAN_PROVINCE_OF_CHINA = 'F5',
    TAJIKISTAN = '2D',
    TANZANIA_UNITED_REPUBLIC_OF = 'W0',
    THAILAND = 'W1',
    TIMOR_LESTE = 'Z3',
    TOGO = 'W2',
    TOKELAU = 'W3',
    TONGA = 'W4',
    TRINIDAD_AND_TOBAGO = 'W5',
    TUNISIA = 'W6',
    TURKEY = 'W8',
    TURKMENISTAN = '2E',
    TURKS_AND_CAICOS_ISLANDS = 'W7',
    TUVALU = '2G',
    UGANDA = 'W9',
    UKRAINE = '2H',
    UNITED_ARAB_EMIRATES = 'C0',
    UNITED_KINGDOM = 'X0',
    UNITED_STATES_MINOR_OUTLYING_ISLANDS = '2J',
    URUGUAY = 'X3',
    UZBEKISTAN = '2K',
    VANUATU = '2L',
    VENEZUELA = 'X5',
    VIET_NAM = 'Q1',
    VIRGIN_ISLANDS_BRITISH = 'D8',
    VIRGIN_ISLANDS_US = 'VI',
    WALLIS_AND_FUTUNA = 'X8',
    WESTERN_SAHARA = 'U5',
    YEMEN = 'T7',
    ZAMBIA = 'Y4',
    ZIMBABWE = 'Y5',
    UNKNOWN = 'XX',