class OutOfRangeError(ValueError):
    ...

def from_latlon(
    latitude: float,
    longitude: float,
    force_zone_number: int | None = None,
    force_zone_letter: str | None = None,
) -> tuple[float, float, int, str]:
    ...

def to_latlon(
    easting: float,
    northing: float,
    zone_number: int,
    zone_letter: str | None = None,
    northern: bool | None = None,
    strict: bool = True,
) -> tuple[float, float]:
    ...
