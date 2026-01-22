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
        """
        Model workflow method.

        input: dataframe of single company including all context windows (1 per row)
        output: excel file with 1 row with classification and original input data
        """

        combined_context = " --- ".join(
            self.normalize_context_text(ctx)
            for ctx in single_company_df["context"].astype(str).tolist()
        )

        llm_response = self.llm.classify(combined_context)

        category, reason = self.parse_llm_response(llm_response)

        result_df = single_company_df.iloc[[0]].copy()

        result_df.loc[result_df.index[0], "context"] = combined_context

        result_df["nps_category"] = category
        result_df["nps_reason"] = reason

        ticker = str(result_df["ticker"].iloc[0]).strip().upper()
        output_path = self.NPS_CLASSIFIED_EXCEL / f"{ticker}_nps_classified.xlsx"

        result_df.to_excel(output_path, index=False, engine="openpyxl")

        return None
    
    def parse_llm_response(self, response):
        #TODO: might need to adapt the response of the model whatever makes sense here
        """
        Parse LLM response in the format:
        <CATEGORY>|<REASON>
        """
        if not isinstance(response, str):
            return "", ""

        response = response.strip()

        if "|" not in response:
            return "", ""

        category, reason = response.split("|", 1)

        return category.strip(), reason.strip()
    
    def normalize_context_text(self, text: str) -> str:
        if not isinstance(text, str):
            return ""
        return " ".join(text.replace("\n", " ").split())
    
    #TODO: this was how it was done for each context window seperately. remove it later if not needed anymore
    # def model_workflow(self, single_company_df):
    #     """Model workflow method.

    #     input: dataframe of single company including all context windows (1 per row)
    #     output: csv with classifications and orignal input data
    #     """

    #     result_df = single_company_df.copy()

    #     llm_outputs = []

    #     for _, row in result_df.iterrows():
    #         context_text = row["context"]
    #         llm_response = self.llm.classify(context_text)
    #         llm_outputs.append(llm_response)

    #     result_df["nps_classification"] = llm_outputs

    #     ticker = str(result_df["ticker"].iloc[0]).strip().upper()
        
    #     output_path = self.NPS_CLASSIFIED_EXCEL / f"{ticker}_nps_classified."

    #     result_df.to_excel(output_path, index=False, engine="openpyxl")

    #     return None