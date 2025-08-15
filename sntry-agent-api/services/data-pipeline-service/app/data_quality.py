import re
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from .models import DataQualityReport, ProcessingStatus
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DataQualityValidator:
    """Validates data quality and generates quality reports"""
    
    def __init__(self):
        self.validation_rules = {
            'completeness': self._check_completeness,
            'uniqueness': self._check_uniqueness,
            'validity': self._check_validity,
            'consistency': self._check_consistency,
            'accuracy': self._check_accuracy,
        }
    
    async def validate_data(
        self,
        data: List[Dict[str, Any]],
        validation_rules: List[str],
        job_id: str,
        db: Session
    ) -> DataQualityReport:
        """Validate data quality and create report"""
        
        total_records = len(data)
        issues = []
        validation_results = {}
        
        try:
            # Run validation rules
            for rule in validation_rules:
                if rule in self.validation_rules:
                    result = await self.validation_rules[rule](data)
                    validation_results[rule] = result
                    
                    if result['issues']:
                        issues.extend(result['issues'])
            
            # Calculate overall quality score
            quality_score = self._calculate_quality_score(validation_results, total_records)
            
            # Count valid vs invalid records
            invalid_records = sum(issue.get('affected_records', 0) for issue in issues)
            valid_records = max(0, total_records - invalid_records)
            
            # Create quality report
            report = DataQualityReport(
                job_id=job_id,
                total_records=total_records,
                valid_records=valid_records,
                invalid_records=invalid_records,
                quality_score=quality_score,
                validation_rules=validation_rules,
                issues=issues
            )
            
            db.add(report)
            db.commit()
            
            logger.info(f"Data quality validation completed for job {job_id}. Score: {quality_score:.2f}")
            return report
            
        except Exception as e:
            logger.error(f"Data quality validation failed for job {job_id}: {str(e)}")
            raise
    
    async def _check_completeness(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check data completeness (missing values)"""
        issues = []
        missing_stats = {}
        
        if not data:
            return {'passed': True, 'issues': [], 'stats': {}}
        
        # Get all columns from the data
        all_columns = set()
        for record in data:
            all_columns.update(record.keys())
        
        for column in all_columns:
            missing_count = 0
            for record in data:
                if column not in record or record[column] is None or record[column] == '':
                    missing_count += 1
            
            missing_percentage = (missing_count / len(data)) * 100
            
            missing_stats[column] = {
                'missing_count': missing_count,
                'missing_percentage': missing_percentage
            }
            
            if missing_percentage > 10:  # More than 10% missing
                issues.append({
                    'type': 'completeness',
                    'severity': 'high' if missing_percentage > 50 else 'medium',
                    'column': column,
                    'description': f'Column has {missing_percentage:.1f}% missing values',
                    'affected_records': missing_count
                })
        
        return {
            'passed': len(issues) == 0,
            'issues': issues,
            'stats': missing_stats
        }
    
    async def _check_uniqueness(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check data uniqueness (duplicates)"""
        issues = []
        uniqueness_stats = {}
        
        if not data:
            return {'passed': True, 'issues': [], 'stats': {}}
        
        # Check for duplicate rows
        seen_rows = set()
        duplicate_count = 0
        for record in data:
            row_tuple = tuple(sorted(record.items()))
            if row_tuple in seen_rows:
                duplicate_count += 1
            else:
                seen_rows.add(row_tuple)
        
        if duplicate_count > 0:
            issues.append({
                'type': 'uniqueness',
                'severity': 'medium',
                'description': f'Found {duplicate_count} duplicate rows',
                'affected_records': duplicate_count
            })
        
        # Get all columns from the data
        all_columns = set()
        for record in data:
            all_columns.update(record.keys())
        
        # Check uniqueness for each column
        for column in all_columns:
            values = []
            non_null_count = 0
            for record in data:
                if column in record and record[column] is not None and record[column] != '':
                    values.append(record[column])
                    non_null_count += 1
            
            unique_count = len(set(values))
            uniqueness_ratio = unique_count / non_null_count if non_null_count > 0 else 0
            
            uniqueness_stats[column] = {
                'unique_count': unique_count,
                'total_count': non_null_count,
                'uniqueness_ratio': uniqueness_ratio
            }
            
            # Flag columns that should be unique but aren't (like IDs)
            if 'id' in column.lower() and uniqueness_ratio < 1.0:
                issues.append({
                    'type': 'uniqueness',
                    'severity': 'high',
                    'column': column,
                    'description': f'ID column has duplicate values (uniqueness: {uniqueness_ratio:.2f})',
                    'affected_records': non_null_count - unique_count
                })
        
        return {
            'passed': len(issues) == 0,
            'issues': issues,
            'stats': uniqueness_stats
        }
    
    async def _check_validity(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check data validity (format, range, type)"""
        issues = []
        validity_stats = {}
        
        if not data:
            return {'passed': True, 'issues': [], 'stats': {}}
        
        # Get all columns from the data
        all_columns = set()
        for record in data:
            all_columns.update(record.keys())
        
        for column in all_columns:
            column_issues = []
            
            # Check for email format if column name suggests email
            if 'email' in column.lower():
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                invalid_count = 0
                
                for record in data:
                    if column in record and record[column]:
                        if not re.match(email_pattern, str(record[column])):
                            invalid_count += 1
                
                if invalid_count > 0:
                    column_issues.append({
                        'type': 'validity',
                        'severity': 'medium',
                        'column': column,
                        'description': f'Invalid email format in {invalid_count} records',
                        'affected_records': invalid_count
                    })
            
            # Check for phone number format
            elif 'phone' in column.lower():
                phone_pattern = r'^\+?[\d\s\-\(\)]{10,}$'
                invalid_count = 0
                
                for record in data:
                    if column in record and record[column]:
                        if not re.match(phone_pattern, str(record[column])):
                            invalid_count += 1
                
                if invalid_count > 0:
                    column_issues.append({
                        'type': 'validity',
                        'severity': 'medium',
                        'column': column,
                        'description': f'Invalid phone format in {invalid_count} records',
                        'affected_records': invalid_count
                    })
            
            # Check numeric ranges for age, count, quantity columns
            elif 'age' in column.lower() or 'count' in column.lower() or 'quantity' in column.lower():
                negative_count = 0
                
                for record in data:
                    if column in record and record[column] is not None:
                        try:
                            value = float(record[column])
                            if value < 0:
                                negative_count += 1
                        except (ValueError, TypeError):
                            pass
                
                if negative_count > 0:
                    column_issues.append({
                        'type': 'validity',
                        'severity': 'high',
                        'column': column,
                        'description': f'Negative values found in {column} ({negative_count} records)',
                        'affected_records': negative_count
                    })
            
            validity_stats[column] = {
                'issues_count': len(column_issues)
            }
            
            issues.extend(column_issues)
        
        return {
            'passed': len(issues) == 0,
            'issues': issues,
            'stats': validity_stats
        }
    
    async def _check_consistency(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check data consistency across columns"""
        issues = []
        consistency_stats = {}
        
        if not data:
            return {'passed': True, 'issues': [], 'stats': {}}
        
        # Get all columns from the data
        all_columns = set()
        for record in data:
            all_columns.update(record.keys())
        
        # Check date consistency (start_date < end_date)
        date_columns = [col for col in all_columns if 'date' in col.lower()]
        checks_performed = 0
        
        if len(date_columns) >= 2:
            for i in range(len(date_columns)):
                for j in range(i + 1, len(date_columns)):
                    col1, col2 = date_columns[i], date_columns[j]
                    
                    # Check if start dates are after end dates
                    if 'start' in col1.lower() and 'end' in col2.lower():
                        inconsistent = 0
                        for record in data:
                            if col1 in record and col2 in record:
                                try:
                                    # Simple date comparison (assumes ISO format)
                                    if record[col1] and record[col2]:
                                        if str(record[col1]) > str(record[col2]):
                                            inconsistent += 1
                                except:
                                    pass
                        
                        if inconsistent > 0:
                            issues.append({
                                'type': 'consistency',
                                'severity': 'high',
                                'columns': [col1, col2],
                                'description': f'Start date after end date in {inconsistent} records',
                                'affected_records': inconsistent
                            })
                        checks_performed += 1
        
        # Check numeric consistency (e.g., total = sum of parts)
        numeric_columns = []
        for col in all_columns:
            # Check if column contains numeric values
            is_numeric = True
            for record in data[:5]:  # Sample first 5 records
                if col in record and record[col] is not None:
                    try:
                        float(record[col])
                    except (ValueError, TypeError):
                        is_numeric = False
                        break
            if is_numeric:
                numeric_columns.append(col)
        
        # Look for potential sum relationships
        for col in numeric_columns:
            if 'total' in col.lower():
                component_cols = [c for c in numeric_columns 
                                if c != col and 'total' not in c.lower()]
                
                if len(component_cols) >= 2:
                    inconsistent = 0
                    for record in data:
                        if col in record and record[col] is not None:
                            try:
                                total_value = float(record[col])
                                component_sum = sum(
                                    float(record.get(c, 0) or 0) 
                                    for c in component_cols 
                                    if c in record and record[c] is not None
                                )
                                if abs(total_value - component_sum) > 0.01:
                                    inconsistent += 1
                            except (ValueError, TypeError):
                                pass
                    
                    if inconsistent > 0:
                        issues.append({
                            'type': 'consistency',
                            'severity': 'medium',
                            'column': col,
                            'description': f'Total column inconsistent with sum of components in {inconsistent} records',
                            'affected_records': inconsistent
                        })
                    checks_performed += 1
        
        consistency_stats['checks_performed'] = checks_performed
        
        return {
            'passed': len(issues) == 0,
            'issues': issues,
            'stats': consistency_stats
        }
    
    async def _check_accuracy(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check data accuracy against known patterns"""
        issues = []
        accuracy_stats = {}
        
        if not data:
            return {'passed': True, 'issues': [], 'stats': {}}
        
        # Get all columns from the data
        all_columns = set()
        for record in data:
            all_columns.update(record.keys())
        
        text_columns_checked = 0
        
        # Check for common data entry errors
        for column in all_columns:
            # Check if column contains text values
            has_text = False
            for record in data[:5]:  # Sample first 5 records
                if column in record and record[column] is not None:
                    if isinstance(record[column], str):
                        has_text = True
                        break
            
            if has_text:
                text_columns_checked += 1
                
                # Check for inconsistent capitalization
                unique_values = set()
                for record in data:
                    if column in record and record[column] is not None:
                        unique_values.add(str(record[column]))
                
                # Group by lowercase to find capitalization inconsistencies
                lowercase_groups = {}
                for value in unique_values:
                    lower_val = value.lower()
                    if lower_val not in lowercase_groups:
                        lowercase_groups[lower_val] = []
                    lowercase_groups[lower_val].append(value)
                
                inconsistent_caps = sum(1 for group in lowercase_groups.values() if len(group) > 1)
                
                if inconsistent_caps > 0:
                    issues.append({
                        'type': 'accuracy',
                        'severity': 'low',
                        'column': column,
                        'description': f'Inconsistent capitalization in {inconsistent_caps} value groups',
                        'affected_records': inconsistent_caps
                    })
        
        accuracy_stats['capitalization_checks'] = text_columns_checked
        
        return {
            'passed': len(issues) == 0,
            'issues': issues,
            'stats': accuracy_stats
        }
    
    def _calculate_quality_score(self, validation_results: Dict[str, Any], total_records: int) -> float:
        """Calculate overall data quality score (0-100)"""
        if not validation_results:
            return 100.0
        
        total_issues = 0
        weighted_issues = 0
        
        severity_weights = {
            'high': 3,
            'medium': 2,
            'low': 1
        }
        
        for rule_result in validation_results.values():
            for issue in rule_result.get('issues', []):
                total_issues += 1
                severity = issue.get('severity', 'medium')
                weight = severity_weights.get(severity, 2)
                affected_records = issue.get('affected_records', 1)
                
                # Weight by severity and proportion of affected records
                impact = (affected_records / total_records) * weight
                weighted_issues += impact
        
        # Calculate score (higher weighted issues = lower score)
        if weighted_issues == 0:
            return 100.0
        
        # Normalize to 0-100 scale
        max_possible_impact = len(validation_results) * 3  # All high severity
        score = max(0, 100 - (weighted_issues / max_possible_impact) * 100)
        
        return round(score, 2)
    
    def get_quality_report(self, job_id: str, db: Session) -> Optional[DataQualityReport]:
        """Get quality report for a job"""
        return db.query(DataQualityReport).filter(DataQualityReport.job_id == job_id).first()