"""When each foreign market's close is final (story A17e): its time zone and the local time its closing value is fixed,
the input of `available_at` and of the as-of rule. Times are the end of each market's closing auction (reasoning from
the exchanges' published hours; the boundary tests pin them), so a value is never labelled known before its market
could have fixed it. Daylight saving follows the zone (Sydney, London, Frankfurt, New York)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from .source import at_local


@dataclass(frozen=True)
class MarketClose:
    zone: str
    close: time
    lunch: tuple[time, time] | None = None  # the midday break, local time: no new level inside it

    def available_at(self, value_date: date) -> datetime:
        return at_local(value_date, self.close, self.zone)

    def at_lunch(self, moment: datetime) -> bool:
        local = moment.astimezone(ZoneInfo(self.zone)).time()
        return self.lunch is not None and self.lunch[0] <= local < self.lunch[1]


TOKYO = MarketClose("Asia/Tokyo", time(15, 30), (time(11, 30), time(12, 30)))  # 12:00 IST; lunch 08:00-09:00 IST
SEOUL = MarketClose("Asia/Seoul", time(15, 30))  # 12:00 IST
SHANGHAI = MarketClose("Asia/Shanghai", time(15, 0), (time(11, 30), time(13, 0)))  # 12:30 IST; lunch 09:00-10:30
TAIPEI = MarketClose("Asia/Taipei", time(13, 30))  # 11:00 IST
# after the closing auction: 13:40 IST; lunch 09:30-10:30 IST
HONG_KONG = MarketClose("Asia/Hong_Kong", time(16, 10), (time(12, 0), time(13, 0)))
SINGAPORE = MarketClose("Asia/Singapore", time(17, 0))  # 14:30 IST
# after the closing auction: 10:40 IST in Australian summer time, 11:40 in winter
SYDNEY = MarketClose("Australia/Sydney", time(16, 10))
LONDON = MarketClose("Europe/London", time(16, 35))  # after the closing auction
FRANKFURT = MarketClose("Europe/Berlin", time(17, 35))  # Xetra after the closing auction
EURO_STOXX = MarketClose("Europe/Berlin", time(17, 50))  # the Euro Stoxx 50's final value
NEW_YORK = MarketClose("America/New_York", time(16, 0))
CBOE_VIX = MarketClose("America/New_York", time(16, 15))  # VIX is calculated until 16:15 New York
