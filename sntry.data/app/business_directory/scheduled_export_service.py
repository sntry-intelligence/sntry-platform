"""
Scheduled Export Service for Automated Reporting
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os

from app.core.config import settings
from app.business_directory.export_service import ExportService

logger = logging.getLogger(__name__)


class ScheduledExportService:
    """Service for managing scheduled exports and automated reporting"""
    
    def __init__(self, db: Session):
        self.db = db
        self.export_service = ExportService(db)
    
    def generate_daily_report(self) -> Dict[str, Any]:
        """Generate daily business intelligence report"""
        try:
            logger.info("Generating daily report")
            
            # Get dashboard data
            dashboard_data = self.export_service.export_dashboard_data_to_json()
            
            # Generate qualified leads report
            leads_csv = self.export_service.export_qualified_leads_to_csv(min_score=70.0, max_results=100)
            
            # Calculate daily metrics
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            
            daily_metrics = self._calculate_daily_metrics(yesterday)
            
            report = {
                'report_type': 'daily',
                'report_date': today.isoformat(),
                'period': yesterday.isoformat(),
                'dashboard_data': dashboard_data,
                'daily_metrics': daily_metrics,
                'qualified_leads_count': len(leads_csv.split('\n')) - 1,  # Subtract header
                'files_generated': ['qualified_leads.csv']
            }
            
            logger.info(f"Daily report generated for {yesterday}")
            return report
            
        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
            raise
    
    def generate_weekly_report(self) -> Dict[str, Any]:
        """Generate weekly business intelligence report"""
        try:
            logger.info("Generating weekly report")
            
            # Get dashboard data
            dashboard_data = self.export_service.export_dashboard_data_to_json()
            
            # Generate comprehensive exports
            customer_360_excel = self.export_service.export_customer_360_to_excel()
            business_excel = self.export_service.export_to_excel()
            leads_csv = self.export_service.export_qualified_leads_to_csv(min_score=60.0, max_results=500)
            
            # Calculate weekly metrics
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=7)
            
            weekly_metrics = self._calculate_weekly_metrics(start_date, end_date)
            
            report = {
                'report_type': 'weekly',
                'report_date': end_date.isoformat(),
                'period': f"{start_date.isoformat()} to {end_date.isoformat()}",
                'dashboard_data': dashboard_data,
                'weekly_metrics': weekly_metrics,
                'files_generated': [
                    'customer_360_weekly.xlsx',
                    'businesses_weekly.xlsx', 
                    'qualified_leads_weekly.csv'
                ]
            }
            
            logger.info(f"Weekly report generated for {start_date} to {end_date}")
            return report
            
        except Exception as e:
            logger.error(f"Error generating weekly report: {e}")
            raise    def gen
erate_monthly_report(self) -> Dict[str, Any]:
        """Generate monthly comprehensive business intelligence report"""
        try:
            logger.info("Generating monthly report")
            
            # Get comprehensive dashboard data
            dashboard_data = self.export_service.export_dashboard_data_to_json()
            
            # Generate all export formats
            customer_360_excel = self.export_service.export_customer_360_to_excel()
            business_excel = self.export_service.export_to_excel()
            business_geojson = self.export_service.export_to_geojson()
            business_kml = self.export_service.export_to_kml()
            leads_csv = self.export_service.export_qualified_leads_to_csv(min_score=50.0, max_results=1000)
            
            # Calculate monthly metrics
            end_date = datetime.now().date()
            start_date = end_date.replace(day=1)  # First day of current month
            
            monthly_metrics = self._calculate_monthly_metrics(start_date, end_date)
            
            report = {
                'report_type': 'monthly',
                'report_date': end_date.isoformat(),
                'period': f"{start_date.isoformat()} to {end_date.isoformat()}",
                'dashboard_data': dashboard_data,
                'monthly_metrics': monthly_metrics,
                'files_generated': [
                    'customer_360_monthly.xlsx',
                    'businesses_monthly.xlsx',
                    'businesses_monthly.geojson',
                    'businesses_monthly.kml',
                    'qualified_leads_monthly.csv'
                ]
            }
            
            logger.info(f"Monthly report generated for {start_date} to {end_date}")
            return report
            
        except Exception as e:
            logger.error(f"Error generating monthly report: {e}")
            raise
    
    def _calculate_daily_metrics(self, date) -> Dict[str, Any]:
        """Calculate metrics for a specific day"""
        try:
            from app.business_directory.models import Business
            from app.customer_360.models import Customer, CustomerInteraction
            
            start_datetime = datetime.combine(date, datetime.min.time())
            end_datetime = start_datetime + timedelta(days=1)
            
            # New businesses scraped
            new_businesses = self.db.query(Business).filter(
                Business.last_scraped_at >= start_datetime,
                Business.last_scraped_at < end_datetime
            ).count()
            
            # New customers
            new_customers = self.db.query(Customer).filter(
                Customer.created_at >= start_datetime,
                Customer.created_at < end_datetime
            ).count()
            
            # Customer interactions
            interactions = self.db.query(CustomerInteraction).filter(
                CustomerInteraction.interaction_date >= start_datetime,
                CustomerInteraction.interaction_date < end_datetime
            ).count()
            
            return {
                'new_businesses': new_businesses,
                'new_customers': new_customers,
                'customer_interactions': interactions,
                'date': date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating daily metrics: {e}")
            return {'error': str(e)}
    
    def _calculate_weekly_metrics(self, start_date, end_date) -> Dict[str, Any]:
        """Calculate metrics for a week period"""
        try:
            from app.business_directory.models import Business
            from app.customer_360.models import Customer, CustomerInteraction
            
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            # Weekly aggregations
            new_businesses = self.db.query(Business).filter(
                Business.last_scraped_at >= start_datetime,
                Business.last_scraped_at <= end_datetime
            ).count()
            
            new_customers = self.db.query(Customer).filter(
                Customer.created_at >= start_datetime,
                Customer.created_at <= end_datetime
            ).count()
            
            interactions = self.db.query(CustomerInteraction).filter(
                CustomerInteraction.interaction_date >= start_datetime,
                CustomerInteraction.interaction_date <= end_datetime
            ).count()
            
            # Lead progression
            qualified_leads = self.db.query(Customer).filter(
                Customer.updated_at >= start_datetime,
                Customer.updated_at <= end_datetime,
                Customer.lead_status == 'qualified'
            ).count()
            
            return {
                'new_businesses': new_businesses,
                'new_customers': new_customers,
                'customer_interactions': interactions,
                'qualified_leads': qualified_leads,
                'period': f"{start_date.isoformat()} to {end_date.isoformat()}"
            }
            
        except Exception as e:
            logger.error(f"Error calculating weekly metrics: {e}")
            return {'error': str(e)}    d
ef _calculate_monthly_metrics(self, start_date, end_date) -> Dict[str, Any]:
        """Calculate metrics for a month period"""
        try:
            from app.business_directory.models import Business
            from app.customer_360.models import Customer, CustomerInteraction
            
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            # Monthly aggregations
            new_businesses = self.db.query(Business).filter(
                Business.last_scraped_at >= start_datetime,
                Business.last_scraped_at <= end_datetime
            ).count()
            
            new_customers = self.db.query(Customer).filter(
                Customer.created_at >= start_datetime,
                Customer.created_at <= end_datetime
            ).count()
            
            interactions = self.db.query(CustomerInteraction).filter(
                CustomerInteraction.interaction_date >= start_datetime,
                CustomerInteraction.interaction_date <= end_datetime
            ).count()
            
            # Lead conversion metrics
            converted_leads = self.db.query(Customer).filter(
                Customer.updated_at >= start_datetime,
                Customer.updated_at <= end_datetime,
                Customer.lead_status == 'converted'
            ).count()
            
            # Data quality improvements
            geocoded_this_month = self.db.query(Business).filter(
                Business.last_geocoded_at >= start_datetime,
                Business.last_geocoded_at <= end_datetime,
                Business.latitude.isnot(None),
                Business.longitude.isnot(None)
            ).count()
            
            return {
                'new_businesses': new_businesses,
                'new_customers': new_customers,
                'customer_interactions': interactions,
                'converted_leads': converted_leads,
                'geocoded_businesses': geocoded_this_month,
                'period': f"{start_date.isoformat()} to {end_date.isoformat()}"
            }
            
        except Exception as e:
            logger.error(f"Error calculating monthly metrics: {e}")
            return {'error': str(e)}
    
    def send_report_email(self, report: Dict[str, Any], recipients: List[str], 
                         attachments: Optional[List[Dict[str, Any]]] = None):
        """Send report via email with optional attachments"""
        try:
            if not hasattr(settings, 'SMTP_SERVER') or not settings.SMTP_SERVER:
                logger.warning("SMTP not configured, skipping email send")
                return
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = settings.SMTP_FROM_EMAIL
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = f"Jamaica Business Directory - {report['report_type'].title()} Report"
            
            # Create email body
            body = self._create_email_body(report)
            msg.attach(MIMEText(body, 'html'))
            
            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment['data'])
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {attachment["filename"]}'
                    )
                    msg.attach(part)
            
            # Send email
            server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
            if hasattr(settings, 'SMTP_USE_TLS') and settings.SMTP_USE_TLS:
                server.starttls()
            if hasattr(settings, 'SMTP_USERNAME') and settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Report email sent to {len(recipients)} recipients")
            
        except Exception as e:
            logger.error(f"Error sending report email: {e}")
    
    def _create_email_body(self, report: Dict[str, Any]) -> str:
        """Create HTML email body for report"""
        report_type = report['report_type'].title()
        period = report.get('period', 'N/A')
        
        # Extract key metrics
        dashboard = report.get('dashboard_data', {})
        business_metrics = dashboard.get('business_metrics', {})
        customer_metrics = dashboard.get('customer_metrics', {})
        kpis = dashboard.get('kpis', {})
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #366092; color: white; padding: 20px; text-align: center; }}
                .metrics {{ display: flex; flex-wrap: wrap; margin: 20px 0; }}
                .metric-card {{ background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 5px; 
                              padding: 15px; margin: 10px; min-width: 200px; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #366092; }}
                .metric-label {{ font-size: 14px; color: #6c757d; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Jamaica Business Directory</h1>
                <h2>{report_type} Report</h2>
                <p>Period: {period}</p>
            </div>
            
            <div class="metrics">
                <div class="metric-card">
                    <div class="metric-value">{business_metrics.get('total_businesses', 0)}</div>
                    <div class="metric-label">Total Businesses</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{customer_metrics.get('total_customers', 0)}</div>
                    <div class="metric-label">Total Customers</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{customer_metrics.get('qualified_leads', 0)}</div>
                    <div class="metric-label">Qualified Leads</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{kpis.get('data_quality_score', 0):.1f}%</div>
                    <div class="metric-label">Data Quality Score</div>
                </div>
            </div>
            
            <h3>Key Performance Indicators</h3>
            <table>
                <tr><th>KPI</th><th>Value</th></tr>
                <tr><td>Geocoding Rate</td><td>{business_metrics.get('geocoding_rate', 0):.1f}%</td></tr>
                <tr><td>Lead Qualification Rate</td><td>{customer_metrics.get('qualification_rate', 0):.1f}%</td></tr>
                <tr><td>Lead Conversion Rate</td><td>{kpis.get('lead_conversion_rate', 0):.1f}%</td></tr>
                <tr><td>Customer Engagement Score</td><td>{kpis.get('customer_engagement_score', 0):.1f}%</td></tr>
            </table>
            
            <p>This automated report was generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.</p>
            <p>For more detailed analysis, please access the full dashboard or review the attached files.</p>
        </body>
        </html>
        """
        
        return html_body