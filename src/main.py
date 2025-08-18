import sys
import asyncio
import logging
from typing import Optional
import time
import csv
import os
from database import create_tables, get_db_session
from models import Lead, Interaction, Blacklist, ChannelType, InteractionStatus
from sqlmodel import select

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_auto_pipeline():
    try:
        # Step 1: Ensure tables exist
        logger.info("Step 1/5: Preparing database tables...")
        create_tables()
        time.sleep(1)

        # Step 2: Scrape and save a small batch quickly
        logger.info("Step 2/5: Scraping premium clinics from Google Maps (quick batch)...")
        await quick_scrape_and_save(limit=10)
        time.sleep(1)

        # Step 3: Enrich newly saved leads with emails
        logger.info("Step 3/5: Enriching leads with website emails...")
        await enrich_emails_command(limit=None)
        time.sleep(1)

        # Step 4: Send Step 0 campaign emails to leads with emails
        logger.info("Step 4/5: Sending Step 0 email campaign...")
        await run_email_campaign(step=0, limit=None)
        time.sleep(1)

        # Step 5: Export current leads snapshot
        logger.info("Step 5/5: Exporting results to CSV...")
        await export_to_csv("data/leads_export.csv")

        logger.info("✅ Pipeline completed successfully!")
        logger.info("Final status:")
        await show_status()
        logger.info("➡️ Check data/leads_export.csv for results")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        logger.info("Current status:")
        try:
            await show_status()
        except:
            pass


async def init_database():
    """Initialize database with tables and test data."""
    
    logger.info("Creating database tables...")
    create_tables()
    
    # Add test data
    session = get_db_session()
    try:
        # Add test leads
        test_leads = [
            Lead(
                company_name="London Premium Dental",
                email="info@londonpremiumdental.co.uk",
                phone="+44 20 7123 4567",
                website_url="https://londonpremiumdental.co.uk",
                address="123 Harley Street, London W1G 6BA",
                contact_name="Dr. James Smith",
                premium_score=9
            ),
            Lead(
                company_name="Elite Dental Clinic",
                email="contact@elitedental.london",
                phone="+44 20 7234 5678",
                website_url="https://elitedental.london",
                address="456 Wimpole Street, London W1G 8YA",
                contact_name="Dr. Sarah Johnson",
                premium_score=8
            ),
            Lead(
                company_name="Boutique Dental Care",
                email="hello@boutiquedental.co.uk",
                phone="+44 20 7345 6789",
                website_url="https://boutiquedental.co.uk",
                address="789 Portland Place, London W1B 1NT",
                contact_name="Dr. Michael Brown",
                premium_score=7
            )
        ]
        
        for lead in test_leads:
            session.add(lead)
        
        # Add blacklist entries
        blacklist_entries = [
            Blacklist(type="domain", value="example.com", reason="Test domain"),
            Blacklist(type="company_name", value="Generic Dental", reason="Not premium")
        ]
        
        for entry in blacklist_entries:
            session.add(entry)
            
        session.commit()
        logger.info("Database initialized with test data!")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to add test data: {e}")
    finally:
        session.close()


async def reset_database():
    """Reset database (delete all data)."""
    session = get_db_session()
    try:
        # Delete in order due to foreign key constraints
        interactions = session.exec(select(Interaction)).all()
        for interaction in interactions:
            session.delete(interaction)
            
        leads = session.exec(select(Lead)).all()
        for lead in leads:
            session.delete(lead)
            
        blacklist_entries = session.exec(select(Blacklist)).all()
        for entry in blacklist_entries:
            session.delete(entry)
            
        session.commit()
        logger.info("Database reset successfully!")
    except Exception as e:
        session.rollback()
        logger.error(f"Error resetting database: {e}")
    finally:
        session.close()


async def show_status():
    """Show system status."""
    
    session = get_db_session()
    try:
        leads = session.exec(select(Lead)).all()
        interactions = session.exec(select(Interaction)).all()
        
        logger.info(f"System Status:")
        logger.info(f"  • Total leads: {len(leads)}")
        logger.info(f"  • Total interactions: {len(interactions)}")
        
        # Status breakdown
        status_counts = {}
        for lead in leads:
            status_counts[lead.status] = status_counts.get(lead.status, 0) + 1
        
        if status_counts:
            logger.info(f"  • Lead status breakdown:")
            for status, count in status_counts.items():
                logger.info(f"    - {status}: {count}")
                
    except Exception as e:
        logger.error(f"Error getting status: {e}")
    finally:
        session.close()


