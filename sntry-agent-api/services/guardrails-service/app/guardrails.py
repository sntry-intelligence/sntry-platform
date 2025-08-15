"""
AI Guardrails core functionality
"""
import re
import hashlib
import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
import json

# ML/NLP imports
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    import torch
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logging.warning("Transformers and ML libraries not available. Using rule-based fallbacks.")

from .models import ViolationType, SeverityLevel, ActionType


class ContentModerator:
    """Content moderation using multiple detection methods"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.models = {}
        self._load_models()
        self._load_word_lists()
    
    def _load_models(self):
        """Load pre-trained models for content moderation"""
        if not TRANSFORMERS_AVAILABLE:
            self.logger.warning("ML models not available, using rule-based detection only")
            return
        
        try:
            # Load toxicity detection model
            self.models['toxicity'] = pipeline(
                "text-classification",
                model="unitary/toxic-bert",
                device=0 if torch.cuda.is_available() else -1
            )
            
            # Load hate speech detection model
            self.models['hate_speech'] = pipeline(
                "text-classification", 
                model="martin-ha/toxic-comment-model",
                device=0 if torch.cuda.is_available() else -1
            )
            
            self.logger.info("Content moderation models loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load ML models: {e}")
            self.models = {}
    
    def _load_word_lists(self):
        """Load word lists for rule-based detection"""
        # Profanity words (basic list - in production, use comprehensive datasets)
        self.profanity_words = {
            'mild': ['damn', 'hell', 'crap'],
            'moderate': ['stupid', 'idiot', 'moron'],
            'severe': ['hate', 'kill', 'die']  # Simplified for demo
        }
        
        # Hate speech indicators
        self.hate_speech_patterns = [
            r'\b(hate|despise|loathe)\s+(all|every)\s+\w+',
            r'\b(kill|murder|eliminate)\s+(all|every)\s+\w+',
            r'\b\w+\s+(are|is)\s+(inferior|worthless|garbage)'
        ]
        
        # Violence indicators
        self.violence_patterns = [
            r'\b(kill|murder|assassinate|eliminate|destroy)\b',
            r'\b(bomb|explosion|weapon|gun|knife|attack)\b',
            r'\b(violence|violent|brutal|savage)\b'
        ]
        
        # PII patterns
        self.pii_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b|\b\d{3}-\d{4}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
        }
    
    def moderate_content(self, content: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Moderate content using multiple detection methods
        
        Args:
            content: Text content to moderate
            context: Additional context for moderation
            
        Returns:
            Dictionary with moderation results
        """
        results = {
            'is_safe': True,
            'violations': [],
            'action': ActionType.ALLOW,
            'confidence_score': 0.0,
            'filtered_content': content,
            'explanation': None
        }
        
        # Check for various violation types
        violations = []
        
        # 1. Toxicity detection
        toxicity_result = self._detect_toxicity(content)
        if toxicity_result['detected']:
            violations.append(toxicity_result)
        
        # 2. Hate speech detection
        hate_speech_result = self._detect_hate_speech(content)
        if hate_speech_result['detected']:
            violations.append(hate_speech_result)
        
        # 3. Violence detection
        violence_result = self._detect_violence(content)
        if violence_result['detected']:
            violations.append(violence_result)
        
        # 4. Profanity detection
        profanity_result = self._detect_profanity(content)
        if profanity_result['detected']:
            violations.append(profanity_result)
        
        # 5. PII detection
        pii_result = self._detect_pii(content)
        if pii_result['detected']:
            violations.append(pii_result)
        
        # Determine overall result
        if violations:
            results['is_safe'] = False
            results['violations'] = violations
            
            # Determine action based on highest severity
            max_severity = max(v['severity'] for v in violations)
            results['action'] = self._determine_action(max_severity)
            
            # Calculate overall confidence
            results['confidence_score'] = sum(v['confidence'] for v in violations) / len(violations)
            
            # Filter content if needed
            if results['action'] in [ActionType.FILTER, ActionType.BLOCK]:
                results['filtered_content'] = self._filter_content(content, violations)
            
            results['explanation'] = self._generate_explanation(violations)
        
        return results
    
    def _detect_toxicity(self, content: str) -> Dict[str, Any]:
        """Detect toxic content"""
        result = {
            'type': ViolationType.TOXICITY,
            'detected': False,
            'confidence': 0.0,
            'severity': SeverityLevel.LOW,
            'details': {}
        }
        
        if 'toxicity' in self.models:
            try:
                prediction = self.models['toxicity'](content)
                toxic_score = next((p['score'] for p in prediction if p['label'] == 'TOXIC'), 0.0)
                
                if toxic_score > 0.7:
                    result['detected'] = True
                    result['confidence'] = toxic_score
                    result['severity'] = SeverityLevel.HIGH if toxic_score > 0.9 else SeverityLevel.MEDIUM
                    result['details'] = {'ml_score': toxic_score}
            except Exception as e:
                self.logger.error(f"Toxicity detection failed: {e}")
        
        # Fallback to rule-based detection
        if not result['detected']:
            toxic_words = ['toxic', 'poison', 'harmful', 'dangerous']
            found_words = [word for word in toxic_words if word.lower() in content.lower()]
            if found_words:
                result['detected'] = True
                result['confidence'] = 0.6
                result['severity'] = SeverityLevel.MEDIUM
                result['details'] = {'matched_words': found_words}
        
        return result
    
    def _detect_hate_speech(self, content: str) -> Dict[str, Any]:
        """Detect hate speech"""
        result = {
            'type': ViolationType.HATE_SPEECH,
            'detected': False,
            'confidence': 0.0,
            'severity': SeverityLevel.LOW,
            'details': {}
        }
        
        # Pattern-based detection
        for pattern in self.hate_speech_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                result['detected'] = True
                result['confidence'] = 0.8
                result['severity'] = SeverityLevel.HIGH
                result['details'] = {'matched_pattern': pattern}
                break
        
        return result
    
    def _detect_violence(self, content: str) -> Dict[str, Any]:
        """Detect violent content"""
        result = {
            'type': ViolationType.VIOLENCE,
            'detected': False,
            'confidence': 0.0,
            'severity': SeverityLevel.LOW,
            'details': {}
        }
        
        violence_count = 0
        matched_patterns = []
        
        for pattern in self.violence_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                violence_count += len(matches)
                matched_patterns.append(pattern)
        
        if violence_count > 0:
            result['detected'] = True
            result['confidence'] = min(0.9, violence_count * 0.3)
            # Make violence detection more sensitive
            result['severity'] = SeverityLevel.HIGH if violence_count >= 1 else SeverityLevel.MEDIUM
            result['details'] = {
                'violence_count': violence_count,
                'matched_patterns': matched_patterns
            }
        
        return result
    
    def _detect_profanity(self, content: str) -> Dict[str, Any]:
        """Detect profanity"""
        result = {
            'type': ViolationType.PROFANITY,
            'detected': False,
            'confidence': 0.0,
            'severity': SeverityLevel.LOW,
            'details': {}
        }
        
        found_profanity = []
        max_severity = SeverityLevel.LOW
        
        for severity, words in self.profanity_words.items():
            for word in words:
                if re.search(r'\b' + re.escape(word) + r'\b', content, re.IGNORECASE):
                    found_profanity.append({'word': word, 'severity': severity})
                    if severity == 'severe':
                        max_severity = SeverityLevel.HIGH
                    elif severity == 'moderate' and max_severity == SeverityLevel.LOW:
                        max_severity = SeverityLevel.MEDIUM
        
        if found_profanity:
            result['detected'] = True
            result['confidence'] = 0.9
            result['severity'] = max_severity
            result['details'] = {'found_words': found_profanity}
        
        return result
    
    def _detect_pii(self, content: str) -> Dict[str, Any]:
        """Detect personally identifiable information"""
        result = {
            'type': ViolationType.PII,
            'detected': False,
            'confidence': 0.0,
            'severity': SeverityLevel.MEDIUM,
            'details': {}
        }
        
        found_pii = []
        
        for pii_type, pattern in self.pii_patterns.items():
            matches = re.findall(pattern, content)
            if matches:
                found_pii.extend([{'type': pii_type, 'value': match} for match in matches])
        
        if found_pii:
            result['detected'] = True
            result['confidence'] = 0.95
            result['severity'] = SeverityLevel.HIGH
            result['details'] = {'found_pii': found_pii}
        
        return result
    
    def _determine_action(self, severity: SeverityLevel) -> ActionType:
        """Determine action based on severity"""
        if severity == SeverityLevel.CRITICAL:
            return ActionType.BLOCK
        elif severity == SeverityLevel.HIGH:
            return ActionType.FILTER
        elif severity == SeverityLevel.MEDIUM:
            return ActionType.WARN
        else:
            return ActionType.ALLOW
    
    def _filter_content(self, content: str, violations: List[Dict]) -> str:
        """Filter problematic content"""
        filtered = content
        
        for violation in violations:
            if violation['type'] == ViolationType.PII:
                # Replace PII with placeholders
                for pii in violation['details'].get('found_pii', []):
                    filtered = filtered.replace(pii['value'], f"[{pii['type'].upper()}]")
            
            elif violation['type'] == ViolationType.PROFANITY:
                # Replace profanity with asterisks
                for word_info in violation['details'].get('found_words', []):
                    word = word_info['word']
                    replacement = '*' * len(word)
                    filtered = re.sub(r'\b' + re.escape(word) + r'\b', replacement, filtered, flags=re.IGNORECASE)
        
        return filtered
    
    def _generate_explanation(self, violations: List[Dict]) -> str:
        """Generate human-readable explanation of violations"""
        if not violations:
            return "Content is safe"
        
        violation_types = [v['type'] for v in violations]
        type_counts = {vtype: violation_types.count(vtype) for vtype in set(violation_types)}
        
        explanations = []
        for vtype, count in type_counts.items():
            if count == 1:
                explanations.append(f"Contains {vtype.replace('_', ' ')}")
            else:
                explanations.append(f"Contains multiple instances of {vtype.replace('_', ' ')}")
        
        return "; ".join(explanations)


