"""Classification model pipeline."""

from nps_crawling.config import Config
from nps_crawling.llm.llm_ollama import LLMOllama


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
        output: csv with classifications and orignal input data
        """
        result_df = single_company_df.copy()

        llm_outputs = []

        for _, row in result_df.iterrows():
            context_text = row["context"]
            llm_response = self.llm.classify(context_text)
            llm_outputs.append(llm_response)

        result_df["nps_classification"] = llm_outputs

        ticker = str(result_df["ticker"].iloc[0]).strip().upper()

        output_path = self.NPS_CLASSIFIED_CSV / f"{ticker}_nps_classified.csv"

        result_df.to_csv(output_path, index=False)

        return None
