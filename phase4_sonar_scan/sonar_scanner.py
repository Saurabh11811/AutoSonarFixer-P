#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
import subprocess
import requests
import json
from datetime import datetime
import time

# Adjust sys.path for relative imports
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(project_root, "../utils"))
from config_manager import ConfigManager

sys.path.append(os.path.join(project_root, "../phase4_sonar_scan"))
import sonar_project_creator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

shell_script = os.path.join(os.path.dirname(project_root), "run_sonar_scan.sh")

def run_full_sonar_pipeline(repo_path, repo_name, config):
    sonar_config = config['sonarqube']
    server_url = sonar_config['server_url']
    auth_token = sonar_config['auth_token']
    scanner_path = sonar_config['scanner_path']

    sonar_project_creator.create_sonar_project(server_url, auth_token, repo_name, repo_name)

    user_shell = os.environ.get("SHELL", "/bin/bash")
    command = f"'{shell_script}' '{repo_path}' '{repo_name}' '{server_url}' '{auth_token}' '{scanner_path}'"

    try:
        subprocess.run([user_shell, "-l", "-c", command], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Sonar scan failed: {e}")
        raise
    print("Sleeping 10 seconds to let sonar porject populated for repo - ", repo_name)
    time.sleep(10)
    fetch_and_store_raw_sonar_report(repo_name, config)

def fetch_and_store_raw_sonar_report(repo_name, config):
    sonar_config = config['sonarqube']
    server_url = sonar_config['server_url']
    auth_token = sonar_config['auth_token']
    admin_username = sonar_config['admin_username']
    admin_password = sonar_config['admin_password']

    branch = get_main_branch(server_url, auth_token, repo_name)
    token_auth = (auth_token, '')
    admin_auth = (admin_username, admin_password)

    # Issues
    issues, page, page_size = [], 1, 500
    while True:
        params = {
            'componentKeys': repo_name, 'branch': branch,
            'statuses': 'OPEN,CONFIRMED,REOPENED,RESOLVED,CLOSED',
            'severities': 'INFO,MINOR,MAJOR,CRITICAL,BLOCKER',
            'types': 'CODE_SMELL,BUG,VULNERABILITY',
            'ps': page_size, 'p': page
        }
        response = requests.get(f"{server_url}/api/issues/search", auth=token_auth, params=params)
        if response.status_code != 200:
            raise Exception(f"Issues fetch failed: {response.status_code} - {response.text}")
        data = response.json()
        issues.extend(data.get("issues", []))
        if page * page_size >= data["paging"]["total"]: break
        page += 1

    # Hotspots
    hotspots, page = [], 1
    while True:
        params_hotspots = {'projectKey': repo_name, 'ps': page_size, 'p': page}
        response_hotspots = requests.get(f"{server_url}/api/hotspots/search", auth=admin_auth, params=params_hotspots)
        if response_hotspots.status_code != 200:
            raise Exception(f"Hotspots fetch failed: {response_hotspots.status_code} - {response_hotspots.text}")
        data_hotspots = response_hotspots.json()
        hotspots.extend(data_hotspots.get("hotspots", []))
        if page * page_size >= data_hotspots["paging"]["total"]: break
        page += 1

    results_dir = os.path.join(sonar_config['results_path'], repo_name)
    os.makedirs(results_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    full_snapshot_path = os.path.join(results_dir, f"{timestamp}_full_snapshot.json")
    with open(full_snapshot_path, 'w') as f:
        json.dump({"issues": issues, "hotspots": hotspots}, f, indent=2)
    logging.info(f"✅ Raw snapshot stored: {full_snapshot_path}")

def get_main_branch(server_url, auth_token, project_key):
    auth = (auth_token, '')
    url = f"{server_url}/api/project_branches/list?project={project_key}"
    response = requests.get(url, auth=auth)
    if response.status_code == 200:
        for branch in response.json().get("branches", []):
            if branch.get("isMain", False): return branch["name"]
    return "main"

if __name__ == "__main__":
    config_mgr = ConfigManager()
    config = config_mgr.config
    enabled_repos = config_mgr.get_enabled_repos()

    for repo in enabled_repos:
        repo_name = repo['repo_url'].rstrip('/').split('/')[-1].replace('.git', '')
        full_repo_path = os.path.join(repo['local_clone_path'], repo_name)
        logging.info(f"🚀 Running scan for repo: {repo_name}")
        run_full_sonar_pipeline(full_repo_path, repo_name, config)

    # Direct call reporter
    sys.path.append(project_root)
    import phase4_sonar_scan.sonar_summary_reporter as reporter
    reporter.run_summary()
