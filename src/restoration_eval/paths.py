"""Central path definitions for the painting restoration evaluation project."""
from pathlib import Path


def get_project_root() -> Path:
    """Return the current project root.

    Notebooks are expected to be run from the project root. If a notebook is
    run from the notebooks directory, this function returns its parent.
    """
    cwd = Path.cwd().resolve()
    if cwd.name == "notebooks":
        return cwd.parent
    return cwd


PROJECT_ROOT = get_project_root()

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
RAW_IMAGES_DIR = RAW_DIR / "images"
RAW_METADATA_DIR = RAW_DIR / "metadata"
RAW_METADATA_PILOT_PATH = RAW_METADATA_DIR / "metadata_pilot.csv"
RAW_METADATA_50_PATH = RAW_METADATA_DIR / "metadata_50.csv"

# Default metadata path for the current controlled 50-painting experiment.
RAW_METADATA_PATH = RAW_METADATA_50_PATH

PROCESSED_DIR = DATA_DIR / "processed"
CLEAN_DIR = PROCESSED_DIR / "clean"
MASK_DIR = PROCESSED_DIR / "masks"
MASKED_DIR = PROCESSED_DIR / "masked"
RESTORED_DIR = PROCESSED_DIR / "restored"
RESTORED_OPENCV_DIR = RESTORED_DIR / "opencv_telea"
PROCESSED_METADATA_DIR = PROCESSED_DIR / "metadata"

PROCESSED_CLEAN_METADATA_PATH = PROCESSED_METADATA_DIR / "metadata_processed_clean.csv"
MASK_METADATA_PATH = PROCESSED_METADATA_DIR / "metadata_masks.csv"
RESTORATION_METADATA_OPENCV_PATH = PROCESSED_METADATA_DIR / "metadata_restorations_opencv_telea.csv"

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
METRICS_DIR = OUTPUTS_DIR / "metrics"
FIGURES_DIR = OUTPUTS_DIR / "figures"
REPORTS_DIR = OUTPUTS_DIR / "reports"
LOGS_DIR = OUTPUTS_DIR / "logs"


def ensure_directories() -> None:
    """Create all standard project directories if they do not already exist."""
    for path in [
        RAW_IMAGES_DIR,
        RAW_METADATA_DIR,
        CLEAN_DIR,
        MASK_DIR,
        MASKED_DIR,
        RESTORED_OPENCV_DIR,
        PROCESSED_METADATA_DIR,
        METRICS_DIR,
        FIGURES_DIR,
        REPORTS_DIR,
        LOGS_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)
