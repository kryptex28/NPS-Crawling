import re

from config.config import Config

class NpsMentionFilterPipeline(Config):
  
    def __init__(self):

        # normalize phrases to lowercase for case-insensitive matching
        self.filter_words= [p.lower() for p in Config.LIST_OF_PHRASES_TO_FILTER_FILINGS_FOR]

        # define sentence splitting logic here, using simple logic here:
        # split on ., !, ? followed by whitespace
        # since performance is high
        self._sentence_splitter = re.compile(r'(?<=[.!?])\s+')

        self.sentences_before = Config.AMOUNT_SENTENCES_INCLUDED_BEFORE
        self.sentences_after = Config.AMOUNT_SENTENCES_INCLUDED_AFTER

    def filtering_workflow(self, dict_batch):
        """
        input: expects a list of dicts with following keys:
        "company", "ticker", "cik", "filing_url", "keywords_found", "html_text"

        output: list of dicts. 1 dict represents 1 hit of matching phrases. contains keys: 
        "company", "ticker", "cik", "filing_url", "keywords_found", "html_text",
        "matched_phrase", "context", "hit_sentence_index", "context_start_index", "context_end_index"
        """

        all_hits = []

        for single_dict in dict_batch:
            hits = self._extract_context_from_single_dict(single_dict)
            if hits:
                all_hits.extend(hits)

        return all_hits
    
    def _extract_context_from_single_dict(self, single_dict):
        
        text = single_dict.get("html_text")

        sentences = self._split_into_sentences(text)
        
        n = len(sentences)

        hits = []

        for idx, single_sentence in enumerate(sentences):
            matched_phrases = self._finding_matching_phrases(single_sentence)
            if not matched_phrases:
                continue
            
            start, end, context = self._create_context_window(sentences, n, idx)
            
            for phrase in matched_phrases:
                hit = self._build_hit_dict(single_dict, phrase, context, idx, start,end)
                hits.append(hit)

        return hits
    
    def _split_into_sentences(self, text):
        
        sentences = self._sentence_splitter.split(text)
        
        # strip leading or trailing whitespaces here
        return [s.strip() for s in sentences if s.strip()]

    def _finding_matching_phrases(self, single_sentence):
        """
        input: single sentence
        output: single sentence if this sentence includes a phrase as defined in 
        Config var LIST_OF_PHRASES_TO_FILTER_FILINGS_FOR
        """

        sentence_lower = single_sentence.lower()
        matches = []
        for phrase in self.filter_words:
            if phrase in sentence_lower:
                matches.append(phrase)

        return matches
    
    def _create_context_window(self, sentences, n, idx):

        start = max(0, idx - self.sentences_before)
        end = min(n, idx + self.sentences_after + 1)  
        context = " ".join(sentences[start:end]).strip()

        return start, end, context
    
    def _build_hit_dict(self, single_dict, phrase, context, idx, start, end):
        
        return {
            "company": single_dict.get("company"),
            "ticker": single_dict.get("ticker"),
            "cik": single_dict.get("cik"),
            "filing_url": single_dict.get("filing_url"),
            "keywords_found": single_dict.get("keywords_found"),

            "matched_phrase": phrase,
            "context": context,
            "hit_sentence_index": idx,
            "context_start_index": start,
            "context_end_index": end,
        }