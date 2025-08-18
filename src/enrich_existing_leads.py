#!/usr/bin/env python3
"""Enrich existing leads with Place Details API data."""

import os
import time
import re
import logging
from typing import Optional
from dotenv import load_dotenv
import requests

from database import get_db_session
from models import Lead
from sqlmodel import select

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PLACE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"


def get_place_details(place_id: str) -> dict:
    """Get detailed information for a place using Place Details API."""
    if not GOOGLE_API_KEY:
        logger.error("No Google API key found")
        return {}
    
    params = {
        "place_id": place_id,
        "key": GOOGLE_API_KEY,
        "fields": "name,formatted_phone_number,website,formatted_address,rating,user_ratings_total"
    }
    
    try:
        response = requests.get(PLACE_DETAILS_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "OK":
            return data.get("result", {})
        else:
            logger.warning(f"API returned status: {data.get('status')} for place_id: {place_id}")
            return {}
            
    except Exception as e:
        logger.error(f"Failed to get details for place {place_id}: {e}")
        return {}


def extract_place_id_from_notes(notes: str) -> Optional[str]:
    """Extract place_id from notes field."""
    if not notes:
        return None
    
    # Look for place_id: XXXXX pattern
    match = re.search(r'place_id:\s*([A-Za-z0-9_-]+)', notes)
    if match:
        return match.group(1)
    
    return None


def enrich_existing_leads(max_leads: Optional[int] = None):
    """Enrich existing leads with website and phone data."""
    
    session = get_db_session()
    enriched_count = 0
    
    try:
        # Get leads that don't have website or phone but have place_id in notes
        leads = session.exec(
            select(Lead).where(
                (Lead.website_url.is_(None)) | (Lead.phone.is_(None))
            ).where(
                Lead.notes.like("%place_id:%")
            ).where(
                Lead.source == "googlemaps"
            )
        ).all()
        
        if max_leads:
            leads = leads[:max_leads]
        
        logger.info(f"Found {len(leads)} leads to enrich")
        
        for i, lead in enumerate(leads):
            place_id = extract_place_id_from_notes(lead.notes)
            if not place_id:
                logger.warning(f"Could not extract place_id from notes for {lead.company_name}")
                continue
            
            logger.info(f"Enriching {i+1}/{len(leads)}: {lead.company_name} (place_id: {place_id})")
            
            details = get_place_details(place_id)
            if details:
                updated = False
                
                # Update website if missing
                if not lead.website_url and details.get("website"):
                    lead.website_url = details["website"]
                    updated = True
                    logger.info(f"  ✅ Added website: {details['website']}")
                
                # Update phone if missing
                if not lead.phone and details.get("formatted_phone_number"):
                    lead.phone = details["formatted_phone_number"]
                    updated = True
                    logger.info(f"  ✅ Added phone: {details['formatted_phone_number']}")
                
                if updated:
                    enriched_count += 1
                else:
                    logger.info(f"  ℹ️  No new data available")
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
        
        session.commit()
        logger.info(f"Successfully enriched {enriched_count} leads")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error enriching leads: {e}")
    finally:
        session.close()
    
    return enriched_count


if __name__ == "__main__":
    import sys
    
    max_leads = None
    if len(sys.argv) > 1:
        try:
            max_leads = int(sys.argv[1])
            logger.info(f"Limiting to {max_leads} leads for testing")
        except ValueError:
            logger.error("Invalid number provided")
            sys.exit(1)
    
    enriched = enrich_existing_leads(max_leads)
    print(f"Enriched {enriched} leads with additional data!")
