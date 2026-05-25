#!/bin/bash

# ============================================================
# PostgreSQL Backup Script
# Project: finance-econ-pipeline
# Database: analytics_lab
# Container: postgres-db
# ============================================================

PROJECT_DIR="/home/homeserver/projects/finance-econ-pipeline"
BACKUP_DIR="$PROJECT_DIR/backups/postgres"
LOG_FILE="$PROJECT_DIR/logs/postgres_backup.log"

DB_CONTAINER="postgres-db"
DB_USER="nate"
DB_NAME="analytics_lab"

TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_backup_${TIMESTAMP}.sql"

mkdir -p "$BACKUP_DIR"
mkdir -p "$PROJECT_DIR/logs"

echo "======================================" >> "$LOG_FILE"
echo "PostgreSQL backup started at: $(date)" >> "$LOG_FILE"
echo "Backup file: $BACKUP_FILE" >> "$LOG_FILE"

docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "Backup successful: $BACKUP_FILE" >> "$LOG_FILE"

    gzip "$BACKUP_FILE"

    echo "Compressed backup: ${BACKUP_FILE}.gz" >> "$LOG_FILE"

    # Delete backups older than 14 days
    find "$BACKUP_DIR" -type f -name "*.sql.gz" -mtime +14 -delete

    echo "Old backups older than 14 days removed." >> "$LOG_FILE"
else
    echo "Backup failed at: $(date)" >> "$LOG_FILE"
fi

echo "PostgreSQL backup finished at: $(date)" >> "$LOG_FILE"
echo "======================================" >> "$LOG_FILE"
