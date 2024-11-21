
# ArrStalledHandler

ArrStalledHandler is a Python-based script designed to handle stalled downloads in [Radarr](https://radarr.video/) and [Sonarr](https://sonarr.tv/) by taking actions such as removing, blocklisting, or blocklisting and re-searching for the affected items. It supports configuration through a `.env` file, logging for visibility, and is deployable via Docker for ease of use.

This repository is licensed under the **[GNU General Public License v3.0 (GPLv3)](LICENSE)**.

Developed by **[Tommy Vange Rød](https://github.com/tommyvange)**.

----------

## Features

-   **Automatic Handling of Stalled Downloads**:
    -   Detect stalled downloads based on error messages from Radarr/Sonarr queues.
    -   Perform configurable actions such as:
        -   Remove the stalled download.
        -   Blocklist the stalled download.
        -   Blocklist and re-trigger a search for the movie or episodes.
-   **Database Tracking**:
    -   Tracks stalled downloads in a SQLite database to ensure actions are only taken after a specified timeout period.
-   **Logging**:
    -   Verbose and informative logging controlled via configuration.
-   **Docker Support**:
    -   Easily deployable with Docker and customizable run intervals.

----------


## Configuration

The script is fully configurable using environment variables specified in a `.env` file. Below is a description of each configuration option:

### `.env` Variables

| Variable         | Description                                                                 | Default Value         |
|------------------|-----------------------------------------------------------------------------|-----------------------|
| `RADARR_URL`     | The base URL for Radarr's API. Example: `http://localhost:7878`.            | None (required)       |
| `RADARR_API_KEY` | The API key for Radarr (found in Radarr settings).                         | None (required)       |
| `SONARR_URL`     | The base URL for Sonarr's API. Example: `http://localhost:8989`.           | None (required)       |
| `SONARR_API_KEY` | The API key for Sonarr (found in Sonarr settings).                         | None (required)       |
| `STALLED_TIMEOUT`| Time (in seconds) a download must remain stalled before actions are taken. | `3600` (1 hour)       |
| `STALLED_ACTION` | Action to perform on stalled downloads: `REMOVE`, `BLOCKLIST`, or `BLOCKLIST_AND_SEARCH`. | `BLOCKLIST_AND_SEARCH` |
| `VERBOSE`        | Enable verbose logging for debugging (`true` or `false`).                  | `false`               |
| `RUN_INTERVAL`   | Time (in seconds) between script executions when running in Docker.        | `300` (5 minutes)     |

To disable Radarr or Sonarr; leave the URL empty in the environment. If the service does not have a URL, then it is skipped.

----------

## How It Works

### Script Workflow

1.  **Initialization**:
    
    -   The script initializes a SQLite database (`stalled_downloads.db`) to track stalled downloads.
    -   It fetches the current queue from Radarr and Sonarr APIs.
2.  **Detect Stalled Downloads**:
    
    -   The script identifies stalled downloads based on the error message: `"The download is stalled with no connections"`.
3.  **Timeout Check**:
    
    -   Downloads are only handled if they have been stalled longer than the configured `STALLED_TIMEOUT`.
4.  **Perform Configured Action**:
    
    -   Based on the `STALLED_ACTION` setting:
        -   **REMOVE**: Removes the stalled download.
        -   **BLOCKLIST**: Removes and blocklists the stalled download.
        -   **BLOCKLIST_AND_SEARCH**: Removes, blocklists, and re-triggers a search for the movie or episodes.
5.  **Logging**:
    
    -   Logs detailed information about each action for visibility.
6.  **Repeat**:
    
    -   When running in Docker, the script waits for the `RUN_INTERVAL` duration and repeats the process.

----------

## Deployment

### Local Installation

1.  **Clone the Repository**:
    
    ``` bash
    git clone https://github.com/your-username/ArrStalledHandler.git
    cd ArrStalledHandler
    ```
    
2.  **Install Dependencies**:
    ``` bash
    pip install -r requirements.txt
    ```
        
3.  **Configure Environment**:
    
    Create a `.env` file and populate it with the required variables:
 
	``` env
	RADARR_URL=http://localhost:7878
	RADARR_API_KEY=your_radarr_api_key
	SONARR_URL=http://localhost:8989
	SONARR_API_KEY=your_sonarr_api_key
	STALLED_TIMEOUT=3600
	STALLED_ACTION=BLOCKLIST_AND_SEARCH
	VERBOSE=false
	RUN_INTERVAL=300
	```
        
4.  **Run the Script**:
    
    ``` bash
    python main.py
    ```

### Docker Deployment

1.  **Clone the Repository**:
    
    ``` bash
    git clone https://github.com/your-username/ArrStalledHandler.git
    cd ArrStalledHandler
    ```
    
2.  **Configure Environment**:
    
    Create a `.env` file and populate it with the required variables:
 
	``` env
	RADARR_URL=http://localhost:7878
	RADARR_API_KEY=your_radarr_api_key
	SONARR_URL=http://localhost:8989
	SONARR_API_KEY=your_sonarr_api_key
	STALLED_TIMEOUT=3600
	STALLED_ACTION=BLOCKLIST_AND_SEARCH
	VERBOSE=false
	RUN_INTERVAL=300
	```

3.  **Build the Docker Image**:
    
    ``` bash
    docker-compose build
    ```
    
4.  **Run the Docker Container**:
    
    ``` bash
    docker-compose up -d
    ```
    
5.  **Check output to verify that the script is working**:
    
    ``` bash
    docker-compose logs -f
    ```

----------

## Logging

-   Logs are written to the console and are controlled by the `VERBOSE` environment variable.
-   If `VERBOSE` is set to `true`, debug-level logs are enabled. 

Example log output:
    
``` text
INFO: Checking stalled downloads in Radarr...
INFO: Handling Download ID 1462067687 in Radarr (elapsed time: 400 seconds).
INFO: Triggering search for Movie ID 770 in Radarr using Command API...
INFO: Script execution completed. Sleeping for 300 seconds...
```
    

----------

## Troubleshooting

1. **Script Not Executing Actions**:
    -   Check if `STALLED_TIMEOUT` is too high.
    -   Verify the stalled downloads are correctly detected via Radarr/Sonarr queues.

----------

## Contributing

Contributions are welcome! If you find a bug or have an idea for improvement, feel free to open an issue or submit a pull request.

----------

# GNU General Public License v3.0 (GPLv3)

The  **GNU General Public License v3.0 (GPLv3)**  is a free, copyleft license for software and other creative works. It ensures your freedom to share, modify, and distribute all versions of a program, keeping it free software for everyone.

Full license can be read [here](LICENSE) or at [gnu.org](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text).

## Key Points:

1.  **Freedom to Share and Change:**
    
    -   You can distribute copies of GPLv3-licensed software.
    -   Access the source code.
    -   Modify the software.
    -   Create new free programs using parts of it.
2.  **Responsibilities:**
    
    -   If you distribute GPLv3 software, pass on the same freedoms to recipients.
    -   Provide the source code.
    -   Make recipients aware of their rights.
3.  **No Warranty:**
    
    -   No warranty for this free software.
    -   Developers protect your rights through copyright and this license.
4.  **Marking Modifications:**
    
    -   Clearly mark modified versions to avoid attributing problems to previous authors.
