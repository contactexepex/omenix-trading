import logging

from fno.ingestion.providers.base import Provider

log = logging.getLogger(__name__)

AUTO_PROVIDER = "auto"


def get_provider(name: str, config: dict) -> Provider:
    """`auto` uses Groww when its credentials are set (the owner's PC) and the free NSE website otherwise. A Groww
    provider built here alerts its failed sign-in and keeps out of A16's marks (story GW1); A16 builds its own."""
    name = (name or "nse").lower()
    if name == AUTO_PROVIDER:
        return _auto_provider(config)
    if name == "nse":
        from fno.ingestion.providers.public import NSEProvider

        return NSEProvider(config)
    if name == "groww":
        return _groww_provider(config)
    if name == "sample":
        from fno.ingestion.providers.sample import SampleProvider

        return SampleProvider(config)
    raise ValueError(f"Unknown provider: {name}")


def _auto_provider(config: dict) -> Provider:
    """Groww when credentials and its SDK are usable (the owner's PC), the free NSE website otherwise."""
    from fno.ingestion.providers.public import NSEProvider

    try:
        from fno.ingestion.providers.groww import has_groww_credentials

        if has_groww_credentials():
            return _groww_provider(config)
    except (ImportError, RuntimeError) as exc:
        log.warning("Groww unavailable (%s); using the NSE website for option chains", exc)
    return NSEProvider(config)


def _groww_provider(config: dict) -> Provider:
    from fno.ingestion.providers.groww import GrowwProvider
    from fno.ingestion.providers.groww_quiet_windows import MarkQuietWindows

    return GrowwProvider(config, alert_sign_in_failure, MarkQuietWindows())


def alert_sign_in_failure(line: str) -> None:
    """Story GW1: a token day's first failed Groww sign-in, one #fno-desk line; the outcome is printed, so an unsent
    alert is seen ("alert NOT sent: ...")."""
    from fno.ingestion.composition import build_alert_sender

    print(build_alert_sender().send(line))


__all__ = ["Provider", "get_provider"]
