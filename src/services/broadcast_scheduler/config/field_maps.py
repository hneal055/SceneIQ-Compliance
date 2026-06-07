# =============================================================================
# src/services/broadcast_scheduler/config/field_maps.py
# Field-name maps for the three supported schedule formats.
#
# Add new field name variants here as new schedule formats are encountered.
#
# Extracted from the standalone broadcast-scheduler-parser's config/settings.py.
# Path-based settings (INPUT_DIR, OUTPUT_DIR, REPORTS_DIR, ARCHIVE_DIR, etc.)
# are NOT copied here — those are passed in at call time by the SceneIQ
# router so the parser stays free of hardcoded paths.
# =============================================================================


# Maps real-world CSV column headers -> internal standard field names.
# Add new header variants on the left as you discover them.
CSV_FIELD_MAP = {
    # Input field name   : Internal standard name
    "Title"              : "title",
    "title"              : "title",
    "Programme Title"    : "title",
    "Show Title"         : "title",
    "TX Time"            : "tx_time",
    "tx_time"            : "tx_time",
    "Transmission Time"  : "tx_time",
    "Air Time"           : "tx_time",
    "Duration"           : "duration",
    "duration"           : "duration",
    "Run Time"           : "duration",
    "Episode"            : "episode_number",
    "Ep No"              : "episode_number",
    "Series"             : "series_number",
    "Channel"            : "channel",
    "channel"            : "channel",
    "Network"            : "channel",
    "Genre"              : "genre",
    "Category"           : "genre",
    "Rights Start"       : "rights_start",
    "Rights End"         : "rights_end",
    "Licence Start"      : "rights_start",
    "Licence End"        : "rights_end",
}

# Maps BXF / XML tag names -> internal standard field names.
XML_FIELD_MAP = {
    "ProgramName"        : "title",
    "EpisodeTitle"       : "episode_title",
    "SeriesNumber"       : "series_number",
    "EpisodeNumber"      : "episode_number",
    "StartTime"          : "tx_time",
    "Duration"           : "duration",
    "ChannelRef"         : "channel",
    "ContentRef"         : "asset_id",
    "RightsStart"        : "rights_start",
    "RightsEnd"          : "rights_end",
}


# Maps JSON keys -> internal standard field names.
JSON_FIELD_MAP = {
    "title"               : "title",
    "programTitle"        : "title",
    "programmeTitle"      : "title",
    "episodeTitle"        : "episode_title",
    "txTime"              : "tx_time",
    "startTime"           : "tx_time",
    "airTime"             : "tx_time",
    "duration"            : "duration",
    "runTime"             : "duration",
    "episodeNumber"       : "episode_number",
    "episode"             : "episode_number",
    "seriesNumber"        : "series_number",
    "series"              : "series_number",
    "channel"             : "channel",
    "network"             : "channel",
    "genre"               : "genre",
    "category"            : "genre",
    "rightsStart"         : "rights_start",
    "rightsEnd"           : "rights_end",
    "assetId"             : "asset_id",
    "contentId"           : "asset_id",
"Daypart"            : "daypart",
"daypart"            : "daypart",
}
