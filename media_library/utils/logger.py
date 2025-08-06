import logging
import os

# Define the folder where logs will be stored
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Get `bilibili_scraper/`
DATA_FOLDER = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_FOLDER, exist_ok=True)  # Ensure the folder exists

# Define log file path
LOG_FILE = os.path.join(DATA_FOLDER, "bilibili_scraper.log")

# Configure logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# Create a logger instance
logger = logging.getLogger(__name__)
