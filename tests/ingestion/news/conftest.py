import pytest

from fno.ingestion.news.session import NEWS_PACER


@pytest.fixture(autouse=True)
def _forget_the_news_pacer():
    """The news pacer is process-wide like the shared one: no test may leave a host's state for the next."""
    yield
    NEWS_PACER._hosts.clear()
