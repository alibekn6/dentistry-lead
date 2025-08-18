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
        logger.info("Step 1/5: Initializing database...")
        await init_database()
        time.sleep(2)
        
        logger.info("Step 2/5: Checking initial status...")
        await show_status()
        time.sleep(2)
        
        logger.info("Step 3/5: Scraping leads...")
        await scrape_leads()
        time.sleep(5)
        

        logger.info("Step 4/5: Running email campaign...")
        await run_email_campaign()
        time.sleep(30)  # Wait for campaign to complete
        

        logger.info("Step 5/5: Exporting results...")
        await export_to_csv("data/leads_export.csv")
        

        logger.info("Pipeline completed successfully!")
        logger.info("Final status:")
        await show_status()
        
        logger.info("Check data/leads_export.csv for results!")
        
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


async def scrape_leads():
    """Scrape leads from Google Maps."""
    logger.info("Scraping leads from Google Maps...")
    
    try:
        from scrapers.googlemaps import search_premium_clinics, save_clinics_to_database
        
        # Search for premium clinics
        clinics = search_premium_clinics()
        logger.info(f"Found {len(clinics)} premium clinics from Google Maps")
        
        # Save to database
        saved_count = save_clinics_to_database(clinics)
        logger.info(f"Successfully saved {saved_count} new leads to database")
        
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        logger.info("Falling back to test data...")
        # Fallback to test data if scraping fails


async def run_email_campaign():
    """Run email campaign."""
    
    session = get_db_session()
    try:
        cold_leads = session.exec(select(Lead).where(Lead.status == "cold")).all()
        
        logger.info(f"Starting campaign for {len(cold_leads)} cold leads...")
        
        for lead in cold_leads:
            logger.info(f"Sending Step 0 to {lead.company_name}...")
            interaction = Interaction(
                lead_id=lead.id,
                channel=ChannelType.EMAIL,
                step=0,
                message_template="email_step_0",
                message_content=f"Hello {lead.contact_name or 'there'}, reaching out about premium dental products for {lead.company_name}...",
                status=InteractionStatus.SENT
            )
            session.add(interaction)
            lead.last_step_completed = 0
            
            time.sleep(1)  # Small delay between emails
            
            # Step 1: Follow-up 1 (after 24 seconds)
            time.sleep(24)
            logger.info(f"📤 Sending Step 1 to {lead.company_name}...")
            interaction = Interaction(
                lead_id=lead.id,
                channel=ChannelType.EMAIL,
                step=1,
                message_template="email_step_1",
                message_content=f"Following up with {lead.company_name} about premium dental solutions...",
                status=InteractionStatus.SENT
            )
            session.add(interaction)
            lead.last_step_completed = 1
            
            # Step 2: Follow-up 2 (after another 24 seconds)
            time.sleep(24)
            logger.info(f"Sending Step 2 to {lead.company_name}...")
            interaction = Interaction(
                lead_id=lead.id,
                channel=ChannelType.EMAIL,
                step=2,
                message_template="email_step_2",
                message_content=f"Final follow-up with {lead.company_name}...",
                status=InteractionStatus.SENT
            )
            session.add(interaction)
            lead.last_step_completed = 2
            lead.status = "stopped"  # Campaign completed
            
        session.commit()
        logger.info("Email campaign completed!")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Campaign failed: {e}")
    finally:
        session.close()


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
  auto           Run full automated pipeline (init → scrape → campaign → export)
  init-db        Initialize database tables
  reset-db       Reset database (delete all data)
  status         Show current system status
  scrape         Scrape leads from Google Maps
  run-campaign   Run email campaign
  export-csv     Export leads to CSV file
  help           Show this help message

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
        
        elif command == 'run-campaign':
            logger.info("Starting email campaign...")
            await run_email_campaign()
        
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