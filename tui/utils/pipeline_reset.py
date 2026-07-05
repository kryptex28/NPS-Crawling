"""Reset cached pipeline instances after project configuration changes."""


def reset_pipeline_models() -> None:
    """Reset the singleton instances and caches of crawl, preprocess, and classification models."""
    from models.classification_model import ClassificationModel
    from models.crawl_model import CrawlModel
    from models.preprocessing_model import PreprocessingModel

    for model_cls in (CrawlModel, PreprocessingModel, ClassificationModel):
        instance = getattr(model_cls, "instance", None)
        if instance is None:
            continue
        if hasattr(instance, "_crawl"):
            instance._crawl = None
        if hasattr(instance, "_preprocessing"):
            instance._preprocessing = None
        if hasattr(instance, "_classification"):
            instance._classification = None