class BiasDetector:
    """Detect various types of bias in content"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._load_bias_indicators()
    
    def _load_bias_indicators(self):
        """Load bias detection patterns and word lists"""
        self.bias_indicators = {
            'gender': {
                'patterns': [
                    r'\b(men|women|male|female)\s+(are|is)\s+(better|worse|superior|inferior)',
                    r'\b(he|she)\s+(should|must|cannot)\s+\w+',
                ],
                'words': ['manly', 'feminine', 'girly', 'masculine']
            },
            'racial': {
                'patterns': [
                    r'\b(white|black|asian|hispanic)\s+(people|person)\s+(are|is)\s+\w+',
                ],
                'words': ['exotic', 'articulate', 'urban', 'ghetto']
            },
            'age': {
                'patterns': [
                    r'\b(young|old|elderly)\s+(people|person)\s+(are|is|cannot|should)',
                ],
                'words': ['boomer', 'millennial', 'outdated', 'inexperienced']
            },
            'religious': {
                'patterns': [
                    r'\b(christian|muslim|jewish|hindu|buddhist)\s+(are|is)\s+\w+',
                ],
                'words': ['extremist', 'fundamentalist', 'radical']
            }
        }
    
    def detect_bias(self, content: str, bias_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Detect bias in content
        
        Args:
            content: Text content to analyze
            bias_types: Specific bias types to check (if None, check all)
            
        Returns:
            Dictionary with bias detection results
        """
        if bias_types is None:
            bias_types = list(self.bias_indicators.keys())
        
        results = {
            'has_bias': False,
            'bias_results': [],
            'overall_bias_score': 0.0,
            'confidence_score': 0.0,
            'recommendations': []
        }
        
        bias_scores = []
        
        for bias_type in bias_types:
            if bias_type in self.bias_indicators:
                bias_result = self._detect_specific_bias(content, bias_type)
                if bias_result['detected']:
                    results['bias_results'].append(bias_result)
                    bias_scores.append(bias_result['score'])
        
        if bias_scores:
            results['has_bias'] = True
            results['overall_bias_score'] = max(bias_scores)
            results['confidence_score'] = sum(bias_scores) / len(bias_scores)
            results['recommendations'] = self._generate_bias_recommendations(results['bias_results'])
        
        return results
    
    def _detect_specific_bias(self, content: str, bias_type: str) -> Dict[str, Any]:
        """Detect specific type of bias"""
        indicators = self.bias_indicators[bias_type]
        
        result = {
            'bias_type': bias_type,
            'detected': False,
            'score': 0.0,
            'confidence': 0.0,
            'evidence': []
        }
        
        evidence = []
        
        # Check patterns
        for pattern in indicators['patterns']:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                evidence.extend([{'type': 'pattern', 'match': match, 'pattern': pattern} for match in matches])
        
        # Check bias words
        for word in indicators['words']:
            if re.search(r'\b' + re.escape(word) + r'\b', content, re.IGNORECASE):
                evidence.append({'type': 'word', 'word': word})
        
        if evidence:
            result['detected'] = True
            result['score'] = min(1.0, len(evidence) * 0.3)
            result['confidence'] = 0.7 if len(evidence) > 1 else 0.5
            result['evidence'] = evidence
        
        return result
    
    def _generate_bias_recommendations(self, bias_results: List[Dict]) -> List[str]:
        """Generate recommendations to reduce bias"""
        recommendations = []
        
        for result in bias_results:
            bias_type = result['bias_type']
            
            if bias_type == 'gender':
                recommendations.append("Consider using gender-neutral language")
                recommendations.append("Avoid assumptions based on gender")
            elif bias_type == 'racial':
                recommendations.append("Use inclusive language that doesn't stereotype")
                recommendations.append("Focus on individual characteristics rather than group generalizations")
            elif bias_type == 'age':
                recommendations.append("Avoid age-based assumptions about capabilities")
                recommendations.append("Use age-neutral descriptions when possible")
            elif bias_type == 'religious':
                recommendations.append("Respect religious diversity and avoid stereotypes")
                recommendations.append("Use neutral language when discussing religious topics")
        
        return list(set(recommendations))  # Remove duplicates


