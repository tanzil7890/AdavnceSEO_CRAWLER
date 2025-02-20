from kafka import KafkaProducer as BaseKafkaProducer
from typing import Any, Callable
import json
import logging

from ...config.settings import settings

logger = logging.getLogger(__name__)

class KafkaProducer:
    def __init__(self, bootstrap_servers: str, value_serializer: Callable = None):
        self.producer = BaseKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=value_serializer or (lambda v: json.dumps(v).encode('utf-8'))
        )

    def send(self, topic: str, value: Any, key: str = None):
        try:
            future = self.producer.send(topic, value=value, key=key.encode('utf-8') if key else None)
            future.get(timeout=10)  # Wait for message to be sent
        except Exception as e:
            logger.error(f"Error sending message to Kafka: {e}")
            raise

    def close(self):
        if self.producer:
            self.producer.close() 