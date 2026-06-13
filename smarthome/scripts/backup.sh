#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
TARGET_DIR="$BASE_DIR/backups/$STAMP"

mkdir -p "$TARGET_DIR"

copy_if_exists() {
  local src="$1"
  local dest="$2"
  if [[ -e "$src" ]]; then
    mkdir -p "$(dirname "$dest")"
    cp -a "$src" "$dest"
  fi
}

copy_if_exists "$BASE_DIR/n8n_data/database.sqlite" "$TARGET_DIR/n8n_data/database.sqlite"
copy_if_exists "$BASE_DIR/frigate_config/frigate.db" "$TARGET_DIR/frigate_config/frigate.db"
copy_if_exists "$BASE_DIR/mosquitto/config/mosquitto.conf" "$TARGET_DIR/mosquitto/config/mosquitto.conf"
copy_if_exists "$BASE_DIR/mosquitto.conf" "$TARGET_DIR/mosquitto.conf"

echo "Backup completed: $TARGET_DIR"
