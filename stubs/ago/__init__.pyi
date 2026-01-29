from typing import Union
from datetime import datetime, timedelta

def human(
    subject: Union[datetime, timedelta, int, float],
    precision: int = 2,
    past_tense: str = "{} ago",
    future_tense: str = "in {}",
    abbreviate: bool = False
) -> str:
    ...