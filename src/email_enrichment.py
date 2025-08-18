"""
Email enrichment module for finding email addresses on lead websites.
Automatically scans websites and updates the database with found emails.
"""

import re
import time
import logging
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

from sqlmodel import select, Session
from database import get_db_session
from models import Lead
from scrapers.website import scrape_website_for_emails

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def validate_email(email: str) -> bool:
    """Validate if email address is properly formatted."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def is_generic_email(email: str) -> bool:
    """Check if email is generic/automated (lower priority)."""
    generic_prefixes = [
        'noreply', 'no-reply', 'donotreply', 'do-not-reply',
        'automated', 'system', 'bot', 'mailer', 'daemon',
        'postmaster', 'webmaster', 'admin'
    ]
    
    local_part = email.split('@')[0].lower()
    return any(prefix in local_part for prefix in generic_prefixes)


def choose_best_email(emails: List[str]) -> Optional[str]:
    """Choose the best email from a list of found emails."""
    if not emails:
        return None
    
    # Filter valid emails
    valid_emails = [email for email in emails if validate_email(email)]
    if not valid_emails:
        return None
    
    # Prioritize non-generic emails
    non_generic = [email for email in valid_emails if not is_generic_email(email)]
    if non_generic:
        return non_generic[0]
    
    # Fallback to any valid email
    return valid_emails[0]


def generate_standard_emails(website_url: str) -> List[str]:
    """Generate standard email patterns based on domain."""
    try:
        domain = urlparse(website_url).netloc
        if domain.startswith('www.'):
            domain = domain[4:]
        
        standard_patterns = [
            f"info@{domain}",
            f"contact@{domain}",
            f"hello@{domain}",
            f"enquiries@{domain}",
            f"appointments@{domain}",
            f"reception@{domain}",
            f"admin@{domain}"
        ]
        
        return standard_patterns
    except Exception as e:
        logger.warning(f"Could not generate standard emails for {website_url}: {e}")
        return []


async def enrich_leads_with_emails(
    limit: Optional[int] = None,
    delay_seconds: float = 2.0,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Enrich leads with email addresses by scraping their websites.
    
    Args:
        limit: Maximum number of leads to process (None = all)
        delay_seconds: Delay between website requests
        dry_run: If True, don't update database
    
    Returns:
        Dictionary with statistics
    """
    
    stats = {
        'processed': 0,
        'emails_found': 0,
        'emails_updated': 0,
        'errors': 0,
        'skipped': 0
    }
    
    session = get_db_session()
    
    try:
        # Find leads with website but no email
        query = select(Lead).where(
            Lead.website_url.isnot(None),
            Lead.email.is_(None)
        )
        
        if limit:
            query = query.limit(limit)
            
        leads_to_process = session.exec(query).all()
        total_leads = len(leads_to_process)
        
        logger.info(f"🔍 Found {total_leads} leads to enrich with emails")
        
        if dry_run:
            logger.info("🧪 DRY RUN MODE - No database changes will be made")
        
        for i, lead in enumerate(leads_to_process, 1):
            try:
                logger.info(f"📧 Processing {i}/{total_leads}: {lead.company_name}")
                logger.info(f"   Website: {lead.website_url}")
                
                # Extract emails from website
                result = scrape_website_for_emails(lead.website_url)
                found_emails = result.get('emails', [])
                stats['processed'] += 1
                
                if found_emails:
                    best_email = choose_best_email(found_emails)
                    
                    if best_email:
                        logger.info(f"   ✅ Found email: {best_email}")
                        stats['emails_found'] += 1
                        
                        if not dry_run:
                            lead.email = best_email
                            session.add(lead)
                            session.commit()
                            session.refresh(lead)
                            stats['emails_updated'] += 1
                            logger.info(f"   💾 Updated database")
                        else:
                            logger.info(f"   🧪 Would update with: {best_email}")
                    else:
                        logger.info(f"   ⚠️  Found emails but none suitable: {found_emails}")
                        stats['skipped'] += 1
                else:
                    logger.info(f"   ❌ No emails found on website")
                    
                    # Generate standard email suggestions
                    standard_emails = generate_standard_emails(lead.website_url)
                    if standard_emails:
                        logger.info(f"   💡 Suggestions: {standard_emails[:3]}")
                    
                    stats['skipped'] += 1
                
                # Delay between requests to be respectful
                if i < total_leads:  # Don't delay after last request
                    time.sleep(delay_seconds)
                
            except Exception as e:
                logger.error(f"   ❌ Error processing {lead.company_name}: {e}")
                stats['errors'] += 1
                continue
        
        # Final statistics
        logger.info(f"\n📊 Email Enrichment Complete!")
        logger.info(f"   • Processed: {stats['processed']}")
        logger.info(f"   • Emails found: {stats['emails_found']}")
        logger.info(f"   • Database updated: {stats['emails_updated']}")
        logger.info(f"   • Skipped: {stats['skipped']}")
        logger.info(f"   • Errors: {stats['errors']}")
        
        success_rate = (stats['emails_found'] / stats['processed'] * 100) if stats['processed'] > 0 else 0
        logger.info(f"   • Success rate: {success_rate:.1f}%")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Database error during email enrichment: {e}")
        stats['errors'] += 1
    finally:
        session.close()
    
    return stats


async def enrich_single_lead(lead_id: str, dry_run: bool = False) -> Dict[str, Any]:
    """Enrich a single lead with email for testing purposes."""
    
    session = get_db_session()
    
    try:
        lead = session.get(Lead, lead_id)
        if not lead:
            return {"error": "Lead not found"}
        
        if not lead.website_url:
            return {"error": "Lead has no website URL"}
        
        if lead.email and not dry_run:
            return {"error": "Lead already has email", "current_email": lead.email}
        
        logger.info(f"🔍 Testing email extraction for: {lead.company_name}")
        logger.info(f"   Website: {lead.website_url}")
        
        # Extract emails
        result = scrape_website_for_emails(lead.website_url)
        found_emails = result.get('emails', [])
        best_email = choose_best_email(found_emails) if found_emails else None
        
        result = {
            "lead_name": lead.company_name,
            "website": lead.website_url,
            "found_emails": found_emails,
            "best_email": best_email,
            "updated": False
        }
        
        if best_email and not dry_run:
            lead.email = best_email
            session.add(lead)
            session.commit()
            session.refresh(lead)
            result["updated"] = True
            logger.info(f"   ✅ Updated with: {best_email}")
        elif best_email:
            logger.info(f"   🧪 Would update with: {best_email}")
        else:
            logger.info(f"   ❌ No suitable email found")
            # Add suggestions
            standard_emails = generate_standard_emails(lead.website_url)
            result["suggestions"] = standard_emails[:3]
        
        return result
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error enriching single lead: {e}")
        return {"error": str(e)}
    finally:
        session.close()


if __name__ == "__main__":
    import asyncio
    
    print("🧪 Testing email enrichment on first 3 leads...")
    result = asyncio.run(enrich_leads_with_emails(limit=3, dry_run=True))
    print(f"\nTest completed: {result}")
