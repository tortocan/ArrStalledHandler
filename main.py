import os
import sqlite3
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
import time
import logging

# Load environment variables
load_dotenv()

# Configuration from .env
RADARR_URL = os.getenv("RADARR_URL")
RADARR_API_KEY = os.getenv("RADARR_API_KEY")
SONARR_URL = os.getenv("SONARR_URL")
SONARR_API_KEY = os.getenv("SONARR_API_KEY")
STALLED_TIMEOUT = int(os.getenv("STALLED_TIMEOUT", 3600))
STALLED_ACTION = os.getenv("STALLED_ACTION", "BLOCKLIST_AND_SEARCH").upper()
VERBOSE = os.getenv("VERBOSE", "false").lower() == "true"
RUN_INTERVAL = int(os.getenv("RUN_INTERVAL", 300))  # Default to 300 seconds

DB_FILE = "stalled_downloads.db"

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if VERBOSE else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

def initialize_database():
    """Initialize the SQLite database for tracking stalled downloads."""
    if STALLED_TIMEOUT == 0:
        return  # Skip DB initialization if timeout is 0

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Create the table with the new schema
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stalled_downloads (
            download_id TEXT,
            first_detected TIMESTAMP NOT NULL,
            arr_service TEXT NOT NULL,
            PRIMARY KEY (download_id, arr_service)
        )
    """)

    conn.commit()
    conn.close()

def get_stalled_downloads_from_db(arr_service):
    """Retrieve stalled downloads for a specific service from the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Fetch all records for the specific service
    cursor.execute("SELECT download_id, first_detected FROM stalled_downloads WHERE arr_service = ?", (arr_service,))
    rows = cursor.fetchall()
    conn.close()

    # Convert download_id to string and timestamps to datetime
    return {str(row[0]): datetime.fromisoformat(row[1]) for row in rows}

def add_stalled_download_to_db(download_id, first_detected, arr_service):
    """Add a stalled download to the database if it does not already exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Insert only if the (download_id, arr_service) pair does not already exist
    cursor.execute("""
        INSERT OR IGNORE INTO stalled_downloads (download_id, first_detected, arr_service)
        VALUES (?, ?, ?)
    """, (str(download_id), first_detected.isoformat(), arr_service))

    added = cursor.rowcount > 0
    conn.commit()
    conn.close()

    return added

def remove_stalled_download_from_db(download_id, arr_service):
    """Remove a stalled download entry from the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Delete the record for the specific service
    cursor.execute("DELETE FROM stalled_downloads WHERE download_id = ? AND arr_service = ?", (download_id, arr_service))

    conn.commit()
    conn.close()

def query_api(url, headers, params=None):
    """Query an API endpoint and return the JSON response."""
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"API Request Error: {e}")
        return None

def post_api(url, headers, data=None):
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        logging.debug(f"Successfully performed POST action on {url} with data {data}.")
    except requests.RequestException as e:
        logging.error(f"API POST Error: {e}")

def delete_api(url, headers, params=None):
    try:
        response = requests.delete(url, headers=headers, params=params)
        response.raise_for_status()
        logging.debug(f"Successfully performed DELETE action on {url} with params {params}.")
    except requests.RequestException as e:
        logging.error(f"API DELETE Error: {e}")

