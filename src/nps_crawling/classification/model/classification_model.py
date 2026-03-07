"""Classification model pipeline."""

import re

from nps_crawling.config import Config
from nps_crawling.llm.llm_ollama import LLMOllama


def _sanitize_filename(name: str) -> str:
    """Replace characters invalid in filenames (e.g. / \\ : * ? \" < > |) with underscore."""
    if not name or not isinstance(name, str):
        return "unknown"
    s = str(name).strip()
    s = re.sub(r'[<>:"/\\|?*]', "_", s)
    return s or "unknown"


class ClassificationModelPipeline(Config):
    """Classification model pipeline class."""

    def __init__(
        self,
        model: str = "mistral",
        host: str = "localhost",
        port: int = 14000,
    ):
        """Initializes ClassificationModelPipeline."""
        super().__init__()

        self.llm = LLMOllama(
            persona=self.OLLAMA_PERSONA,
            model=model,
            host=host,
            port=port,
            temperature=0.0,
            top_p=1.0,
            top_k=1,
            num_predict=128,
            seed=42,
            repeat_penalty=1.0,
        )

    def model_workflow(self, single_company_df):
        """Model workflow method.

        input: dataframe of single company including all context windows (1 per row)
              with columns: company, ticker, cik, filing_url, keywords_found, matched_phrase, context
        output: csv with classifications and original input data
        """
        if single_company_df is None or single_company_df.empty:
            return None

        result_df = single_company_df.copy()

        llm_outputs = []
        for _, row in result_df.iterrows():
            context_text = row.get("context") or ""
            llm_response = self.llm.classify(context_text)
            llm_outputs.append(llm_response)

        result_df["nps_classification"] = llm_outputs

        ticker = result_df["ticker"].iloc[0] if "ticker" in result_df.columns else None
        company = result_df["company"].iloc[0] if "company" in result_df.columns else None
        file_stem = _sanitize_filename(ticker) if ticker not in (None, "", "N/A") else _sanitize_filename(company)

        output_path = self.NPS_CLASSIFIED_CSV / f"{file_stem}_nps_classified.csv"
        result_df.to_csv(output_path, index=False)

        return None
