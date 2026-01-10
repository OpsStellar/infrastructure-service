"""
OpenTelemetry instrumentation setup for Infrastructure Service
"""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
import logging

from config import settings

logger = logging.getLogger(__name__)


def setup_instrumentation(app):
    """
    Setup OpenTelemetry instrumentation for the Infrastructure Service
    
    Args:
        app: FastAPI application instance
    """
    try:
        # Create resource with service name
        resource = Resource(attributes={
            SERVICE_NAME: settings.OTEL_SERVICE_NAME
        })
        
        # Setup tracer provider
        tracer_provider = TracerProvider(resource=resource)
        
        # Configure OTLP exporter
        otlp_exporter = OTLPSpanExporter(
            endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
            insecure=True  # Use TLS in production
        )
        
        # Add span processor
        tracer_provider.add_span_processor(
            BatchSpanProcessor(otlp_exporter)
        )
        
        # Set global tracer provider
        trace.set_tracer_provider(tracer_provider)
        
        # Instrument FastAPI
        FastAPIInstrumentor.instrument_app(app)
        logger.info("✅ FastAPI instrumentation enabled")
        
        # Instrument SQLAlchemy
        SQLAlchemyInstrumentor().instrument()
        logger.info("✅ SQLAlchemy instrumentation enabled")
        
        # Instrument httpx for external API calls
        HTTPXClientInstrumentor().instrument()
        logger.info("✅ HTTPX instrumentation enabled")
        
        # Instrument Redis
        RedisInstrumentor().instrument()
        logger.info("✅ Redis instrumentation enabled")
        
        logger.info(f"🔍 OpenTelemetry initialized - sending traces to {settings.OTEL_EXPORTER_OTLP_ENDPOINT}")
        
    except Exception as e:
        logger.warning(f"⚠️ OpenTelemetry setup failed (non-critical): {e}")


def shutdown_instrumentation():
    """Shutdown OpenTelemetry and flush remaining spans"""
    try:
        trace.get_tracer_provider().shutdown()
        logger.info("🔍 OpenTelemetry shut down successfully")
    except Exception as e:
        logger.warning(f"⚠️ OpenTelemetry shutdown warning: {e}")


def get_tracer(name: str = __name__):
    """
    Get a tracer instance for manual span creation
    
    Args:
        name: Tracer name (usually __name__)
    
    Returns:
        Tracer instance
    """
    return trace.get_tracer(name)
