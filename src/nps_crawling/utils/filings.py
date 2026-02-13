class Filing:

    def __init__(self,
                 filename,
                 index,
                 ciks,
                 period_ending,
                 file_num,
                 display_names,
                 xsl,
                 sequence,
                 root_forms,
                 file_date,
                 biz_states,
                 sics,
                 form,
                 adsh,
                 firm_number,
                 biz_location,
                 file_type,
                 fire_descrption,
                 inc_states
    ):
        self.filename = filename
        self.index = index
        self.ciks = ciks
        self.period_ending = period_ending
        self.file_num = file_num
        self.display_names = display_names
        self.xsl = xsl
        self.sequence = sequence
        self.root_forms = root_forms
        self.file_date = file_date
        self.biz_states = biz_states
        self.sics = sics
        self.form = form
        self.adsh = adsh
        self.firm_number = firm_number
        self.biz_location = biz_location
        self.file_type = file_type
        self.fire_descrption = fire_descrption
        self.inc_state = inc_states

    def get_url(self):
        return f'https://sec.gov/Archives/edgar/data/{self.ciks}/{self.adsh}/{self.filename}'