#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jun 20 20:53:47 2025

@author: saurabh.agarwal
"""

import yaml
import logging
import sys
import os
import pprint

class ConfigManager:
    def __init__(self, config_path=None):
        # Dynamically compute project root
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        if config_path is None:
            self.config_path = os.path.join(self.project_root, "config", "config.yaml")
        else:
            self.config_path = config_path

        self.config = self.load_config()
        self.normalize_paths()

    def load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            logging.error(f"Error loading config file: {e}")
            sys.exit(1)

    def normalize_paths(self):
        """Normalize all relative paths to absolute paths based on project root"""

        # Normalize Sonar results path
        sonar_config = self.config.get('sonarqube', {})
        if 'results_path' in sonar_config:
            results_path = sonar_config['results_path']
            if not os.path.isabs(results_path):
                absolute_path = os.path.join(self.project_root, results_path)
                sonar_config['results_path'] = absolute_path

        # Normalize local_clone_path for each repo
        for repo in self.config.get('github', {}).get('repos', []):
            clone_path = repo.get('local_clone_path', '')
            if not os.path.isabs(clone_path):
                absolute_clone = os.path.join(self.project_root, clone_path)
                repo['local_clone_path'] = absolute_clone

    def save_config(self):
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
            logging.info("Config file updated.")
        except Exception as e:
            logging.error(f"Error writing config file: {e}")
            sys.exit(1)

    def get_enabled_repos(self):
        repos = self.config.get('github', {}).get('repos', [])
        return [repo for repo in repos if repo.get('enabled', False)]

    def update_repo_entry(self, repo_url, key, value):
        updated = False
        for repo in self.config.get('github', {}).get('repos', []):
            if repo.get('repo_url') == repo_url:
                repo[key] = value
                updated = True
        if updated:
            self.save_config()
        else:
            logging.warning(f"Repo URL {repo_url} not found in config.")

    def print_config(self):
        pp = pprint.PrettyPrinter(indent=2)
        pp.pprint(self.config)

# Standalone test entry point:
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    config_mgr = ConfigManager()
    config_mgr.print_config()
