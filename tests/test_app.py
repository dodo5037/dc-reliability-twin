"""Module 7 test: the dashboard starts and every tab renders without an error."""
from streamlit.testing.v1 import AppTest


def test_dashboard_runs_without_exceptions():
    at = AppTest.from_file("../app.py", default_timeout=120).run()
    assert not at.exception
    assert at.title[0].value == "Dubai Data Center Reliability Twin"
    assert len(at.tabs) == 6
    assert len(at.metric) >= 11
