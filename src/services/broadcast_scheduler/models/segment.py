# =============================================================================
# src/services/broadcast_scheduler/models/segment.py
# The Segment class â€” represents a single item inside a broadcast schedule.
# A Segment is one row of a rundown: a show, an ad break, a promo, a slate, etc.
# =============================================================================


class Segment:
    """A single item (show, ad, promo, slate) inside a broadcast schedule."""

    # Creates a new Segment. Every field is optional so the parser can fill
    # them in one by one â€” different source formats provide different fields.
    def __init__(
        self,
        title=None,
        episode_title=None,
        tx_time=None,
        duration=None,
        episode_number=None,
        series_number=None,
        channel=None,
        genre=None,
        rights_start=None,
        rights_end=None,
        asset_id=None,
    ):
        self.title = title                  # programme or item title
        self.episode_title = episode_title  # secondary title, e.g. for series episodes
        self.tx_time = tx_time              # transmission time (HH:MM:SS:FF)
        self.duration = duration            # run time (HH:MM:SS:FF)
        self.episode_number = episode_number
        self.series_number = series_number
        self.channel = channel              # channel/network name
        self.genre = genre                  # category, e.g. "Drama", "News"
        self.rights_start = rights_start    # licence window start date
        self.rights_end = rights_end        # licence window end date
        self.asset_id = asset_id            # links to an Asset record

    # Returns a short readable summary when the Segment is printed.
    # Shows the three most useful fields for spotting a row in the log.
    def __repr__(self):
        return (
            f"Segment(title={self.title!r}, "
            f"tx_time={self.tx_time!r}, "
            f"duration={self.duration!r})"
        )



