from faker import Faker
import json
import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from .models import SyntheticDataJob, ProcessingStatus, DataSourceType
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class SyntheticDataGenerator:
    """Generates synthetic data for training and testing"""
    
    def __init__(self):
        self.fake = Faker()
        self.templates = {
            'user_profile': self._generate_user_profiles,
            'transaction': self._generate_transactions,
            'product': self._generate_products,
            'conversation': self._generate_conversations,
            'document': self._generate_documents,
            'sensor_data': self._generate_sensor_data,
        }
    
    async def generate_synthetic_data(
        self,
        template_type: str,
        num_records: int,
        output_format: DataSourceType,
        parameters: Dict[str, Any],
        preserve_privacy: bool,
        db: Session
    ) -> str:
        """Generate synthetic data based on template"""
        
        job_id = str(uuid.uuid4())
        
        # Create synthetic data job record
        job = SyntheticDataJob(
            job_id=job_id,
            template_type=template_type,
            parameters=parameters,
            output_format=output_format.value,
            status=ProcessingStatus.PENDING
        )
        db.add(job)
        db.commit()
        
        try:
            # Update status to processing
            job.status = ProcessingStatus.PROCESSING
            db.commit()
            
            # Generate data based on template
            if template_type not in self.templates:
                raise ValueError(f"Unsupported template type: {template_type}")
            
            data = await self.templates[template_type](num_records, parameters, preserve_privacy)
            
            # Convert to requested format
            output_data = self._convert_to_format(data, output_format)
            
            # Mark as completed
            job.status = ProcessingStatus.COMPLETED
            job.records_generated = len(data)
            job.completed_at = datetime.utcnow()
            
            logger.info(f"Generated {len(data)} synthetic records for job {job_id}")
            
        except Exception as e:
            logger.error(f"Synthetic data generation failed for job {job_id}: {str(e)}")
            job.status = ProcessingStatus.FAILED
        
        db.commit()
        return job_id
    
    async def _generate_user_profiles(
        self, 
        num_records: int, 
        parameters: Dict[str, Any], 
        preserve_privacy: bool
    ) -> List[Dict[str, Any]]:
        """Generate synthetic user profile data"""
        
        profiles = []
        
        for _ in range(num_records):
            profile = {
                'user_id': str(uuid.uuid4()) if preserve_privacy else self.fake.uuid4(),
                'first_name': self.fake.first_name(),
                'last_name': self.fake.last_name(),
                'email': self.fake.email() if not preserve_privacy else self.fake.safe_email(),
                'phone': self.fake.phone_number() if not preserve_privacy else self._anonymize_phone(),
                'date_of_birth': self.fake.date_of_birth(minimum_age=18, maximum_age=80).isoformat(),
                'address': {
                    'street': self.fake.street_address(),
                    'city': self.fake.city(),
                    'state': self.fake.state(),
                    'zip_code': self.fake.zipcode(),
                    'country': parameters.get('country', 'US')
                },
                'occupation': self.fake.job(),
                'company': self.fake.company(),
                'salary': self.fake.random_int(min=30000, max=200000),
                'created_at': self.fake.date_time_between(start_date='-2y', end_date='now').isoformat(),
                'preferences': {
                    'newsletter': self.fake.boolean(),
                    'notifications': self.fake.boolean(),
                    'language': parameters.get('language', 'en')
                }
            }
            
            profiles.append(profile)
        
        return profiles
    
    async def _generate_transactions(
        self, 
        num_records: int, 
        parameters: Dict[str, Any], 
        preserve_privacy: bool
    ) -> List[Dict[str, Any]]:
        """Generate synthetic transaction data"""
        
        transactions = []
        
        # Generate some user IDs to reference
        num_users = parameters.get('num_users', min(1000, num_records // 10))
        user_ids = [str(uuid.uuid4()) for _ in range(num_users)]
        
        for _ in range(num_records):
            transaction = {
                'transaction_id': str(uuid.uuid4()),
                'user_id': self.fake.random_element(user_ids),
                'amount': round(self.fake.random.uniform(1.0, 1000.0), 2),
                'currency': parameters.get('currency', 'USD'),
                'transaction_type': self.fake.random_element(['purchase', 'refund', 'transfer', 'deposit']),
                'merchant': self.fake.company(),
                'category': self.fake.random_element([
                    'groceries', 'entertainment', 'gas', 'restaurants', 
                    'shopping', 'utilities', 'healthcare', 'travel'
                ]),
                'timestamp': self.fake.date_time_between(start_date='-1y', end_date='now').isoformat(),
                'status': self.fake.random_element(['completed', 'pending', 'failed']),
                'payment_method': self.fake.random_element(['credit_card', 'debit_card', 'bank_transfer', 'cash']),
                'location': {
                    'city': self.fake.city(),
                    'state': self.fake.state(),
                    'country': parameters.get('country', 'US')
                }
            }
            
            if not preserve_privacy:
                transaction['card_last_four'] = self.fake.credit_card_number()[-4:]
            
            transactions.append(transaction)
        
        return transactions
    
    async def _generate_products(
        self, 
        num_records: int, 
        parameters: Dict[str, Any], 
        preserve_privacy: bool
    ) -> List[Dict[str, Any]]:
        """Generate synthetic product data"""
        
        products = []
        categories = parameters.get('categories', [
            'Electronics', 'Clothing', 'Books', 'Home & Garden', 
            'Sports', 'Toys', 'Health', 'Automotive'
        ])
        
        for _ in range(num_records):
            category = self.fake.random_element(categories)
            
            product = {
                'product_id': str(uuid.uuid4()),
                'name': self.fake.catch_phrase(),
                'description': self.fake.text(max_nb_chars=200),
                'category': category,
                'price': round(self.fake.random.uniform(5.0, 500.0), 2),
                'currency': parameters.get('currency', 'USD'),
                'brand': self.fake.company(),
                'sku': self.fake.bothify(text='??-####-??'),
                'weight': round(self.fake.random.uniform(0.1, 10.0), 2),
                'dimensions': {
                    'length': round(self.fake.random.uniform(1.0, 50.0), 1),
                    'width': round(self.fake.random.uniform(1.0, 50.0), 1),
                    'height': round(self.fake.random.uniform(1.0, 50.0), 1)
                },
                'in_stock': self.fake.boolean(chance_of_getting_true=80),
                'stock_quantity': self.fake.random_int(min=0, max=1000),
                'rating': round(self.fake.random.uniform(1.0, 5.0), 1),
                'reviews_count': self.fake.random_int(min=0, max=1000),
                'created_at': self.fake.date_time_between(start_date='-2y', end_date='now').isoformat(),
                'tags': [self.fake.word() for _ in range(self.fake.random_int(min=1, max=5))]
            }
            
            products.append(product)
        
        return products
    
    async def _generate_conversations(
        self, 
        num_records: int, 
        parameters: Dict[str, Any], 
        preserve_privacy: bool
    ) -> List[Dict[str, Any]]:
        """Generate synthetic conversation data for AI training"""
        
        conversations = []
        
        # Conversation templates
        templates = [
            {
                'context': 'customer_support',
                'intents': ['complaint', 'inquiry', 'compliment', 'request']
            },
            {
                'context': 'sales',
                'intents': ['product_info', 'pricing', 'availability', 'comparison']
            },
            {
                'context': 'technical_support',
                'intents': ['troubleshooting', 'setup', 'bug_report', 'feature_request']
            }
        ]
        
        for _ in range(num_records):
            template = self.fake.random_element(templates)
            intent = self.fake.random_element(template['intents'])
            
            conversation = {
                'conversation_id': str(uuid.uuid4()),
                'context': template['context'],
                'intent': intent,
                'user_message': self._generate_user_message(template['context'], intent),
                'assistant_response': self._generate_assistant_response(template['context'], intent),
                'sentiment': self.fake.random_element(['positive', 'neutral', 'negative']),
                'satisfaction_score': self.fake.random_int(min=1, max=5),
                'resolved': self.fake.boolean(chance_of_getting_true=85),
                'timestamp': self.fake.date_time_between(start_date='-6m', end_date='now').isoformat(),
                'language': parameters.get('language', 'en'),
                'channel': self.fake.random_element(['chat', 'email', 'phone', 'social'])
            }
            
            if not preserve_privacy:
                conversation['user_id'] = str(uuid.uuid4())
            
            conversations.append(conversation)
        
        return conversations
    
    async def _generate_documents(
        self, 
        num_records: int, 
        parameters: Dict[str, Any], 
        preserve_privacy: bool
    ) -> List[Dict[str, Any]]:
        """Generate synthetic document data"""
        
        documents = []
        
        document_types = parameters.get('document_types', [
            'article', 'report', 'manual', 'policy', 'faq', 'tutorial'
        ])
        
        for _ in range(num_records):
            doc_type = self.fake.random_element(document_types)
            
            document = {
                'document_id': str(uuid.uuid4()),
                'title': self.fake.catch_phrase(),
                'content': self.fake.text(max_nb_chars=2000),
                'document_type': doc_type,
                'author': self.fake.name() if not preserve_privacy else 'Anonymous',
                'created_at': self.fake.date_time_between(start_date='-2y', end_date='now').isoformat(),
                'updated_at': self.fake.date_time_between(start_date='-1y', end_date='now').isoformat(),
                'tags': [self.fake.word() for _ in range(self.fake.random_int(min=1, max=5))],
                'category': self.fake.random_element(['technical', 'business', 'legal', 'marketing']),
                'language': parameters.get('language', 'en'),
                'word_count': self.fake.random_int(min=100, max=5000),
                'version': f"{self.fake.random_int(min=1, max=10)}.{self.fake.random_int(min=0, max=9)}",
                'status': self.fake.random_element(['draft', 'published', 'archived'])
            }
            
            documents.append(document)
        
        return documents
    
    async def _generate_sensor_data(
        self, 
        num_records: int, 
        parameters: Dict[str, Any], 
        preserve_privacy: bool
    ) -> List[Dict[str, Any]]:
        """Generate synthetic IoT sensor data"""
        
        sensor_data = []
        
        sensor_types = parameters.get('sensor_types', [
            'temperature', 'humidity', 'pressure', 'motion', 'light', 'sound'
        ])
        
        # Generate some device IDs
        num_devices = parameters.get('num_devices', min(100, num_records // 100))
        device_ids = [f"device_{i:04d}" for i in range(num_devices)]
        
        for _ in range(num_records):
            sensor_type = self.fake.random_element(sensor_types)
            
            # Generate realistic values based on sensor type
            if sensor_type == 'temperature':
                value = round(self.fake.random.uniform(-10.0, 40.0), 2)
                unit = 'celsius'
            elif sensor_type == 'humidity':
                value = round(self.fake.random.uniform(0.0, 100.0), 2)
                unit = 'percent'
            elif sensor_type == 'pressure':
                value = round(self.fake.random.uniform(980.0, 1050.0), 2)
                unit = 'hPa'
            elif sensor_type == 'motion':
                value = self.fake.boolean()
                unit = 'boolean'
            elif sensor_type == 'light':
                value = round(self.fake.random.uniform(0.0, 1000.0), 2)
                unit = 'lux'
            else:  # sound
                value = round(self.fake.random.uniform(30.0, 120.0), 2)
                unit = 'dB'
            
            reading = {
                'reading_id': str(uuid.uuid4()),
                'device_id': self.fake.random_element(device_ids),
                'sensor_type': sensor_type,
                'value': value,
                'unit': unit,
                'timestamp': self.fake.date_time_between(start_date='-30d', end_date='now').isoformat(),
                'location': {
                    'latitude': float(self.fake.latitude()),
                    'longitude': float(self.fake.longitude()),
                    'building': self.fake.building_number(),
                    'room': self.fake.random_element(['A101', 'B205', 'C301', 'D150'])
                },
                'quality': self.fake.random_element(['good', 'fair', 'poor']),
                'battery_level': self.fake.random_int(min=0, max=100)
            }
            
            sensor_data.append(reading)
        
        return sensor_data
    
    def _generate_user_message(self, context: str, intent: str) -> str:
        """Generate realistic user messages"""
        templates = {
            'customer_support': {
                'complaint': "I'm having issues with my order. It was supposed to arrive yesterday but I haven't received it yet.",
                'inquiry': "Can you help me understand how to use this feature?",
                'compliment': "I wanted to thank you for the excellent service. Everything worked perfectly!",
                'request': "I need to change my shipping address for my recent order."
            },
            'sales': {
                'product_info': "Can you tell me more about the specifications of this product?",
                'pricing': "What's the current price for this item? Are there any discounts available?",
                'availability': "Is this product currently in stock? When will it be available?",
                'comparison': "How does this product compare to similar alternatives?"
            },
            'technical_support': {
                'troubleshooting': "The application keeps crashing when I try to save my work.",
                'setup': "I need help setting up the initial configuration.",
                'bug_report': "I found a bug where the data doesn't save properly.",
                'feature_request': "It would be great if you could add a dark mode option."
            }
        }
        
        return templates.get(context, {}).get(intent, "I need some help with this.")
    
    def _generate_assistant_response(self, context: str, intent: str) -> str:
        """Generate realistic assistant responses"""
        templates = {
            'customer_support': {
                'complaint': "I apologize for the delay. Let me check your order status and provide an update.",
                'inquiry': "I'd be happy to help you with that. Let me walk you through the process.",
                'compliment': "Thank you so much for your kind words! We really appreciate your feedback.",
                'request': "I can help you update your shipping address. Let me process that change for you."
            },
            'sales': {
                'product_info': "Here are the detailed specifications for this product...",
                'pricing': "The current price is $X.XX. We have a 10% discount available this week.",
                'availability': "This product is currently in stock and ready to ship within 2-3 business days.",
                'comparison': "Compared to similar products, this one offers better performance and value."
            },
            'technical_support': {
                'troubleshooting': "Let's troubleshoot this issue step by step. First, please try restarting the application.",
                'setup': "I'll guide you through the setup process. Let's start with the basic configuration.",
                'bug_report': "Thank you for reporting this bug. I'll escalate it to our development team.",
                'feature_request': "That's a great suggestion! I'll forward it to our product team for consideration."
            }
        }
        
        return templates.get(context, {}).get(intent, "I'll help you with that right away.")
    
    def _anonymize_phone(self) -> str:
        """Generate anonymized phone number"""
        return f"555-{self.fake.random_int(min=1000, max=9999)}"
    
    def _convert_to_format(self, data: List[Dict[str, Any]], output_format: DataSourceType) -> str:
        """Convert data to requested output format"""
        if output_format == DataSourceType.JSON:
            return json.dumps(data, indent=2, default=str)
        
        elif output_format == DataSourceType.CSV:
            if not data:
                return ""
            
            # Convert to CSV format
            import csv
            from io import StringIO
            
            output = StringIO()
            if data:
                fieldnames = data[0].keys()
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                for row in data:
                    # Flatten nested dictionaries for CSV
                    flat_row = {}
                    for key, value in row.items():
                        if isinstance(value, dict):
                            flat_row[key] = json.dumps(value)
                        else:
                            flat_row[key] = value
                    writer.writerow(flat_row)
            
            return output.getvalue()
        
        elif output_format == DataSourceType.PARQUET:
            # In real implementation, would save to file and return path
            return f"Generated {len(data)} records in Parquet format"
        
        else:
            return json.dumps(data, indent=2, default=str)
    
    def get_job_status(self, job_id: str, db: Session) -> Optional[SyntheticDataJob]:
        """Get synthetic data job status"""
        return db.query(SyntheticDataJob).filter(SyntheticDataJob.job_id == job_id).first()