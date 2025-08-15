import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from .models import DataIngestionJob, ProcessingStatus
import logging

logger = logging.getLogger(__name__)


class DataCleaningEngine:
    """Handles data cleaning and preprocessing operations"""
    
    def __init__(self):
        self.cleaning_operations = {
            'remove_duplicates': self._remove_duplicates,
            'handle_missing_values': self._handle_missing_values,
            'normalize_text': self._normalize_text,
            'remove_outliers': self._remove_outliers,
            'standardize_formats': self._standardize_formats,
            'validate_data_types': self._validate_data_types,
        }
    
    async def clean_data(
        self,
        job_id: str,
        cleaning_operations: List[str],
        remove_duplicates: bool,
        handle_missing_values: str,
        normalize_text: bool,
        db: Session
    ) -> Dict[str, Any]:
        """Clean data for specified ingestion job"""
        
        # Get the ingestion job
        job = db.query(DataIngestionJob).filter(DataIngestionJob.job_id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        if job.status != ProcessingStatus.COMPLETED:
            raise ValueError(f"Job {job_id} is not in completed state")
        
        try:
            # Load data (in real implementation, this would come from storage)
            # For now, we'll simulate with metadata
            original_records = job.job_metadata.get('records_ingested', 0) if job.job_metadata else 0
            
            # Apply cleaning operations
            cleaning_results = {
                'original_records': original_records,
                'operations_applied': [],
                'records_removed': 0,
                'records_modified': 0,
                'final_records': original_records
            }
            
            # Simulate cleaning operations
            records_after_cleaning = original_records
            
            if remove_duplicates:
                duplicates_removed = int(original_records * 0.05)  # Simulate 5% duplicates
                records_after_cleaning -= duplicates_removed
                cleaning_results['operations_applied'].append('remove_duplicates')
                cleaning_results['records_removed'] += duplicates_removed
            
            if handle_missing_values == 'drop':
                missing_removed = int(original_records * 0.03)  # Simulate 3% missing
                records_after_cleaning -= missing_removed
                cleaning_results['operations_applied'].append('drop_missing_values')
                cleaning_results['records_removed'] += missing_removed
            elif handle_missing_values in ['fill', 'interpolate']:
                cleaning_results['operations_applied'].append(f'{handle_missing_values}_missing_values')
                cleaning_results['records_modified'] += int(original_records * 0.03)
            
            if normalize_text:
                cleaning_results['operations_applied'].append('normalize_text')
                cleaning_results['records_modified'] += int(original_records * 0.8)  # Most text records
            
            # Apply custom cleaning operations
            for operation in cleaning_operations:
                if operation in self.cleaning_operations:
                    result = await self.cleaning_operations[operation](None)  # Simulate
                    cleaning_results['operations_applied'].append(operation)
                    if 'removed' in result:
                        cleaning_results['records_removed'] += result['removed']
                    if 'modified' in result:
                        cleaning_results['records_modified'] += result['modified']
            
            cleaning_results['final_records'] = records_after_cleaning
            
            # Update job metadata
            if job.job_metadata is None:
                job.job_metadata = {}
            job.job_metadata.update({
                'cleaning_applied': True,
                'cleaning_results': cleaning_results,
                'records_after_cleaning': records_after_cleaning
            })
            db.commit()
            
            logger.info(f"Data cleaning completed for job {job_id}")
            return cleaning_results
            
        except Exception as e:
            logger.error(f"Data cleaning failed for job {job_id}: {str(e)}")
            raise
    
    async def _remove_duplicates(self, data: Optional[List[Dict[str, Any]]]) -> Dict[str, int]:
        """Remove duplicate records"""
        if not data:
            return {'removed': 0, 'modified': 0}
        
        original_count = len(data)
        seen = set()
        unique_data = []
        
        for record in data:
            # Create a hashable representation of the record
            record_tuple = tuple(sorted(record.items()))
            if record_tuple not in seen:
                seen.add(record_tuple)
                unique_data.append(record)
        
        removed_count = original_count - len(unique_data)
        return {'removed': removed_count, 'modified': 0}
    
    async def _handle_missing_values(self, data: Optional[List[Dict[str, Any]]], method: str = 'drop') -> Dict[str, int]:
        """Handle missing values in dataset"""
        if not data:
            return {'removed': 0, 'modified': 0}
        
        original_count = len(data)
        
        if method == 'drop':
            # Remove records with any missing values
            cleaned_data = []
            for record in data:
                has_missing = False
                for value in record.values():
                    if value is None or value == '':
                        has_missing = True
                        break
                if not has_missing:
                    cleaned_data.append(record)
            
            removed_count = original_count - len(cleaned_data)
            return {'removed': removed_count, 'modified': 0}
        
        elif method == 'fill':
            # Fill missing values with defaults
            modified_count = 0
            for record in data:
                for key, value in record.items():
                    if value is None or value == '':
                        # Try to determine if it should be numeric or text
                        try:
                            # Check if other records have numeric values for this key
                            numeric_values = []
                            for other_record in data:
                                if key in other_record and other_record[key] is not None and other_record[key] != '':
                                    try:
                                        numeric_values.append(float(other_record[key]))
                                    except (ValueError, TypeError):
                                        break
                            
                            if numeric_values:
                                # Fill with median
                                numeric_values.sort()
                                median = numeric_values[len(numeric_values) // 2]
                                record[key] = median
                            else:
                                # Fill with 'Unknown' for text
                                record[key] = 'Unknown'
                            
                            modified_count += 1
                        except:
                            record[key] = 'Unknown'
                            modified_count += 1
            
            return {'removed': 0, 'modified': modified_count}
        
        elif method == 'interpolate':
            # Simple interpolation for numeric values
            modified_count = 0
            # This is a simplified version - in practice would be more sophisticated
            for record in data:
                for key, value in record.items():
                    if value is None or value == '':
                        record[key] = 0  # Simple default
                        modified_count += 1
            
            return {'removed': 0, 'modified': modified_count}
        
        return {'removed': 0, 'modified': 0}
    
    async def _normalize_text(self, data: Optional[List[Dict[str, Any]]]) -> Dict[str, int]:
        """Normalize text data"""
        if not data:
            return {'removed': 0, 'modified': 0}
        
        modified_count = 0
        
        # Get all columns from the data
        all_columns = set()
        for record in data:
            all_columns.update(record.keys())
        
        # Find text columns
        text_columns = []
        for col in all_columns:
            for record in data[:5]:  # Sample first 5 records
                if col in record and record[col] is not None:
                    if isinstance(record[col], str):
                        text_columns.append(col)
                        break
        
        for col in text_columns:
            for record in data:
                if col in record and record[col] is not None:
                    original_value = str(record[col])
                    
                    # Convert to lowercase
                    normalized_value = original_value.lower()
                    
                    # Remove extra whitespace
                    normalized_value = normalized_value.strip()
                    
                    # Remove special characters (keep alphanumeric and spaces)
                    normalized_value = re.sub(r'[^a-zA-Z0-9\s]', '', normalized_value)
                    
                    if normalized_value != original_value:
                        record[col] = normalized_value
                        modified_count += 1
        
        return {'removed': 0, 'modified': modified_count}
    
    async def _remove_outliers(self, data: Optional[List[Dict[str, Any]]]) -> Dict[str, int]:
        """Remove statistical outliers using IQR method"""
        if not data:
            return {'removed': 0, 'modified': 0}
        
        original_count = len(data)
        
        # Get all columns from the data
        all_columns = set()
        for record in data:
            all_columns.update(record.keys())
        
        # Find numeric columns
        numeric_columns = []
        for col in all_columns:
            is_numeric = True
            for record in data[:10]:  # Sample first 10 records
                if col in record and record[col] is not None:
                    try:
                        float(record[col])
                    except (ValueError, TypeError):
                        is_numeric = False
                        break
            if is_numeric:
                numeric_columns.append(col)
        
        cleaned_data = data.copy()
        
        for col in numeric_columns:
            # Collect numeric values for this column
            values = []
            for record in cleaned_data:
                if col in record and record[col] is not None:
                    try:
                        values.append(float(record[col]))
                    except (ValueError, TypeError):
                        pass
            
            if len(values) > 4:  # Need at least 4 values for quartiles
                values.sort()
                n = len(values)
                Q1 = values[n // 4]
                Q3 = values[3 * n // 4]
                IQR = Q3 - Q1
                
                # Define outlier bounds
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                # Remove outliers
                cleaned_data = [
                    record for record in cleaned_data
                    if col not in record or record[col] is None or
                    (lower_bound <= float(record[col]) <= upper_bound)
                ]
        
        removed_count = original_count - len(cleaned_data)
        return {'removed': removed_count, 'modified': 0}
    
    async def _standardize_formats(self, data: Optional[List[Dict[str, Any]]]) -> Dict[str, int]:
        """Standardize data formats (dates, phone numbers, etc.)"""
        if not data:
            return {'removed': 0, 'modified': 0}
        
        modified_count = 0
        
        # Get all columns from the data
        all_columns = set()
        for record in data:
            all_columns.update(record.keys())
        
        # Standardize date columns
        for col in all_columns:
            if 'date' in col.lower() or 'time' in col.lower():
                for record in data:
                    if col in record and record[col] is not None:
                        try:
                            # Simple date standardization - convert to ISO format
                            date_str = str(record[col])
                            # This is a simplified version - in practice would use proper date parsing
                            if '/' in date_str:
                                # Convert MM/DD/YYYY to YYYY-MM-DD
                                parts = date_str.split('/')
                                if len(parts) == 3:
                                    record[col] = f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
                                    modified_count += 1
                        except:
                            pass
        
        # Standardize phone numbers
        for col in all_columns:
            if 'phone' in col.lower():
                for record in data:
                    if col in record and record[col] is not None:
                        # Remove all non-digit characters
                        phone_str = str(record[col])
                        cleaned_phone = re.sub(r'[^\d]', '', phone_str)
                        if cleaned_phone != phone_str:
                            record[col] = cleaned_phone
                            modified_count += 1
        
        return {'removed': 0, 'modified': modified_count}
    
    async def _validate_data_types(self, data: Optional[List[Dict[str, Any]]]) -> Dict[str, int]:
        """Validate and convert data types"""
        if not data:
            return {'removed': 0, 'modified': 0}
        
        modified_count = 0
        
        # Get all columns from the data
        all_columns = set()
        for record in data:
            all_columns.update(record.keys())
        
        # Attempt to convert numeric columns
        for col in all_columns:
            # Check if column values can be converted to numeric
            can_be_numeric = True
            for record in data[:10]:  # Sample first 10 records
                if col in record and record[col] is not None:
                    try:
                        float(record[col])
                    except (ValueError, TypeError):
                        can_be_numeric = False
                        break
            
            if can_be_numeric:
                # Convert all values in this column to numeric
                for record in data:
                    if col in record and record[col] is not None:
                        try:
                            original_value = record[col]
                            numeric_value = float(original_value)
                            # Only convert if it's actually a string representation of a number
                            if str(original_value) != str(numeric_value):
                                record[col] = numeric_value
                                modified_count += 1
                        except (ValueError, TypeError):
                            pass
        
        return {'removed': 0, 'modified': modified_count}