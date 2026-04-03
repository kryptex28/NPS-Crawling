"""Pipeline to filter NPS mentions and extract context."""

import re

from nps_crawling.config import Config


class NpsMentionFilterPipeline(Config):
    """Pipeline to filter NPS mentions and extract context."""
    def __init__(self):
        """Initialize the NpsMentionFilterPipeline."""
        # normalize phrases to lowercase for case-insensitive matching
        self.filter_words = [p.lower() for p in Config.LIST_OF_PHRASES_TO_FILTER_FILINGS_FOR]

        # define sentence splitting logic here, using simple logic here:
        # split on ., !, ? followed by whitespace
        # since performance is high
        self._sentence_splitter = re.compile(r'(?<=[.!?])\s+')

        self.sentences_before = Config.AMOUNT_SENTENCES_INCLUDED_BEFORE
        self.sentences_after = Config.AMOUNT_SENTENCES_INCLUDED_AFTER

    def filtering_workflow(self, records):
        """Filtering workflow method.

        input: list of dicts, each with "metadata" and "core_text" keys.

        output: same list with a "context" key added to each record.
        "context" is a list of dicts, one per matched phrase hit:
            {
                "matched_phrase": str,
                "context": str,
                "hit_sentence_index": int,
                "context_start_index": int,
                "context_end_index": int,
            }
        Records with no hits get an empty "context" list.

        Also adds "all_context_windows": a single string that merges all
        context windows for the record, removing duplicate sentences from
        overlapping windows.
        """
        for record in records:
            text = record.get("core_text", "")
            record["context"] = self._extract_context_windows(text)
            record["all_context_windows"] = self._build_concatenated_context(
                text, record["context"],
            )
        return records

    def _extract_context_windows(self, text):
        """Extract all context windows from a text string."""
        if not text:
            return []

        sentences = self._split_into_sentences(text)
        n = len(sentences)
        hits = []

        for idx, sentence in enumerate(sentences):
            matched_phrases = self._finding_matching_phrases(sentence)
            if not matched_phrases:
                continue

            start, end, context = self._create_context_window(sentences, n, idx)

            for phrase in matched_phrases:
                hits.append({
                    "matched_phrase": phrase,
                    "context": context,
                    "hit_sentence_index": idx,
                    "context_start_index": start,
                    "context_end_index": end,
                })

        return hits

    def _build_concatenated_context(self, text, context_windows):
        """Merge all context windows into one string without duplicate sentences."""
        if not context_windows or not text:
            return ""

        sentences = self._split_into_sentences(text)

        # Collect all (start, end) ranges from context windows
        ranges = []
        for cw in context_windows:
            ranges.append((cw["context_start_index"], cw["context_end_index"]))

        # Merge overlapping/adjacent ranges
        ranges.sort()
        merged = [ranges[0]]
        for start, end in ranges[1:]:
            prev_start, prev_end = merged[-1]
            if start <= prev_end:
                merged[-1] = (prev_start, max(prev_end, end))
            else:
                merged.append((start, end))

        # Join sentences from merged ranges, separating disjoint blocks
        blocks = [" ".join(sentences[s:e]) for s, e in merged]
        return " ".join(blocks)

    def _split_into_sentences(self, text):

        sentences = self._sentence_splitter.split(text)

        # strip leading or trailing whitespaces here
        return [s.strip() for s in sentences if s.strip()]

    def _finding_matching_phrases(self, single_sentence):
        """Find matching phrases in a single sentence.

        input: single sentence
        output: single sentence if this sentence includes a phrase as defined in
        Config var LIST_OF_PHRASES_TO_FILTER_FILINGS_FOR.
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
        context = re.sub(r'\s+', ' ', context)

        return start, end, context
