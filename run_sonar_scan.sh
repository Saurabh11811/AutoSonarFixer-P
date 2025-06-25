#!/bin/bash

REPO_PATH="$1"
PROJECT_KEY="$2"
SERVER_URL="$3"
AUTH_TOKEN="$4"
SONAR_SCANNER="$5"

if [ -z "$REPO_PATH" ] || [ -z "$PROJECT_KEY" ] || [ -z "$SERVER_URL" ] || [ -z "$AUTH_TOKEN" ] || [ -z "$SONAR_SCANNER" ]; then
  echo "Usage: $0 <repo_path> <project_key> <server_url> <auth_token> <scanner_path>"
  exit 1
fi

cd "$REPO_PATH" || exit 1

echo "Running SonarScanner for project: $PROJECT_KEY"

"$SONAR_SCANNER" \
  -Dsonar.projectKey="$PROJECT_KEY" \
  -Dsonar.sources=. \
  -Dsonar.host.url="$SERVER_URL" \
  -Dsonar.token="$AUTH_TOKEN" \
  -Dsonar.analysis.mode=publish \
  -Dsonar.scanner.forceCleanCache=true \
  -Dsonar.scm.disabled=true
