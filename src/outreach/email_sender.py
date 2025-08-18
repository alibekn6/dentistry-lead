"""
Email sender module for dental practice lead generation campaigns.
Handles SMTP connection, template rendering, and email delivery tracking.
"""

import smtplib
import logging
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

from config import settings
from models import Lead, Interaction, ChannelType, InteractionStatus
from database import get_db_session

logger = logging.getLogger(__name__)


class EmailSender:
    """Handles email sending for dental practice outreach campaigns."""
    
    def __init__(self):
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
        self.from_email = settings.from_email
        self.seller_name = settings.seller_name
        self.company_name = settings.company_name
        self.test_mode = settings.test_mode
        
        # Templates directory
        self.templates_dir = Path(__file__).parent / "templates"
        
        if not self.from_email or not self.smtp_user or not self.smtp_password:
            logger.warning("⚠️  Email credentials not configured. Check your .env file.")
    
    def load_template(self, step: int) -> Optional[str]:
        """Load email template for specific step."""
        template_path = self.templates_dir / f"email_step_{step}.txt"
        
        try:
            if template_path.exists():
                return template_path.read_text(encoding='utf-8')
            else:
                logger.error(f"Template not found: {template_path}")
                return None
        except Exception as e:
            logger.error(f"Error loading template {template_path}: {e}")
            return None
    
    def render_template(self, template: str, lead: Lead, step: int) -> Tuple[str, str]:
        """Render email template with lead data."""
        
        # Extract location from address if available
        location = "London"
        if lead.address:
            if "Harley" in lead.address:
                location = "Harley Street"
            elif "Kensington" in lead.address:
                location = "Kensington"
            elif "Chelsea" in lead.address:
                location = "Chelsea"
            elif "Mayfair" in lead.address:
                location = "Mayfair"
        
        # Template variables
        variables = {
            'seller_name': self.seller_name,
            'company_name': self.company_name,
            'lead_company_name': lead.company_name,
            'location': location,
            'email': lead.email,
            'phone': lead.phone or 'not provided',
            'website': lead.website_url or 'not available',
            'step': step
        }
        
        # Render template
        rendered = template
        for key, value in variables.items():
            placeholder = '{' + key + '}'
            rendered = rendered.replace(placeholder, str(value))
        
        # Extract subject and body
        lines = rendered.strip().split('\n')
        subject_line = ""
        body_lines = []
        
        for i, line in enumerate(lines):
            if line.startswith('Subject: '):
                subject_line = line[9:]  # Remove "Subject: "
            elif i > 0 and not line.startswith('Subject: '):  # Skip subject line
                body_lines.append(line)
        
        subject = subject_line if subject_line else f"Partnership Opportunity - {lead.company_name}"
        body = '\n'.join(body_lines).strip()
        
        return subject, body
    
    def create_email_message(self, to_email: str, subject: str, body: str) -> MIMEMultipart:
        """Create email message with proper headers."""
        
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{self.seller_name} <{self.from_email}>"
        msg['To'] = to_email
        msg['Subject'] = Header(subject, 'utf-8')
        
        # Add headers to improve deliverability
        msg['Reply-To'] = self.from_email
        msg['Return-Path'] = self.from_email
        msg['X-Mailer'] = f"{self.company_name} Lead Generation System"
        
        # Plain text version
        text_part = MIMEText(body, 'plain', 'utf-8')
        msg.attach(text_part)
        
        # HTML version (optional, better formatting)
        html_body = body.replace('\n', '<br>\n')
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        {html_body}
        </body>
        </html>
        """
        html_part = MIMEText(html_body, 'html', 'utf-8')
        msg.attach(html_part)
        
        return msg
    
    def send_email(self, lead: Lead, step: int) -> Dict[str, any]:
        """Send email to a specific lead."""
        
        if not lead.email:
            return {
                'success': False,
                'error': 'Lead has no email address',
                'lead_id': str(lead.id)
            }
        
        try:
            # Load and render template
            template = self.load_template(step)
            if not template:
                return {
                    'success': False,
                    'error': f'Template for step {step} not found',
                    'lead_id': str(lead.id)
                }
            
            subject, body = self.render_template(template, lead, step)
            
            # Create email message
            msg = self.create_email_message(lead.email, subject, body)
            
            if self.test_mode:
                logger.info(f"🧪 TEST MODE - Would send email to {lead.email}")
                logger.info(f"   Subject: {subject}")
                logger.info(f"   Preview: {body[:100]}...")
                
                # Still create interaction record for testing
                self._create_interaction_record(lead, step, subject, body, 'sent')
                
                return {
                    'success': True,
                    'test_mode': True,
                    'lead_id': str(lead.id),
                    'email': lead.email,
                    'subject': subject
                }
            
            # Send actual email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                
                # Send message
                text = msg.as_string()
                server.sendmail(self.from_email, [lead.email], text)
                
                logger.info(f"✅ Email sent successfully to {lead.email}")
                
                # Create interaction record
                self._create_interaction_record(lead, step, subject, body, 'sent')
                
                return {
                    'success': True,
                    'lead_id': str(lead.id),
                    'email': lead.email,
                    'subject': subject
                }
        
        except Exception as e:
            logger.error(f"❌ Failed to send email to {lead.email}: {e}")
            
            # Create failed interaction record
            self._create_interaction_record(lead, step, subject if 'subject' in locals() else 'Unknown', 
                                          body if 'body' in locals() else 'Unknown', 'failed', str(e))
            
            return {
                'success': False,
                'error': str(e),
                'lead_id': str(lead.id),
                'email': lead.email
            }
    
    def _create_interaction_record(self, lead: Lead, step: int, subject: str, 
                                 body: str, status: str, error_message: str = None):
        """Create interaction record in database."""
        
        try:
            session = get_db_session()
            
            interaction = Interaction(
                lead_id=lead.id,
                channel=ChannelType.EMAIL,
                step=step,
                message_template=f"email_step_{step}",
                message_content=f"Subject: {subject}\n\n{body}",
                sent_at=datetime.utcnow(),
                status=InteractionStatus.SENT if status == 'sent' else InteractionStatus.FAILED,
                error_message=error_message
            )
            
            session.add(interaction)
            session.commit()
            session.refresh(interaction)
            
            # Update lead's last step completed (get fresh instance from this session)
            if status == 'sent':
                fresh_lead = session.get(Lead, lead.id)
                if fresh_lead:
                    fresh_lead.last_step_completed = step
                    session.add(fresh_lead)
                    session.commit()
            
            session.close()
            
        except Exception as e:
            logger.error(f"Failed to create interaction record: {e}")
    
    def send_campaign_batch(self, leads: List[Lead], step: int, 
                          delay_seconds: float = 5.0) -> Dict[str, any]:
        """Send email campaign to a batch of leads."""
        
        results = {
            'total_leads': len(leads),
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
        
        logger.info(f"📧 Starting email campaign batch for {len(leads)} leads (Step {step})")
        
        for i, lead in enumerate(leads, 1):
            try:
                logger.info(f"📤 Sending {i}/{len(leads)}: {lead.company_name} -> {lead.email}")
                
                result = self.send_email(lead, step)
                
                if result['success']:
                    results['successful'] += 1
                    if result.get('test_mode'):
                        logger.info(f"   🧪 Test mode - {result['subject']}")
                    else:
                        logger.info(f"   ✅ Sent successfully")
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'lead': lead.company_name,
                        'email': lead.email,
                        'error': result['error']
                    })
                    logger.error(f"   ❌ Failed: {result['error']}")
                
                # Delay between emails to avoid being flagged as spam
                if i < len(leads):
                    logger.info(f"   ⏳ Waiting {delay_seconds}s before next email...")
                    time.sleep(delay_seconds)
                
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'lead': lead.company_name,
                    'email': getattr(lead, 'email', 'Unknown'),
                    'error': str(e)
                })
                logger.error(f"   ❌ Unexpected error: {e}")
                continue
        
        # Final summary
        logger.info(f"\n📊 Campaign Batch Complete!")
        logger.info(f"   ✅ Successful: {results['successful']}")
        logger.info(f"   ❌ Failed: {results['failed']}")
        logger.info(f"   📝 Total processed: {results['total_leads']}")
        
        success_rate = (results['successful'] / results['total_leads'] * 100) if results['total_leads'] > 0 else 0
        logger.info(f"   📈 Success rate: {success_rate:.1f}%")
        
        return results


def test_email_config() -> bool:
    """Test email configuration."""
    
    sender = EmailSender()
    
    if not sender.from_email:
        logger.error("❌ From email not configured")
        return False
    
    if not sender.smtp_user:
        logger.error("❌ SMTP user not configured")
        return False
    
    if not sender.smtp_password:
        logger.error("❌ SMTP password not configured")
        return False
    
    logger.info("✅ Email configuration looks good")
    return True


if __name__ == "__main__":
    # Test email configuration
    print("🧪 Testing email configuration...")
    
    if test_email_config():
        print("✅ Email system ready!")
    else:
        print("❌ Email configuration incomplete. Check your .env file.")
