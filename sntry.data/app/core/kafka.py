"""
Apache Kafka configuration and connection management
"""
import asyncio
import logging
from typing import Dict, List, Optional, Callable
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.errors import KafkaError
import json

from app.core.config import settings

logger = logging.getLogger(__name__)


class KafkaProducer:
    """Async Kafka producer wrapper"""
    
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
    
    async def start(self):
        """Start Kafka producer"""
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                retry_backoff_ms=1000,
                request_timeout_ms=30000
            )
            await self.producer.start()
            logger.info("Kafka producer started successfully")
        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}")
            raise
    
    async def stop(self):
        """Stop Kafka producer"""
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")
    
    async def send_message(self, topic: str, message: Dict, key: Optional[str] = None):
        """Send message to Kafka topic"""
        if not self.producer:
            raise RuntimeError("Kafka producer not started")
        
        try:
            await self.producer.send(topic, value=message, key=key)
            logger.debug(f"Message sent to topic {topic}: {message}")
        except KafkaError as e:
            logger.error(f"Failed to send message to topic {topic}: {e}")
            raise


class KafkaConsumer:
    """Async Kafka consumer wrapper"""
    
    def __init__(self, topics: List[str], group_id: str = None):
        self.topics = topics
        self.group_id = group_id or settings.KAFKA_CONSUMER_GROUP
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.running = False
    
    async def start(self):
        """Start Kafka consumer"""
        try:
            self.consumer = AIOKafkaConsumer(
                *self.topics,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id=self.group_id,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                auto_offset_reset='latest',
                enable_auto_commit=True
            )
            await self.consumer.start()
            logger.info(f"Kafka consumer started for topics: {self.topics}")
        except Exception as e:
            logger.error(f"Failed to start Kafka consumer: {e}")
            raise
    
    async def stop(self):
        """Stop Kafka consumer"""
        self.running = False
        if self.consumer:
            await self.consumer.stop()
            logger.info("Kafka consumer stopped")
    
    async def consume_messages(self, message_handler: Callable):
        """Consume messages and process with handler"""
        if not self.consumer:
            raise RuntimeError("Kafka consumer not started")
        
        self.running = True
        try:
            async for message in self.consumer:
                if not self.running:
                    break
                
                try:
                    await message_handler(message)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    
        except Exception as e:
            logger.error(f"Error consuming messages: {e}")
            raise


# Global Kafka instances
kafka_producer = KafkaProducer()


async def init_kafka():
    """Initialize Kafka connections"""
    try:
        await kafka_producer.start()
        logger.info("Kafka initialization completed")
    except Exception as e:
        logger.error(f"Kafka initialization failed: {e}")
        raise


async def close_kafka():
    """Close Kafka connections"""
    await kafka_producer.stop()
    logger.info("Kafka connections closed")


# Kafka topics
class KafkaTopics:
    """Kafka topic definitions"""
    BUSINESS_EVENTS = "business-events"
    CUSTOMER_EVENTS = "customer-events"
    SCRAPING_EVENTS = "scraping-events"
    GEOCODING_EVENTS = "geocoding-events"
    DATA_QUALITY_EVENTS = "data-quality-events"