def perform_action(base_url, headers, download_id, movie_id, service_name, episode_ids=None):
    # Define action descriptions for logging
    action_desc = {
        "REMOVE": f"remove (ID: {download_id})",
        "BLOCKLIST": f"blocklist (ID: {download_id})",
        "BLOCKLIST_AND_SEARCH": f"blocklist and search (ID: {download_id}, {'Episodes' if service_name == 'Sonarr' else 'Movie'}: {episode_ids if service_name == 'Sonarr' else movie_id})"
    }.get(STALLED_ACTION, "INVALID ACTION")

    if STALLED_ACTION == "REMOVE":
        action_url = f"{base_url}/api/v3/queue/{download_id}"
        logging.info(f"Performing action: {action_desc} in {service_name}...")
        delete_api(action_url, headers)

    elif STALLED_ACTION == "BLOCKLIST":
        action_url = f"{base_url}/api/v3/queue/{download_id}"
        params = {"blocklist": "true", "skipRedownload": "true"}
        logging.info(f"Performing action: {action_desc} in {service_name}...")
        delete_api(action_url, headers, params)

    elif STALLED_ACTION == "BLOCKLIST_AND_SEARCH":
        # Blocklist the item but allow redownload
        action_url = f"{base_url}/api/v3/queue/{download_id}"
        params = {"blocklist": "true", "skipRedownload": "false"}
        logging.info(f"Performing action: {action_desc} in {service_name}...")
        delete_api(action_url, headers, params)

        # Trigger a search via the Command API
        if service_name == "Sonarr" and episode_ids:
            command_url = f"{base_url}/api/v3/command"
            data = {"name": "EpisodeSearch", "episodeIds": episode_ids}
            logging.info(f"Triggering search for Episodes {episode_ids} in {service_name} using Command API...")
            post_api(command_url, headers, data)
        elif service_name == "Radarr" and movie_id:
            command_url = f"{base_url}/api/v3/command"
            data = {"name": "MoviesSearch", "movieIds": [movie_id]}
            logging.info(f"Triggering search for Movie ID {movie_id} in {service_name} using Command API...")
            post_api(command_url, headers, data)
        else:
            logging.warning(f"No valid IDs found for download ID {download_id} in {service_name}, skipping search.")

    else:
        logging.error(f"Invalid STALLED_ACTION: {STALLED_ACTION}")

def handle_stalled_downloads(base_url, api_key, service_name):
    """Handle stalled downloads for a given service (Radarr/Sonarr)."""
    if not base_url or not api_key:
        logging.warning(f"{service_name} handling is disabled.")
        return

    logging.info(f"Checking stalled downloads in {service_name}...")

    queue_url = f"{base_url}/api/v3/queue"
    headers = {"X-Api-Key": api_key}
    params = {"includeEpisode": "true"} if service_name == "Sonarr" else {}

    queue_response = query_api(queue_url, headers, params)
    if not queue_response or "records" not in queue_response:
        logging.error(f"Unexpected response from {service_name}: {queue_response}")
        return

    stalled_downloads = get_stalled_downloads_from_db(service_name)
    logging.debug(f"Stalled downloads for {service_name}: {stalled_downloads}")

    for item in queue_response["records"]:
        if item.get("errorMessage", "").lower() == "the download is stalled with no connections":
            download_id = str(item["id"])  # Ensure consistent type
            movie_id = item.get("movieId") if service_name == "Radarr" else None
            episode_ids = [item["episodeId"]] if service_name == "Sonarr" and "episodeId" in item else None

            logging.debug(f"Processing download ID {download_id}...")

            if download_id in stalled_downloads:
                first_detected = stalled_downloads[download_id]
                elapsed_time = (datetime.now(timezone.utc) - first_detected).total_seconds()

                logging.debug(f"Found in DB. First detected: {first_detected}, Elapsed time: {elapsed_time} seconds, Timeout: {STALLED_TIMEOUT} seconds.")

                if elapsed_time > STALLED_TIMEOUT:
                    logging.info(f"Handling Download ID {download_id} in {service_name} (elapsed time: {elapsed_time} seconds).")
                    perform_action(base_url, headers, download_id, movie_id, service_name, episode_ids)
                    remove_stalled_download_from_db(download_id, service_name)
                else:
                    logging.info(f"Download ID {download_id} in {service_name} is stalled but within timeout period ({elapsed_time} seconds).")
            else:
                logging.debug(f"Not found in DB. Adding to database.")
                added = add_stalled_download_to_db(download_id, datetime.now(timezone.utc), service_name)
                if added:
                    logging.info(f"Adding stalled download ID {download_id} in {service_name} to the database.")
                else:
                    logging.info(f"Download ID {download_id} in {service_name} is stalled but already in the database.")

if __name__ == "__main__":
    try:
        while True:
            initialize_database()
            handle_stalled_downloads(RADARR_URL, RADARR_API_KEY, "Radarr")
            handle_stalled_downloads(SONARR_URL, SONARR_API_KEY, "Sonarr")
            logging.info(f"Script execution completed. Sleeping for {RUN_INTERVAL} seconds...")
            time.sleep(RUN_INTERVAL)
    except KeyboardInterrupt:
        logging.info("Script terminated by user.")
    except Exception as e:
        logging.exception(f"An error occurred: {e}")