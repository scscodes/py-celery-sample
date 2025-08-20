"""
Email Service Mock

Mock implementation of email service for testing and development.
Simulates various email providers with realistic behavior.
"""

import logging
import asyncio
import random
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class EmailServiceMock:
    """Mock email service implementation."""
    
    def __init__(self, provider: str = "sendgrid", failure_rate: float = 0.05):
        self.provider = provider
        self.failure_rate = failure_rate
        self.response_delay = (0.1, 2.0)  # Email send delay range
        
        # Mock email storage
        self._sent_emails = []
        self._bounced_emails = []
        self._delivery_status = {}
        
        # Performance metrics
        self._email_count = 0
        self._error_count = 0
        self._total_response_time = 0.0
        
        logger.info(f"EmailServiceMock initialized: {provider}")
    
    async def send_email(self, to_address: str, subject: str, body: str, 
                        from_address: str = "noreply@company.com", 
                        email_type: str = "text") -> Dict[str, Any]:
        """Send an email with realistic delivery simulation."""
        start_time = time.time()
        self._email_count += 1
        
        try:
            await self._simulate_delay()
            
            if self._should_fail():
                self._error_count += 1
                raise Exception(f"Email delivery failed: {self._generate_email_error()}")
            
            # Generate unique message ID
            message_id = str(uuid.uuid4())
            
            # Simulate delivery status
            delivery_status = self._simulate_delivery_status()
            
            # Store sent email
            email_record = {
                "message_id": message_id,
                "to_address": to_address,
                "from_address": from_address,
                "subject": subject,
                "body": body,
                "email_type": email_type,
                "sent_at": datetime.utcnow().isoformat(),
                "delivery_status": delivery_status,
                "provider": self.provider
            }
            
            self._sent_emails.append(email_record)
            self._delivery_status[message_id] = delivery_status
            
            # Simulate bounce for some emails
            if delivery_status == "bounced":
                self._bounced_emails.append(email_record)
            
            execution_time = time.time() - start_time
            self._total_response_time += execution_time
            
            result = {
                "message_id": message_id,
                "status": "sent",
                "delivery_status": delivery_status,
                "provider_response": f"{self.provider}_accepted",
                "execution_time_ms": execution_time * 1000
            }
            
            logger.info(f"Email sent: {message_id} to {to_address}")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._total_response_time += execution_time
            logger.error(f"Email send failed: {e}")
            raise
    
    async def send_bulk_email(self, recipients: List[str], subject: str, body: str,
                             from_address: str = "noreply@company.com") -> Dict[str, Any]:
        """Send bulk email to multiple recipients."""
        start_time = time.time()
        
        try:
            await self._simulate_delay(factor=len(recipients) * 0.1)
            
            if self._should_fail():
                raise Exception("Bulk email send failed: Rate limit exceeded")
            
            # Process each recipient
            successful_sends = []
            failed_sends = []
            
            for recipient in recipients:
                try:
                    result = await self.send_email(recipient, subject, body, from_address)
                    successful_sends.append({
                        "recipient": recipient,
                        "message_id": result["message_id"],
                        "status": "sent"
                    })
                except Exception as e:
                    failed_sends.append({
                        "recipient": recipient,
                        "error": str(e),
                        "status": "failed"
                    })
            
            execution_time = time.time() - start_time
            
            bulk_result = {
                "total_recipients": len(recipients),
                "successful_sends": len(successful_sends),
                "failed_sends": len(failed_sends),
                "success_rate": len(successful_sends) / len(recipients) if recipients else 0,
                "successful_emails": successful_sends,
                "failed_emails": failed_sends,
                "execution_time_ms": execution_time * 1000
            }
            
            logger.info(f"Bulk email sent: {len(successful_sends)}/{len(recipients)} successful")
            return bulk_result
            
        except Exception as e:
            logger.error(f"Bulk email send failed: {e}")
            raise
    
    async def get_delivery_status(self, message_id: str) -> Dict[str, Any]:
        """Get delivery status for a specific email."""
        await self._simulate_delay(factor=0.2)
        
        if message_id in self._delivery_status:
            # Simulate status updates over time
            current_status = self._delivery_status[message_id]
            
            # Some emails might change status
            if current_status == "sent" and random.random() < 0.1:
                current_status = random.choice(["delivered", "bounced", "opened"])
                self._delivery_status[message_id] = current_status
            
            return {
                "message_id": message_id,
                "status": current_status,
                "last_updated": datetime.utcnow().isoformat(),
                "provider": self.provider
            }
        else:
            return {
                "message_id": message_id,
                "status": "not_found",
                "error": "Message ID not found"
            }
    
    async def send_template_email(self, template_id: str, to_address: str, 
                                 template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send email using template with data substitution."""
        start_time = time.time()
        
        try:
            await self._simulate_delay()
            
            # Simulate template rendering
            rendered_subject = f"Template {template_id} - {template_data.get('subject', 'Default')}"
            rendered_body = f"Rendered template {template_id} with data: {template_data}"
            
            # Send the rendered email
            result = await self.send_email(
                to_address=to_address,
                subject=rendered_subject,
                body=rendered_body,
                email_type="template"
            )
            
            result["template_id"] = template_id
            result["template_data"] = template_data
            
            logger.info(f"Template email sent: {template_id} to {to_address}")
            return result
            
        except Exception as e:
            logger.error(f"Template email send failed: {e}")
            raise
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get email service performance metrics."""
        avg_response_time = (self._total_response_time / self._email_count) if self._email_count > 0 else 0
        
        # Calculate delivery statistics
        total_sent = len(self._sent_emails)
        delivered_count = sum(1 for email in self._sent_emails if email["delivery_status"] == "delivered")
        bounced_count = len(self._bounced_emails)
        
        return {
            "provider": self.provider,
            "total_emails_sent": self._email_count,
            "total_errors": self._error_count,
            "error_rate": (self._error_count / self._email_count) if self._email_count > 0 else 0,
            "avg_response_time_ms": avg_response_time * 1000,
            "delivery_rate": (delivered_count / total_sent) if total_sent > 0 else 0,
            "bounce_rate": (bounced_count / total_sent) if total_sent > 0 else 0,
            "emails_in_queue": total_sent,
            "recent_bounces": bounced_count
        }
    
    def get_sent_emails(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get list of recently sent emails."""
        return self._sent_emails[-limit:]
    
    def get_bounced_emails(self) -> List[Dict[str, Any]]:
        """Get list of bounced emails."""
        return self._bounced_emails.copy()
    
    def clear_email_history(self) -> None:
        """Clear all email history."""
        self._sent_emails.clear()
        self._bounced_emails.clear()
        self._delivery_status.clear()
        logger.info("Email history cleared")
    
    def set_failure_rate(self, rate: float) -> None:
        """Set the failure rate for email operations."""
        self.failure_rate = max(0.0, min(1.0, rate))
        logger.info(f"Email failure rate set to {self.failure_rate:.1%}")
    
    def set_response_delay(self, min_delay: float, max_delay: float) -> None:
        """Set response delay range."""
        self.response_delay = (min_delay, max_delay)
        logger.info(f"Email response delay set to {min_delay}-{max_delay}s")
    
    # Private methods
    
    async def _simulate_delay(self, factor: float = 1.0) -> None:
        """Simulate realistic email service response delay."""
        min_delay, max_delay = self.response_delay
        delay = random.uniform(min_delay, max_delay) * factor
        await asyncio.sleep(delay)
    
    def _should_fail(self) -> bool:
        """Determine if operation should fail based on configured rate."""
        return random.random() < self.failure_rate
    
    def _simulate_delivery_status(self) -> str:
        """Simulate realistic email delivery status."""
        statuses = [
            ("delivered", 0.85),   # 85% delivered
            ("bounced", 0.05),     # 5% bounced
            ("sent", 0.08),        # 8% still sending
            ("spam", 0.02)         # 2% marked as spam
        ]
        
        rand = random.random()
        cumulative = 0.0
        
        for status, probability in statuses:
            cumulative += probability
            if rand <= cumulative:
                return status
        
        return "delivered"  # Default
    
    def _generate_email_error(self) -> str:
        """Generate realistic email service error messages."""
        errors = [
            "Invalid recipient address",
            "Rate limit exceeded",
            "SMTP server timeout",
            "Authentication failed",
            "Message size too large",
            "Spam filter rejection",
            "Mailbox full",
            "Domain not found",
            "Connection refused",
            "Service temporarily unavailable"
        ]
        return random.choice(errors)
