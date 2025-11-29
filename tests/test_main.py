"""Tests for the nps_crawling main module."""

import sys
from runpy import run_module

from nps_crawling import __version__


class RaiseExceptionOnce:
    """Callable that raises an exception the first time it's called."""
    def __init__(self, exception):
        """Initialize with the exception to raise."""
        self.has_run = False
        self.exception = exception

    def __call__(self, *args, **kwargs):
        """Raise the exception only once."""
        if not self.has_run:
            self.has_run = True
            raise self.exception


def test_main_prints_version(capsys):
    """Test that the main module prints the correct version."""
    try:
        sys.argv[1:] = ["--version"]
        run_module("nps_crawling", run_name="__main__", alter_sys=True)
    except SystemExit:
        pass
    assert capsys.readouterr().out == f"{__version__}\n"


# def test_main_verbose(caplog):
#    """Test that the main module runs with increased verbosity."""
#    from nps_crawling.__main__ import main
#
#    try:
#        caplog.set_level(logging.INFO)
#        main(["-v"])
#        assert os.path.exists("nps_filings.json")
#        assert True  # normal end
#    except SystemExit:
#        assert False


# @pytest.mark.parametrize(
#    "options, offset",
#    [
#        pytest.param([], 0, id="default"),
#        pytest.param(["-v"], 10, id="v"),
#        pytest.param(["-vv"], 20, id="vv"),
#        pytest.param(["-vvv"], 30, id="vvv"),
#        pytest.param(["-q"], -10, id="q"),
#        pytest.param(["-qq"], -20, id="qq"),
#        pytest.param(["-qqq"], -30, id="qqq"),
#        pytest.param(["-vv", "-qq"], 0, id="vvqq - default"),
#        pytest.param(["-vv", "-q"], 10, id="vvq"),
#        pytest.param(["-v", "-qq"], -10, id="vqq"),
#    ],
# )
# def test_verbosity_setting(options, offset, monkeypatch):
#    """Test that the main module sets the correct log level."""
#    from nps_crawling.__main__ import main
#
#    default_log_level = logging.WARNING
#    mock_set_level = MagicMock()
#    monkeypatch.setattr("nps_crawling.__main__.log.setLevel", mock_set_level)
#    main(options)
#    mock_set_level.assert_called_with(min(logging.CRITICAL, max(logging.DEBUG, default_log_level - offset)))

# @pytest.mark.parametrize(
#    "options, logs",
#    [
#        pytest.param([], ["Exception from log.info", "Hint: Rerun with"], id="plain"),
#        pytest.param(["-v"], ["Exception from log.info", "Traceback"], id="verbose"),
#    ],
# )
# def test_main_exception(options, logs, monkeypatch, caplog):
#    """Test that the main module handles exceptions correctly."""
#    from nps_crawling.__main__ import log, main
#
#    monkeypatch.setattr(log, "info", RaiseExceptionOnce(Exception("Exception from log.info")))
#    with pytest.raises(SystemExit) as error:
#        main(options)
#    assert error.value.code == 1
#    assert all(x in caplog.text for x in logs)
#
#
# def test_main_interrupt(monkeypatch, caplog):
#    """Test that the main module handles KeyboardInterrupt correctly."""
#    from nps_crawling.__main__ import log, main
#
#    monkeypatch.setattr(log, "info", RaiseExceptionOnce(KeyboardInterrupt()))
#    with pytest.raises(SystemExit) as error:
#        main([])
#    assert error.value.code == 1
#    assert "Aborted by user" in caplog.text
