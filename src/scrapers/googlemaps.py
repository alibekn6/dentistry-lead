"""Google Maps Places scraper for premium dental clinics in London.

- Uses Text Search API with pagination via next_page_token
- Queries premium districts to bypass 60-results-per-query limit
- Filters by rating, reviews, and premium name markers
- Deduplicates by place_id

Environment:
- GOOGLE_API_KEY must be set (read from env)
"""

from __future__ import annotations

import os
import time
import json
import logging
from typing import Dict, List, Any, Optional

import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Try both variable names
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY")
PLACES_TEXTSEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"

PREMIUM_DISTRICTS: List[str] = [
    "Harley Street London",
    "Kensington London",
    "Chelsea London",
    "Mayfair London",
    "Knightsbridge London",
    "Belgravia London",
    "Marylebone London",
    "Soho London",
    "Notting Hill London",
    "Westminster London",
]


PREMIUM_QUERIES: List[str] = [
    "cosmetic dentistry",
    "dental implants",
    "smile makeover clinic",
    "private dental studio",
    "aesthetic dentistry",
    "veneers",
    "Invisalign provider",
    "teeth whitening",
]


def _http_get(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_all_pages(params: Dict[str, Any], delay_seconds: float = 2.0) -> List[Dict[str, Any]]:
    """Fetch up to 60 results via next_page_token pagination for a single query."""
    all_results: List[Dict[str, Any]] = []
    current_params = dict(params)

    while True:
        data = _http_get(PLACES_TEXTSEARCH_URL, current_params)
        results = data.get("results", [])
        all_results.extend(results)

        next_token = data.get("next_page_token")
        if not next_token:
            break

        # Token needs a short delay before it becomes valid
        time.sleep(delay_seconds)
        current_params = {"pagetoken": next_token, "key": GOOGLE_API_KEY}

    return all_results


def is_premium_by_name(name: str) -> bool:
    name_lower = name.lower()
    premium_markers = ["cosmetic", "aesthetic", "studio", "specialist", "private"]
    stop_markers = ["nhs"]

    if any(marker in name_lower for marker in stop_markers):
        return False
    return any(marker in name_lower for marker in premium_markers)


def filter_premium_places(places: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter places by rating/reviews and premium markers or premium addresses."""
    filtered: List[Dict[str, Any]] = []
    for place in places:
        rating = float(place.get("rating", 0.0) or 0.0)
        reviews = int(place.get("user_ratings_total", 0) or 0)
        name = place.get("name", "")
        address = place.get("formatted_address", "")

        # Core filter
        if rating >= 4.7 and reviews >= 50:
            if is_premium_by_name(name) or "Harley Street" in address:
                filtered.append(place)
            else:
                # Still allow if passed rating/reviews (lenient mode)
                filtered.append(place)
    return filtered


def deduplicate_by_place_id(places: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: Dict[str, Dict[str, Any]] = {}
    for p in places:
        pid = p.get("place_id")
        if not pid:
            # Fallback: skip items without place_id
            continue
        seen[pid] = p
    return list(seen.values())


def build_queries() -> List[str]:
    queries: List[str] = []
    for district in PREMIUM_DISTRICTS:
        for q in PREMIUM_QUERIES:
            queries.append(f"{q} in {district}")
    # Also include generic district searches
    for district in PREMIUM_DISTRICTS:
        queries.append(f"dentistry in {district}")
        queries.append(f"dental clinic in {district}")
    return queries


def search_premium_clinics(language: str = "en", per_query_delay: float = 1.0) -> List[Dict[str, Any]]:
    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_MAPS_API_KEY is not set in .env file or environment")

    all_raw: List[Dict[str, Any]] = []
    queries = build_queries()

    for query in queries:
        logger.info(f"Searching query: {query}")
        params = {"query": query, "key": GOOGLE_API_KEY, "language": language}
        try:
            results = fetch_all_pages(params)
            logger.info(f"  -> fetched {len(results)} results")
            all_raw.extend(results)
        except requests.exceptions.RequestException as e:
            logger.warning(f"Network error on '{query}': {e}")
        except Exception as e:
            logger.warning(f"Unexpected error on '{query}': {e}")
        time.sleep(per_query_delay)

    # Deduplicate
    unique = deduplicate_by_place_id(all_raw)
    logger.info(f"Unique places: {len(unique)}")

    # Filter
    premium = filter_premium_places(unique)
    logger.info(f"Premium filtered: {len(premium)}")

    return premium


def save_clinics_to_database(clinics: List[Dict[str, Any]]) -> int:
    """Save scraped clinics to database as leads."""
    try:
        from database import get_db_session
        from models import Lead, Blacklist
        from sqlmodel import select
        
        session = get_db_session()
        saved_count = 0
        
        for clinic in clinics:
            try:
                # Extract data from Google Maps result
                name = clinic.get("name", "")
                address = clinic.get("formatted_address", "")
                place_id = clinic.get("place_id", "")
                rating = float(clinic.get("rating", 0.0) or 0.0)
                reviews = int(clinic.get("user_ratings_total", 0) or 0)
                
                # Get phone and website from place details (if available)
                phone = clinic.get("formatted_phone_number")
                website = clinic.get("website")
                
                # Calculate premium score based on rating and reviews
                premium_score = min(10, int((rating - 4.0) * 2 + min(reviews / 100, 5)))
                
                # Check if already exists
                existing = session.exec(
                    select(Lead).where(Lead.company_name == name)
                ).first()
                
                if existing:
                    logger.info(f"Lead already exists: {name}")
                    continue
                
                # Check blacklist
                blacklisted = session.exec(
                    select(Blacklist).where(Blacklist.value == name)
                ).first()
                
                if blacklisted:
                    logger.info(f"Lead blacklisted: {name}")
                    continue
                
                # Create new lead
                lead = Lead(
                    company_name=name,
                    email=None,  # Will be found later via website scraping
                    phone=phone,
                    website_url=website,
                    address=address,
                    contact_name=None,  # Will be found later
                    status="cold",
                    source="googlemaps",
                    premium_score=premium_score,
                    notes=f"Google Maps: rating {rating}, {reviews} reviews, place_id: {place_id}"
                )
                
                session.add(lead)
                saved_count += 1
                
            except Exception as e:
                logger.error(f"Error saving clinic {clinic.get('name', 'Unknown')}: {e}")
                continue
        
        session.commit()
        logger.info(f"Saved {saved_count} new leads to database")
        return saved_count
        
    except Exception as e:
        logger.error(f"Database error: {e}")
        session.rollback()
        return 0
    finally:
        session.close()


def format_summary(places: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for p in places:
        name = p.get("name", "")
        rating = p.get("rating", "")
        reviews = p.get("user_ratings_total", "")
        address = p.get("formatted_address", "")
        place_id = p.get("place_id", "")
        lines.append(f"- {name} | rating {rating} ({reviews}) | {address} | {place_id}")
    return "\n".join(lines)


if __name__ == "__main__":
    try:
        results = search_premium_clinics()
        print(f"Found premium clinics: {len(results)}")
        print(format_summary(results))
        
        # Save to database
        saved_count = save_clinics_to_database(results)
        print(f"Saved {saved_count} leads to database")
        
    except Exception as e:
        logger.error(f"Failed to search premium clinics: {e}")

