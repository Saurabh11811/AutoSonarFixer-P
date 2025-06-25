import os
import sys
import logging
import requests

# Import ConfigManager
sys.path.append("../utils")
from config_manager import ConfigManager

# Setup logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def detect_local_stack(repo_path):
    if not os.path.exists(repo_path):
        logging.error(f"Repo path does not exist: {repo_path}")
        return 'unknown'

    if os.path.exists(os.path.join(repo_path, 'requirements.txt')) or \
       os.path.exists(os.path.join(repo_path, 'setup.py')):
        logging.info("Local detection: Python project.")
        return 'python'

    if os.path.exists(os.path.join(repo_path, 'pom.xml')):
        logging.info("Local detection: Java Maven project.")
        return 'java-maven'

    if os.path.exists(os.path.join(repo_path, 'build.gradle')):
        logging.info("Local detection: Java Gradle project.")
        return 'java-gradle'

    logging.warning("Local detection: Could not determine tech stack.")
    return 'unknown'

def detect_github_stack(repo_url, api_token=""):
    try:
        parts = repo_url.rstrip('/').split('/')
        owner, repo = parts[-2], parts[-1]
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        headers = {'Authorization': f'token {api_token}'} if api_token else {}

        response = requests.get(api_url, headers=headers)
        if response.status_code != 200:
            logging.warning(f"GitHub API error {response.status_code}: {response.reason}")
            return 'unknown'

        repo_info = response.json()
        language = repo_info.get("language", "unknown")
        logging.info(f"GitHub API detection: Dominant language = {language}")

        if language.lower() == 'python':
            return 'python'
        if language.lower() == 'java':
            return 'java'
        return 'unknown'
    except Exception as e:
        logging.error(f"GitHub API call failed: {e}")
        return 'unknown'

def hybrid_decision(local_stack, github_stack):
    if local_stack != 'unknown':
        if github_stack != 'unknown' and local_stack != github_stack:
            logging.warning(f"Mismatch detected: Local={local_stack} | GitHub={github_stack}")
        else:
            logging.info("Both local & GitHub detection match.")
        return local_stack

    if github_stack != 'unknown':
        logging.info(f"Trusting GitHub detection: {github_stack}")
        if github_stack == 'java':
            # If GitHub only says 'Java', but local build files not found
            return 'java-unknown'
        return github_stack

    logging.warning("Both local and GitHub failed to detect.")
    return 'unknown'


def detect_tech_stack(repo_url, repo_path, api_token=""):
    local_stack = detect_local_stack(repo_path)
    github_stack = detect_github_stack(repo_url, api_token)
    final_stack = hybrid_decision(local_stack, github_stack)
    return final_stack


#only for standalone testing

if __name__ == "__main__":
    config = ConfigManager()

    for repo in config.get_enabled_repos():
        repo_url = repo['repo_url']
        clone_path = repo['local_clone_path']
        api_token = repo.get('api_token', '')

        repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        full_repo_path = os.path.join(clone_path, repo_name)

        logging.info(f"Detecting tech stack for repo: {repo_url}")

        local_stack = detect_local_stack(full_repo_path)
        github_stack = detect_github_stack(repo_url, api_token)
        final_stack = hybrid_decision(local_stack, github_stack)

        logging.info(f"FINAL TECH STACK for {repo_url}: {final_stack}")
        config.update_repo_entry(repo_url, 'detected_tech_stack', final_stack)
