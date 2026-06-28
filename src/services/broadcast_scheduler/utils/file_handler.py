# =============================================================================
# src/services/broadcast_scheduler/utils/file_handler.py
# File and folder operations shared across the parser.
#
# Unlike the standalone parser this came from, no path defaults are baked
# in â€” archive_dir is a required argument so SceneIQ can decide where to
# move files (or skip archiving entirely).
# =============================================================================

from datetime import datetime
from pathlib import Path
import shutil


# Toggles the [FILES] progress prints. Was in config/settings.py originally.
VERBOSE_LOGGING = True


# Returns a sorted list of files inside input_dir whose suffix matches
# one of the given extensions. Subdirectories are ignored. A missing
# input_dir returns an empty list (logged) rather than raising.
#
# Arguments:
#   input_dir   â€” folder to scan (string or Path)
#   extensions  â€” iterable of extensions to match, e.g. [".csv"], [".xml", ".bxf"]
def list_input_files(input_dir, extensions):
    input_dir = Path(input_dir)

    if not input_dir.exists():
        if VERBOSE_LOGGING:
            print(f"[FILES] (info) input folder does not exist: {input_dir}")
        return []

    # Normalise the extension list to lowercase for case-insensitive match
    wanted = {ext.lower() for ext in extensions}

    matched_files = []
    try:
        for entry in input_dir.iterdir():
            if not entry.is_file():
                continue
            if entry.suffix.lower() in wanted:
                matched_files.append(entry)
    except OSError as error:
        print(f"[FILES] ERROR listing {input_dir}: {error}")
        return []

    matched_files.sort()
    return matched_files


# Moves file_path into archive_dir. If a file with the same name already
# exists in the archive, appends a YYYYMMDD-HHMMSS timestamp to the stem
# so nothing gets overwritten. Returns the new Path on success, or None
# on failure (logged).
#
# Arguments:
#   file_path   â€” file to move (string or Path)
#   archive_dir â€” destination folder (REQUIRED â€” caller must specify)
def archive_file(file_path, archive_dir):
    file_path = Path(file_path)

    if archive_dir is None:
        print("[FILES] ERROR: archive_dir is required (caller must specify)")
        return None

    archive_dir = Path(archive_dir)

    if not file_path.exists():
        print(f"[FILES] ERROR: cannot archive â€” file not found: {file_path}")
        return None

    try:
        archive_dir.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        print(f"[FILES] ERROR creating archive folder {archive_dir}: {error}")
        return None

    destination = archive_dir / file_path.name

    # If a file with this name is already in the archive, give the new
    # one a timestamp suffix so we never silently overwrite.
    if destination.exists():
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        new_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        destination = archive_dir / new_name

    try:
        shutil.move(str(file_path), str(destination))
    except OSError as error:
        print(f"[FILES] ERROR archiving {file_path}: {error}")
        return None

    if VERBOSE_LOGGING:
        print(f"[FILES] Archived: {file_path.name} -> {destination}")

    return destination


# Light wrapper around mkdir(parents=True, exist_ok=True). Returns the
# Path so callers can chain â€” e.g. out_dir = ensure_folder_exists(...).
def ensure_folder_exists(folder_path):
    folder_path = Path(folder_path)
    folder_path.mkdir(parents=True, exist_ok=True)
    return folder_path