async def test_scrape_leads(limit: int = 5):
    """Test scraping with a small limit."""
    logger.info(f"Testing Google Maps scraping with limit {limit}...")
    
    try:
        from scrapers.googlemaps import search_premium_clinics
        
        # Search with small limit for testing
        clinics = search_premium_clinics(max_results=limit)
        logger.info(f"Found {len(clinics)} premium clinics from Google Maps")
        
        # Show sample results
        for i, clinic in enumerate(clinics[:3]):
            name = clinic.get('name', 'Unknown')
            website = clinic.get('website', 'No website')
            phone = clinic.get('formatted_phone_number', 'No phone')
            logger.info(f"  {i+1}. {name}")
            logger.info(f"     Website: {website}")
            logger.info(f"     Phone: {phone}")
        
        return clinics
        
    except Exception as e:
        logger.error(f"Error during test scraping: {e}")
        return []


async def quick_scrape_and_save(limit: int = 20):
    """Quick scraping and saving to database with limit."""
    logger.info(f"Quick scraping {limit} leads and saving to database...")
    
    try:
        from scrapers.googlemaps import search_premium_clinics, save_clinics_to_database
        
        # Search with specified limit
        logger.info(f"🔍 Scraping up to {limit} premium clinics...")
        clinics = search_premium_clinics(max_results=limit)
        logger.info(f"📊 Found {len(clinics)} premium clinics from Google Maps")
        
        if clinics:
            # Save to database
            logger.info("💾 Saving to database...")
            saved_count = save_clinics_to_database(clinics)
            logger.info(f"✅ Successfully saved {saved_count} new leads to database")
            
            # Show quick stats
            with_website = sum(1 for c in clinics if c.get('website'))
            with_phone = sum(1 for c in clinics if c.get('formatted_phone_number'))
            
            logger.info(f"📈 Quick Stats:")
            logger.info(f"   • Total scraped: {len(clinics)}")
            logger.info(f"   • Saved to DB: {saved_count}")
            logger.info(f"   • With website: {with_website}")
            logger.info(f"   • With phone: {with_phone}")
            
            # Show first few examples
            logger.info(f"🎯 Sample results:")
            for i, clinic in enumerate(clinics[:3]):
                name = clinic.get('name', 'Unknown')
                website = clinic.get('website', 'No website')
                phone = clinic.get('formatted_phone_number', 'No phone')
                logger.info(f"   {i+1}. {name}")
                logger.info(f"      Website: {website}")
                logger.info(f"      Phone: {phone}")
        else:
            logger.warning("No clinics found!")
        
        return clinics
        
    except Exception as e:
        logger.error(f"Error during quick scraping: {e}")
        return []


async def enrich_emails_command(limit: Optional[int] = None):
    """Command to enrich leads with email addresses."""
    try:
        from email_enrichment import enrich_leads_with_emails
        
        logger.info(f"📧 Starting email enrichment process...")
        if limit:
            logger.info(f"   Limiting to {limit} leads")
        
        # Run enrichment
        stats = await enrich_leads_with_emails(
            limit=limit,
            delay_seconds=2.0,  # 2 second delay between requests
            dry_run=False
        )
        
        logger.info(f"✅ Email enrichment completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during email enrichment: {e}")


async def test_single_email(lead_id: str):
    """Test email extraction for a single lead."""
    try:
        from email_enrichment import enrich_single_lead
        
        logger.info(f"🧪 Testing email extraction for lead ID: {lead_id}")
        
        result = await enrich_single_lead(lead_id, dry_run=True)
        
        if "error" in result:
            logger.error(f"❌ {result['error']}")
        else:
            logger.info(f"✅ Test completed for {result['lead_name']}")
            if result.get('found_emails'):
                logger.info(f"   Found emails: {result['found_emails']}")
                logger.info(f"   Best email: {result['best_email']}")
            else:
                logger.info(f"   No emails found")
                if result.get('suggestions'):
                    logger.info(f"   Suggestions: {result['suggestions']}")
        
    except Exception as e:
        logger.error(f"Error testing email extraction: {e}")


