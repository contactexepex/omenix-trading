"""The one entry the forecast lab calls for the recommender's block (story REC1d): it can never stop an 08:50 or
20:05 edition. It imports nothing of the recommender at load time, so nothing here can fail the lab's own import; a
failure to set the block up gives the edition as the inner maker made it, plus one alert naming the exception class."""


def with_recommend_section(maker, config: dict | None = None, ports=None):
    """`ports`: the sections' ports (tests); built from the repository and Drive only when the block is live."""
    try:
        from .report_wiring import build_recommend_maker

        return build_recommend_maker(maker, config, ports)
    except Exception as failed:  # isolation: nothing of the recommender may stop an edition
        from .report_maker import FailedRecommendMaker

        return FailedRecommendMaker(maker, failed)