class ResponseValidator:
    """Validate AI responses for safety and appropriateness"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.content_moderator = ContentModerator()
        self.bias_detector = BiasDetector()
    
    def validate_response(self, response_text: str, prompt: Optional[str] = None, 
                         context: Optional[Dict] = None, 
                         validation_rules: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Validate AI response for safety and appropriateness
        
        Args:
            response_text: The AI response to validate
            prompt: Original prompt (optional)
            context: Additional context
            validation_rules: Specific validation rules to apply
            
        Returns:
            Dictionary with validation results
        """
        results = {
            'is_valid': True,
            'validation_results': [],
            'issues_found': [],
            'suggestions': [],
            'confidence_score': 1.0
        }
        
        issues = []
        suggestions = []
        validation_results = []
        
        # 1. Content moderation
        moderation_result = self.content_moderator.moderate_content(response_text, context)
        if not moderation_result['is_safe']:
            issues.append("Response contains inappropriate content")
            suggestions.append("Regenerate response with safer content")
            validation_results.append({
                'type': 'content_moderation',
                'passed': False,
                'details': moderation_result
            })
        else:
            validation_results.append({
                'type': 'content_moderation',
                'passed': True,
                'details': moderation_result
            })
        
        # 2. Bias detection
        bias_result = self.bias_detector.detect_bias(response_text)
        if bias_result['has_bias']:
            issues.append("Response contains potential bias")
            suggestions.extend(bias_result['recommendations'])
            validation_results.append({
                'type': 'bias_detection',
                'passed': False,
                'details': bias_result
            })
        else:
            validation_results.append({
                'type': 'bias_detection',
                'passed': True,
                'details': bias_result
            })
        
        # 3. Relevance check (if prompt provided)
        if prompt:
            relevance_result = self._check_relevance(response_text, prompt)
            if not relevance_result['is_relevant']:
                issues.append("Response is not relevant to the prompt")
                suggestions.append("Ensure response addresses the original question")
                validation_results.append({
                    'type': 'relevance_check',
                    'passed': False,
                    'details': relevance_result
                })
            else:
                validation_results.append({
                    'type': 'relevance_check',
                    'passed': True,
                    'details': relevance_result
                })
        
        # 4. Custom validation rules
        if validation_rules:
            for rule in validation_rules:
                rule_result = self._apply_validation_rule(response_text, rule)
                validation_results.append(rule_result)
                if not rule_result['passed']:
                    issues.append(f"Failed validation rule: {rule}")
        
        # Determine overall validity
        if issues:
            results['is_valid'] = False
            results['issues_found'] = issues
            results['suggestions'] = list(set(suggestions))
            
            # Calculate confidence based on number of failed validations
            failed_validations = sum(1 for v in validation_results if not v['passed'])
            results['confidence_score'] = max(0.0, 1.0 - (failed_validations * 0.3))
        
        results['validation_results'] = validation_results
        
        return results
    
    def _check_relevance(self, response: str, prompt: str) -> Dict[str, Any]:
        """Check if response is relevant to the prompt"""
        # Simple keyword-based relevance check
        # In production, use more sophisticated methods like semantic similarity
        
        response_words = set(word.lower() for word in response.split())
        prompt_words = set(word.lower() for word in prompt.split())
        
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        response_words -= stop_words
        prompt_words -= stop_words
        
        if not prompt_words:
            return {'is_relevant': True, 'similarity_score': 1.0}
        
        # Calculate word overlap
        overlap = len(response_words & prompt_words)
        similarity_score = overlap / len(prompt_words)
        
        return {
            'is_relevant': similarity_score > 0.1,  # At least 10% word overlap
            'similarity_score': similarity_score,
            'overlapping_words': list(response_words & prompt_words)
        }
    
    def _apply_validation_rule(self, response: str, rule: str) -> Dict[str, Any]:
        """Apply custom validation rule"""
        result = {
            'type': 'custom_rule',
            'rule': rule,
            'passed': True,
            'details': {}
        }
        
        # Simple rule implementations
        if rule == 'no_urls':
            url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
            if re.search(url_pattern, response):
                result['passed'] = False
                result['details'] = {'found_urls': re.findall(url_pattern, response)}
        
        elif rule == 'max_length_500':
            if len(response) > 500:
                result['passed'] = False
                result['details'] = {'length': len(response), 'max_allowed': 500}
        
        elif rule == 'no_personal_info':
            # Check for potential personal information
            personal_patterns = [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
                r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # Phone
                r'\b\d{3}-\d{2}-\d{4}\b'  # SSN
            ]
            
            found_info = []
            for pattern in personal_patterns:
                matches = re.findall(pattern, response)
                if matches:
                    found_info.extend(matches)
            
            if found_info:
                result['passed'] = False
                result['details'] = {'found_personal_info': found_info}
        
        return result


def generate_content_hash(content: str) -> str:
    """Generate a hash for content deduplication"""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]