async def scrape_leads():
    """Scrape leads from Google Maps."""
    logger.info("Scraping leads from Google Maps...")
    
    try:
        from scrapers.googlemaps import search_premium_clinics, save_clinics_to_database
        from config import settings
        
        # Search for premium clinics with limit
        max_results = settings.max_leads_per_scraping
        logger.info(f"Scraping up to {max_results} premium clinics...")
        clinics = search_premium_clinics(max_results=max_results)
        logger.info(f"Found {len(clinics)} premium clinics from Google Maps")
        
        # Save to database
        saved_count = save_clinics_to_database(clinics)
        logger.info(f"Successfully saved {saved_count} new leads to database")
        
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        logger.info("Falling back to test data...")
        # Fallback to test data if scraping fails


async def test_email_configuration():
    """Test email configuration and SMTP connection."""
    try:
        from outreach.email_sender import test_email_config
        
        logger.info("🔧 Testing email configuration...")
        
        if test_email_config():
            logger.info("✅ Email configuration is valid!")
            logger.info("📧 Ready to send emails")
        else:
            logger.error("❌ Email configuration incomplete")
            logger.info("💡 Please check your .env file and update:")
            logger.info("   - SMTP_HOST, SMTP_PORT")
            logger.info("   - SMTP_USER, SMTP_PASSWORD")
            logger.info("   - FROM_EMAIL")
        
    except Exception as e:
        logger.error(f"Error testing email config: {e}")


async def send_test_email(lead_id: str, step: int = 0):
    """Send a test email to a specific lead."""
    try:
        from outreach.email_sender import EmailSender
        
        session = get_db_session()
        lead = session.get(Lead, lead_id)
        
        if not lead:
            logger.error(f"❌ Lead not found: {lead_id}")
            return
        
        if not lead.email:
            logger.error(f"❌ Lead has no email address: {lead.company_name}")
            return
        
        logger.info(f"📧 Sending test email to {lead.company_name} ({lead.email})")
        logger.info(f"   Using template step: {step}")
        
        sender = EmailSender()
        result = sender.send_email(lead, step)
        
        if result['success']:
            if result.get('test_mode'):
                logger.info(f"🧪 Test email prepared successfully!")
                logger.info(f"   Subject: {result['subject']}")
            else:
                logger.info(f"✅ Email sent successfully!")
        else:
            logger.error(f"❌ Failed to send email: {result['error']}")
        
        session.close()
        
    except Exception as e:
        logger.error(f"Error sending test email: {e}")


async def run_email_campaign(step: int = 0, limit: Optional[int] = None):
    """Run email campaign for leads."""
    try:
        from outreach.email_sender import EmailSender
        from sqlmodel import select
        
        session = get_db_session()
        
        # Get leads with email addresses that haven't completed this step
        query = select(Lead).where(
            Lead.email.isnot(None),
            Lead.status == 'COLD'  # Only send to cold leads
        )
        
        if step > 0:
            # For follow-up emails, only send to leads who completed previous step
            query = query.where(Lead.last_step_completed >= step - 1)
        
        if limit:
            query = query.limit(limit)
        
        leads = session.exec(query).all()
        
        if not leads:
            logger.warning(f"No leads found for email campaign step {step}")
            return
        
        logger.info(f"📧 Starting email campaign:")
        logger.info(f"   Step: {step}")
        logger.info(f"   Leads: {len(leads)}")
        
        # Initialize sender and run campaign
        sender = EmailSender()
        results = sender.send_campaign_batch(leads, step, delay_seconds=5.0)
        
        # Summary
        logger.info(f"\n🎯 Campaign Results:")
        logger.info(f"   ✅ Successful: {results['successful']}")
        logger.info(f"   ❌ Failed: {results['failed']}")
        logger.info(f"   📊 Success Rate: {results['successful']/results['total_leads']*100:.1f}%")
        
        if results['errors']:
            logger.info(f"\n❌ Errors encountered:")
            for error in results['errors'][:5]:  # Show first 5 errors
                logger.info(f"   • {error['lead']}: {error['error']}")
        
        session.close()
        
    except Exception as e:
        logger.error(f"Error running email campaign: {e}")


