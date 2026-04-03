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
        self.max_chars_before = Config.MAX_CONTEXT_CHARS_BEFORE_KEYWORD
        self.max_chars_after = Config.MAX_CONTEXT_CHARS_AFTER_KEYWORD

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
                "char_cutoff_applied": bool,
            }
        The context string is built from up to N sentences before/after the
        hit sentence, then capped at MAX_CONTEXT_CHARS_BEFORE_KEYWORD /
        MAX_CONTEXT_CHARS_AFTER_KEYWORD characters on each side of the
        matched keyword. ``char_cutoff_applied`` is True when either side
        was truncated.
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

            start, end = self._get_sentence_range(n, idx)

            for phrase in matched_phrases:
                context, char_cutoff = self._create_context_window(
                    sentences, start, end, idx, phrase,
                )
                hits.append({
                    "matched_phrase": phrase,
                    "context": context,
                    "hit_sentence_index": idx,
                    "context_start_index": start,
                    "context_end_index": end,
                    "char_cutoff_applied": char_cutoff,
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

    def _get_sentence_range(self, n, idx):
        start = max(0, idx - self.sentences_before)
        end = min(n, idx + self.sentences_after + 1)
        return start, end

    def _create_context_window(self, sentences, start, end, idx, phrase):
        """Build a context window capped by character limits around the keyword.

        Joins sentences[start:end] into a single string, locates the matched
        phrase, then truncates to at most ``max_chars_before`` characters
        before and ``max_chars_after`` characters after the keyword.

        Returns (context_string, char_cutoff_applied).
        """
        full_context = " ".join(sentences[start:end])
        full_context = re.sub(r'\s+', ' ', full_context).strip()

        # Find the keyword position in the full context (case-insensitive)
        kw_pos = full_context.lower().find(phrase.lower())
        if kw_pos == -1:
            return full_context, False

        before_kw = full_context[:kw_pos]
        after_kw = full_context[kw_pos + len(phrase):]

        char_cutoff = False
        if len(before_kw) > self.max_chars_before:
            before_kw = before_kw[-self.max_chars_before:]
            char_cutoff = True
        if len(after_kw) > self.max_chars_after:
            after_kw = after_kw[:self.max_chars_after]
            char_cutoff = True

        context = (before_kw + full_context[kw_pos:kw_pos + len(phrase)] + after_kw).strip()
        return context, char_cutoff
