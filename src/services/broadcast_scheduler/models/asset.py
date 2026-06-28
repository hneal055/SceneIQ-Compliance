# =============================================================================
# src/services/broadcast_scheduler/models/asset.py
# The Asset class â€” represents the underlying media file referenced by a segment.
# Many segments may point to the same Asset via its asset_id.
# =============================================================================


class Asset:
    """A media file (programme, ad, promo) used to fulfil one or more segments."""

    # Creates a new Asset. Every field is optional so the parser can fill them
    # in incrementally as asset records are discovered in the source file.
    def __init__(
        self,
        asset_id=None,
        title=None,
        file_path=None,
        format=None,
        duration=None,
    ):
        self.asset_id = asset_id    # unique identifier, used by Segment.asset_id
        self.title = title          # human-readable asset name
        self.file_path = file_path  # location of the media file on disk/storage
        self.format = format        # e.g. "MXF", "MOV", "MP4"
        self.duration = duration    # length of the media (HH:MM:SS:FF)

    # Returns a short readable summary when the Asset is printed.
    def __repr__(self):
        return (
            f"Asset(asset_id={self.asset_id!r}, "
            f"title={self.title!r}, "
            f"format={self.format!r})"
        )