async def export_to_csv(output_path):
    """Export leads to CSV."""
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    session = get_db_session()
    try:
        leads = session.exec(select(Lead)).all()
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'company_name', 'email', 'phone', 'instagram_url', 
                'contact_name', 'status', 'last_step_completed'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for lead in leads:
                writer.writerow({
                    'company_name': lead.company_name,
                    'email': lead.email,
                    'phone': lead.phone,
                    'instagram_url': lead.instagram_url,
                    'contact_name': lead.contact_name,
                    'status': lead.status,
                    'last_step_completed': lead.last_step_completed
                })
        
        logger.info(f"Exported {len(leads)} leads to {output_path}")
        
    except Exception as e:
        logger.error(f"Export failed: {e}")
    finally:
        session.close()


def show_help():
    """Show available commands."""
    print("""
🦷 Dentistry Lead Generation System
===================================

Available commands:
  auto             Run full automated pipeline (init → scrape → campaign → export)
  init-db          Initialize database tables
  reset-db         Reset database (delete all data)
  status           Show current system status
  scrape           Scrape leads from Google Maps (limited by config)
  test-scrape      Test scraping with small limit (usage: test-scrape [limit])
  quick-scrape     Quick scrape and save to DB (usage: quick-scrape [limit])
  enrich-emails    Find and add email addresses to leads (usage: enrich-emails [limit])
  test-email       Test email extraction for single lead (usage: test-email <lead_id>)
  run-campaign     Run email campaign (usage: run-campaign [step] [limit])
  test-email-config Test email/SMTP configuration
  send-test-email  Send test email to lead (usage: send-test-email <lead_id> [step])
  export-csv       Export leads to CSV file
  help             Show this help message

Usage:
  python src/main.py <command>
  
Examples:
  python src/main.py init-db
  python src/main.py scrape
  python src/main.py run-campaign
  python src/main.py export-csv
""")


async def main():
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    try:
        if command in ['help', '--help', '-h']:
            show_help()
        
        elif command == 'auto':
            logger.info("Starting full automated pipeline...")
            await run_auto_pipeline()
        
        elif command == 'init-db':
            logger.info("Initializing database...")
            await init_database()
        
        elif command == 'reset-db':
            logger.info("Resetting database...")
            await reset_database()
        
        elif command == 'status':
            logger.info("Getting system status...")
            await show_status()
        
        elif command == 'scrape':
            logger.info("Starting lead scraping...")
            await scrape_leads()
        
        elif command == 'test-scrape':
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5
            logger.info(f"Testing scraping with limit of {limit}...")
            await test_scrape_leads(limit)
        
        elif command == 'quick-scrape':
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
            logger.info(f"Quick scraping and saving {limit} leads...")
            await quick_scrape_and_save(limit)
        
        elif command == 'enrich-emails':
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
            logger.info("Starting email enrichment...")
            await enrich_emails_command(limit)
        
        elif command == 'test-email':
            lead_id = sys.argv[2] if len(sys.argv) > 2 else None
            if not lead_id:
                logger.error("Usage: test-email <lead_id>")
                return
            await test_single_email(lead_id)
        
        elif command == 'run-campaign':
            step = int(sys.argv[2]) if len(sys.argv) > 2 else 0
            limit = int(sys.argv[3]) if len(sys.argv) > 3 else None
            logger.info(f"Starting email campaign step {step}...")
            await run_email_campaign(step, limit)
        
        elif command == 'test-email-config':
            logger.info("Testing email configuration...")
            await test_email_configuration()
        
        elif command == 'send-test-email':
            lead_id = sys.argv[2] if len(sys.argv) > 2 else None
            step = int(sys.argv[3]) if len(sys.argv) > 3 else 0
            if not lead_id:
                logger.error("Usage: send-test-email <lead_id> [step]")
                return
            await send_test_email(lead_id, step)
        
        elif command == 'export-csv':
            output_file = sys.argv[2] if len(sys.argv) > 2 else 'data/leads_export.csv'
            logger.info(f"Exporting leads to {output_file}...")
            await export_to_csv(output_file)
        
        else:
            logger.error(f"Unknown command: {command}")
            show_help()
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("⏹️ Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error executing command '{command}': {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())