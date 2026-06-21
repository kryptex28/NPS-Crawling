from nps_crawling.classification.common import classification_config_basename


def test_classification_config_basename_sanitizes_path_chars():
    assert classification_config_basename("a/b") == "a_b"
    assert classification_config_basename('x:y*z?') == "x_y_z_"


def test_classification_config_basename_trims_and_truncates():
    assert classification_config_basename("  NPS Category  ") == "NPS Category"
    assert len(classification_config_basename("x" * 300, max_length=10)) == 10
