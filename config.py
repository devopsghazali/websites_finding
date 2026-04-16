# config.py - API keys aur settings

import os
from dotenv import load_dotenv

load_dotenv()

# Google Maps API Key — ab zaroorat nahi (free scraping mode mein)
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

# Anthropic (Claude) API Key - message generation ke liye (OPTIONAL)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Search settings
DEFAULT_COUNTRY = "India"
DEFAULT_RADIUS = 10000  # meters (10 km)
MAX_RESULTS = 60        # ek search mein kitne results chahiye (Google Maps max ~120)

# Filter settings
MIN_REVIEWS_THRESHOLD = 5    # kam reviews = growth potential
MAX_RATING_THRESHOLD = 4.5   # low rating = improvement needed

# Output settings
OUTPUT_DIR = "output"
CSV_FILENAME = "leads.csv"
