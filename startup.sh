#!/bin/bash
set -e

echo "🚀 Starting Dentistry Lead Generation System..."
echo "================================================"

# Function to wait for PostgreSQL
wait_for_postgres() {
    echo "⏳ Waiting for PostgreSQL to be ready..."
    
    for i in {1..30}; do
        if PGPASSWORD=$POSTGRES_PASSWORD psql -h db -U dentistry_user -d dentistry_db -c "SELECT 1;" >/dev/null 2>&1; then
            echo "✅ PostgreSQL is ready!"
            return 0
        fi
        echo "   Attempt $i/30: PostgreSQL not ready yet, waiting 2 seconds..."
        sleep 2
    done
    
    echo "❌ PostgreSQL is not ready after 60 seconds"
    exit 1
}

# Create data directory for exports
mkdir -p /app/data

# Wait for PostgreSQL
wait_for_postgres

# Run the automated pipeline
echo "🎯 Starting automated pipeline..."
uv run python src/main.py auto

echo ""
echo "🎉 All done! Check /app/data/leads_export.csv for results"
echo "📊 Pipeline completed successfully - container will exit"
echo ""
echo "💡 To run again: docker compose up --build"
echo "💡 To inspect results: cat ./data/leads_export.csv"
echo "💡 To check database: docker compose exec db psql -U dentistry_user -d dentistry_db"
