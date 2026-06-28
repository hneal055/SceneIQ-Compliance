# =============================================================================
# src/services/broadcast_scheduler/models/schedule.py
# The Schedule class â€” represents a full broadcast rundown for one channel/day.
# A Schedule holds a list of Segment objects in transmission order.
# =============================================================================


class Schedule:
    """A broadcast schedule (rundown) for a single channel on a single date."""

    # Creates a new Schedule. All fields are optional so the parser can fill
    # them in step by step as it reads the source file.
    def __init__(self, channel_name=None, schedule_date=None, source_filename=None):
        self.channel_name = channel_name        # e.g. "BBC One"
        self.schedule_date = schedule_date      # the date this rundown is for
        self.source_filename = source_filename  # the file this Schedule came from
        self.segments = []                      # list of Segment objects in TX order

    # Adds a single Segment object to the end of this schedule's segment list.
    # Use this from inside the parsers as each row/element is read.
    def add_segment(self, segment):
        self.segments.append(segment)

    # Returns a short readable summary when the Schedule is printed.
    # Helpful for the progress messages the parser logs to the console.
    def __repr__(self):
        return (
            f"Schedule(channel={self.channel_name!r}, "
            f"date={self.schedule_date!r}, "
            f"segments={len(self.segments)})"
        )




