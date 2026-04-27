"""Pipeline to filter NPS mentions and extract context."""

import re

from nps_crawling.config import Config


class NpsMentionFilterPipeline(Config):
    """Pipeline to filter NPS mentions and extract context."""
    def __init__(self):
        """Initialize the NpsMentionFilterPipeline."""
        # normalize phrases to lowercase for case-insensitive matching
        self.filter_words = [p.lower() for p in Config.LIST_OF_PHRASES_TO_FILTER_FILINGS_FOR]
        self.exclude_words = [p.lower() for p in Config.LIST_OF_PHRASES_TO_EXCLUDE]

        # Sentence splitter: split on ., !, ? followed by whitespace.
        # Cheap and good enough for SEC prose.
        self._sentence_splitter = re.compile(r'(?<=[.!?])\s+')
        # Matches a whole [TABLE] ... [/TABLE] block. Used to protect its
        # internal periods (cell labels, abbreviations like "Messrs.",
        # decimals, "Inc.") from the sentence splitter so the entire table
        # stays in one sentence/context window.
        self._table_block_re = re.compile(r'\[TABLE\].*?\[/TABLE\]')

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
            sentences = self._split_into_sentences(text)
            record["context"] = self._extract_context_windows_from_sentences(sentences)
            record["all_context_windows"] = self._build_concatenated_context(
                sentences, record["context"],
            )
        return records

    def _extract_context_windows_from_sentences(self, sentences):
        """Extract all context windows from a list of sentences."""
        if not sentences:
            return []

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

    def _build_concatenated_context(self, sentences, context_windows):
        """Merge all context windows into one string without duplicate sentences."""
        if not context_windows or not sentences:
            return ""

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

    # Null byte stand-in for periods inside [TABLE] blocks. It survives the
    # sentence splitter and is restored after splitting. Null bytes never
    # occur in SEC filings, so this round-trip is safe.
    _PERIOD_PLACEHOLDER = "\x00"

    def _split_into_sentences(self, text):
        # Protect every [TABLE] ... [/TABLE] block so internal periods don't
        # fragment the table across context windows. Without this, a cell
        # like "Messrs. Norcia" or a decimal "1.37" would create a sentence
        # boundary and the table would spill out of the keyword's window.
        protected = self._table_block_re.sub(
            lambda m: m.group(0).replace(". ", self._PERIOD_PLACEHOLDER + " "),
            text,
        )
        sentences = self._sentence_splitter.split(protected)
        return [
            s.replace(self._PERIOD_PLACEHOLDER, ".").strip()
            for s in sentences
            if s.strip()
        ]

    def _finding_matching_phrases(self, single_sentence):
        """Find matching phrases in a single sentence.

        input: single sentence
        output: list of include phrases (from LIST_OF_PHRASES_TO_FILTER_FILINGS_FOR)
        found in the sentence, excluding hits that only appear as part of an
        excluded phrase (LIST_OF_PHRASES_TO_EXCLUDE).
        """
        sentence_lower = single_sentence.lower()
        masked_sentence = self._mask_excluded_phrases(sentence_lower)

        matches = []
        for phrase in self.filter_words:
            if phrase in masked_sentence:
                matches.append(phrase)

        return matches

    def _mask_excluded_phrases(self, sentence_lower):
        """Replace every occurrence of an excluded phrase with spaces.

        Spaces (rather than removal) preserve surrounding token boundaries so
        an include keyword adjacent to an excluded phrase can't accidentally
        merge with neighboring text.
        """
        masked = sentence_lower
        for excluded in self.exclude_words:
            if not excluded:
                continue
            masked = masked.replace(excluded, " " * len(excluded))
        return masked

    def _get_sentence_range(self, n, idx):
        start = max(0, idx - self.sentences_before)
        end = min(n, idx + self.sentences_after + 1)
        return start, end

    _TABLE_TOKEN_RE = re.compile(r"\[/?TABLE\]")

    def _create_context_window(self, sentences, start, end, idx, phrase):
        """Build a context window capped by character limits around the keyword.

        Joins sentences[start:end] into a single string, locates the matched
        phrase, then truncates to at most ``max_chars_before`` characters
        before and ``max_chars_after`` characters after the keyword.

        When the keyword sits inside a ``[TABLE] ... [/TABLE]`` block, the
        after-cap is stretched as needed to include the ``[/TABLE]``
        closer so the classifier always sees every value in the table.
        A final pass then drops any orphan ``[/TABLE]`` (opener lost to
        before-side truncation) or ``[TABLE]`` (closer lost to after-side
        truncation) along with the half-table still attached, so the
        output never emits a dangling marker.

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
        # Stretch the after-side cap when the keyword sits inside a table,
        # so the closer (and all its values) survives truncation.
        effective_after_cap = self._after_cap_for_enclosing_table(
            after_kw, self.max_chars_after,
        )
        if len(after_kw) > effective_after_cap:
            after_kw = after_kw[:effective_after_cap]
            char_cutoff = True

        context = (
            before_kw + full_context[kw_pos:kw_pos + len(phrase)] + after_kw
        ).strip()
        balanced = self._drop_orphan_table_markers(context)
        if balanced != context:
            char_cutoff = True
        return balanced, char_cutoff

    @staticmethod
    def _after_cap_for_enclosing_table(after_kw: str, max_chars: int) -> int:
        """If the leading ``[/TABLE]`` has no preceding ``[TABLE]`` in the
        after-text, the keyword is inside a table whose closer is further
        out. Return an expanded cap that reaches past that closer so the
        table stays whole.
        """
        # Scan for the first table marker.
        close_idx = after_kw.find("[/TABLE]")
        open_idx = after_kw.find("[TABLE]")
        # Keyword is inside a table iff a closer appears before any opener
        # (or no opener appears at all but a closer does).
        if close_idx == -1:
            return max_chars
        if open_idx == -1 or close_idx < open_idx:
            return max(max_chars, close_idx + len("[/TABLE]"))
        return max_chars

    @classmethod
    def _drop_orphan_table_markers(cls, text: str) -> str:
        """Remove orphan ``[TABLE]`` / ``[/TABLE]`` markers and the half-
        table attached to them.

        Leading orphan closer (opener lost to pre-truncation): drop
        everything up to and including the orphan ``[/TABLE]``.
        Trailing orphan opener (closer lost to post-truncation): drop
        everything from that ``[TABLE]`` onward.
        """
        tokens = [
            (m.start(), m.end(), m.group())
            for m in cls._TABLE_TOKEN_RE.finditer(text)
        ]

        # Leading orphan: any [/TABLE] with no preceding unmatched [TABLE].
        stack = 0
        drop_until = 0
        for start, end, tok in tokens:
            if tok == "[TABLE]":
                stack += 1
            elif stack > 0:
                stack -= 1
            else:
                drop_until = end
        if drop_until:
            text = text[drop_until:].lstrip()
            tokens = [
                (m.start(), m.end(), m.group())
                for m in cls._TABLE_TOKEN_RE.finditer(text)
            ]

        # Trailing orphan: any [TABLE] with no following [/TABLE].
        stack_positions = []
        for start, _end, tok in tokens:
            if tok == "[TABLE]":
                stack_positions.append(start)
            elif stack_positions:
                stack_positions.pop()
        if stack_positions:
            text = text[: stack_positions[0]].rstrip()

        return text
