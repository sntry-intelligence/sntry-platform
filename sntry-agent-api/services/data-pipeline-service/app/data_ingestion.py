import json
import xml.etree.ElementTree as ET
import csv
from io import StringIO
from typing import Dict, Any, List, Optional
from pathlib import Path
import uuid
from sqlalchemy.orm import Session
from .models import DataIngestionJob, DataSourceType, ProcessingStatus
from .data_quality import DataQualityValidator
import logging

logger = logging.getLogger(__name__)


class DataIngestionEngine:
    """Handles data ingestion from various sources"""
    
    def __init__(self):
        self.supported_formats = {
            DataSourceType.CSV: self._ingest_csv,
            DataSourceType.JSON: self._ingest_json,
            DataSourceType.PARQUET: self._ingest_parquet,
            DataSourceType.TEXT: self._ingest_text,
            DataSourceType.XML: self._ingest_xml,
        }
    
    async def ingest_data(
        self, 
        source_type: DataSourceType, 
        source_path: str, 
        metadata: Dict[str, Any],
        validation_rules: List[str],
        db: Session
    ) -> str:
        """Ingest data from specified source"""
        job_id = str(uuid.uuid4())
        
        # Create ingestion job record
        job = DataIngestionJob(
            job_id=job_id,
            source_type=source_type.value,
            source_path=source_path,
            job_metadata=metadata,
            status=ProcessingStatus.PENDING
        )
        db.add(job)
        db.commit()
        
        try:
            # Update status to processing
            job.status = ProcessingStatus.PROCESSING
            db.commit()
            
            # Perform ingestion based on source type
            if source_type not in self.supported_formats:
                raise ValueError(f"Unsupported source type: {source_type}")
            
            data = await self.supported_formats[source_type](source_path, metadata)
            
            # Validate data quality if rules provided
            if validation_rules:
                validator = DataQualityValidator()
                quality_report = await validator.validate_data(data, validation_rules, job_id, db)
                
                # Update job metadata with quality info
                if job.job_metadata is None:
                    job.job_metadata = {}
                job.job_metadata.update({
                    "quality_score": quality_report.quality_score,
                    "total_records": quality_report.total_records,
                    "valid_records": quality_report.valid_records
                })
            
            # Mark as completed
            job.status = ProcessingStatus.COMPLETED
            if job.job_metadata is None:
                job.job_metadata = {}
            job.job_metadata.update({
                "records_ingested": len(data) if hasattr(data, '__len__') else 0,
                "columns": list(data[0].keys()) if data and isinstance(data, list) and data[0] else []
            })
            
        except Exception as e:
            logger.error(f"Data ingestion failed for job {job_id}: {str(e)}")
            job.status = ProcessingStatus.FAILED
            job.error_message = str(e)
        
        db.commit()
        return job_id
    
    async def _ingest_csv(self, source_path: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Ingest CSV data"""
        try:
            # Extract CSV-specific parameters from metadata
            delimiter = metadata.get('delimiter', ',')
            encoding = metadata.get('encoding', 'utf-8')
            
            records = []
            with open(source_path, 'r', encoding=encoding) as file:
                reader = csv.DictReader(file, delimiter=delimiter)
                for row in reader:
                    records.append(dict(row))
            
            logger.info(f"Successfully ingested CSV with {len(records)} records")
            return records
            
        except Exception as e:
            logger.error(f"Failed to ingest CSV from {source_path}: {str(e)}")
            raise
    
    async def _ingest_json(self, source_path: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Ingest JSON data"""
        try:
            with open(source_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            # Handle different JSON structures
            if isinstance(data, list):
                records = data
            elif isinstance(data, dict):
                # If it's a single object, wrap in list
                if 'data' in data:
                    records = data['data'] if isinstance(data['data'], list) else [data['data']]
                else:
                    records = [data]
            else:
                raise ValueError("Unsupported JSON structure")
            
            logger.info(f"Successfully ingested JSON with {len(records)} records")
            return records
            
        except Exception as e:
            logger.error(f"Failed to ingest JSON from {source_path}: {str(e)}")
            raise
    
    async def _ingest_parquet(self, source_path: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Ingest Parquet data"""
        try:
            # For now, return a placeholder since parquet requires pandas
            # In production, this would use pyarrow or similar
            records = [{"message": "Parquet ingestion requires additional dependencies"}]
            logger.info(f"Parquet ingestion placeholder - would process {source_path}")
            return records
            
        except Exception as e:
            logger.error(f"Failed to ingest Parquet from {source_path}: {str(e)}")
            raise
    
    async def _ingest_text(self, source_path: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Ingest plain text data"""
        try:
            with open(source_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            # Create records with text content
            records = [
                {
                    'text': line.strip(),
                    'line_number': i + 1
                }
                for i, line in enumerate(lines)
            ]
            
            logger.info(f"Successfully ingested text file with {len(records)} lines")
            return records
            
        except Exception as e:
            logger.error(f"Failed to ingest text from {source_path}: {str(e)}")
            raise
    
    async def _ingest_xml(self, source_path: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Ingest XML data"""
        try:
            tree = ET.parse(source_path)
            root = tree.getroot()
            
            # Extract data based on XML structure
            records = []
            for element in root:
                record = {}
                for child in element:
                    record[child.tag] = child.text
                records.append(record)
            
            logger.info(f"Successfully ingested XML with {len(records)} records")
            return records
            
        except Exception as e:
            logger.error(f"Failed to ingest XML from {source_path}: {str(e)}")
            raise
    
    def get_job_status(self, job_id: str, db: Session) -> Optional[DataIngestionJob]:
        """Get ingestion job status"""
        return db.query(DataIngestionJob).filter(DataIngestionJob.job_id == job_id).first()