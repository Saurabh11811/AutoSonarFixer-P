import requests
import logging
import sys

# Import config manager for standalone run
sys.path.append("../utils")
from config_manager import ConfigManager

def create_sonar_project(server_url, auth_token, project_key, project_name):
    url = f"{server_url}/api/projects/create"
    auth = (auth_token, '')
    params = {
        'project': project_key,
        'name': project_name
    }

    try:
        response = requests.post(url, auth=auth, params=params)

        if response.status_code == 200:
            logging.info(f"Project {project_key} created successfully.")
        elif response.status_code == 400 and "already exists" in response.text:
            logging.info(f"Project {project_key} already exists.")
        else:
            logging.error(f"Failed to create project: {response.status_code} - {response.text}")
            raise Exception("Sonar project creation failed")
    except Exception as e:
        logging.error(f"Error creating Sonar project: {e}")
        raise

# Main method for standalone testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    config_mgr = ConfigManager()
    sonar_config = config_mgr.config['sonarqube']

    # Iterate enabled repos for testing
    for repo in config_mgr.get_enabled_repos():
        repo_url = repo['repo_url']
        repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')

        logging.info(f"Creating Sonar project for: {repo_name}")

        try:
            create_sonar_project(
                sonar_config['server_url'],
                sonar_config['auth_token'],
                repo_name,
                repo_name
            )
        except Exception as e:
            logging.error(f"Failed for repo {repo_name}: {e}")
