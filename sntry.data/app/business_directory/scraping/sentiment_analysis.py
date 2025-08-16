"""
Sentiment Analysis for Social Media Business Data
Analyzes sentiment of business reviews and mentions from social media
"""
import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SentimentScore(Enum):
    """Sentiment classification levels"""
    VERY_POSITIVE = 5
    POSITIVE = 4
    NEUTRAL = 3
    NEGATIVE = 2
    VERY_NEGATIVE = 1


@dataclass
class SentimentResult:
    """Result of sentiment analysis"""
    score: SentimentScore
    confidence: float
    positive_words: List[str]
    negative_words: List[str]
    overall_sentiment: str
    
    def to_dict(self) -> Dict:
        return {
            "score": self.score.value,
            "confidence": self.confidence,
            "positive_words": self.positive_words,
            "negative_words": self.negative_words,
            "overall_sentiment": self.overall_sentiment
        }


class SimpleSentimentAnalyzer:
    """
    Simple rule-based sentiment analyzer for business reviews
    
    This is a basic implementation. For production use, consider:
    - Using pre-trained models like VADER, TextBlob, or transformers
    - Training custom models on business review data
    - Using cloud APIs like Google Cloud Natural Language or AWS Comprehend
    """
    
    def __init__(self):
        # Jamaican business context positive words
        self.positive_words = {
            'excellent', 'amazing', 'fantastic', 'wonderful', 'great', 'good', 'nice',
            'awesome', 'outstanding', 'superb', 'brilliant', 'perfect', 'love', 'loved',
            'best', 'favorite', 'favourite', 'recommend', 'recommended', 'delicious',
            'tasty', 'fresh', 'clean', 'friendly', 'helpful', 'professional', 'quality',
            'satisfied', 'happy', 'pleased', 'impressed', 'beautiful', 'gorgeous',
            'stunning', 'incredible', 'phenomenal', 'exceptional', 'marvelous',
            'spectacular', 'divine', 'heavenly', 'scrumptious', 'yummy', 'irie',
            'wicked', 'cool', 'nice', 'sweet', 'blessed', 'top', 'premium',
            'authentic', 'genuine', 'reliable', 'trustworthy', 'efficient', 'fast',
            'quick', 'convenient', 'comfortable', 'cozy', 'welcoming', 'warm'
        }
        
        # Jamaican business context negative words
        self.negative_words = {
            'terrible', 'awful', 'horrible', 'bad', 'worst', 'hate', 'hated',
            'disgusting', 'nasty', 'gross', 'dirty', 'filthy', 'rude', 'unfriendly',
            'unprofessional', 'slow', 'expensive', 'overpriced', 'cheap', 'poor',
            'disappointing', 'disappointed', 'unsatisfied', 'unhappy', 'angry',
            'frustrated', 'annoyed', 'irritated', 'upset', 'mad', 'furious',
            'pathetic', 'useless', 'worthless', 'garbage', 'trash', 'waste',
            'scam', 'fraud', 'fake', 'dishonest', 'unreliable', 'untrustworthy',
            'incompetent', 'careless', 'sloppy', 'messy', 'cold', 'stale',
            'bland', 'tasteless', 'overcooked', 'undercooked', 'burnt', 'raw',
            'cramped', 'uncomfortable', 'noisy', 'loud', 'crowded', 'chaotic'
        }
        
        # Intensifiers that modify sentiment strength
        self.intensifiers = {
            'very': 1.5, 'extremely': 2.0, 'incredibly': 1.8, 'absolutely': 1.7,
            'totally': 1.6, 'completely': 1.7, 'really': 1.3, 'quite': 1.2,
            'pretty': 1.1, 'somewhat': 0.8, 'rather': 0.9, 'fairly': 0.9,
            'super': 1.8, 'ultra': 2.0, 'mega': 1.9, 'so': 1.4, 'too': 1.3
        }
        
        # Negation words that flip sentiment
        self.negations = {
            'not', 'no', 'never', 'nothing', 'nobody', 'nowhere', 'neither',
            'nor', 'none', 'hardly', 'scarcely', 'barely', 'seldom', 'rarely',
            'without', 'lack', 'lacking', 'missing', 'absent', 'void', 'empty'
        }
    
    def analyze_text(self, text: str) -> SentimentResult:
        """
        Analyze sentiment of a text string
        
        Args:
            text: Text to analyze (review, comment, etc.)
            
        Returns:
            SentimentResult with sentiment classification and details
        """
        if not text or not text.strip():
            return SentimentResult(
                score=SentimentScore.NEUTRAL,
                confidence=0.0,
                positive_words=[],
                negative_words=[],
                overall_sentiment="neutral"
            )
        
        # Clean and tokenize text
        cleaned_text = self._clean_text(text)
        words = cleaned_text.lower().split()
        
        # Find sentiment words
        positive_found = []
        negative_found = []
        
        # Track context for negations and intensifiers
        sentiment_score = 0.0
        word_count = len(words)
        
        for i, word in enumerate(words):
            # Check for sentiment words
            base_score = 0
            if word in self.positive_words:
                positive_found.append(word)
                base_score = 1.0
            elif word in self.negative_words:
                negative_found.append(word)
                base_score = -1.0
            
            if base_score != 0:
                # Check for intensifiers in the previous 2 words
                intensifier_multiplier = 1.0
                for j in range(max(0, i-2), i):
                    if words[j] in self.intensifiers:
                        intensifier_multiplier = max(intensifier_multiplier, self.intensifiers[words[j]])
                
                # Check for negations in the previous 3 words
                is_negated = False
                for j in range(max(0, i-3), i):
                    if words[j] in self.negations:
                        is_negated = True
                        break
                
                # Apply modifiers
                final_score = base_score * intensifier_multiplier
                if is_negated:
                    final_score *= -1
                
                sentiment_score += final_score
        
        # Normalize score based on text length
        if word_count > 0:
            normalized_score = sentiment_score / word_count
        else:
            normalized_score = 0.0
        
        # Classify sentiment
        sentiment_classification = self._classify_sentiment(normalized_score)
        
        # Calculate confidence based on number of sentiment words found
        total_sentiment_words = len(positive_found) + len(negative_found)
        confidence = min(1.0, total_sentiment_words / max(1, word_count / 10))
        
        return SentimentResult(
            score=sentiment_classification,
            confidence=confidence,
            positive_words=positive_found,
            negative_words=negative_found,
            overall_sentiment=sentiment_classification.name.lower().replace('_', ' ')
        )
    
    def _clean_text(self, text: str) -> str:
        """Clean text for analysis"""
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove mentions and hashtags (keep the text part)
        text = re.sub(r'[@#](\w+)', r'\1', text)
        
        # Remove extra whitespace and punctuation
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _classify_sentiment(self, score: float) -> SentimentScore:
        """Classify normalized sentiment score into categories"""
        if score >= 0.3:
            return SentimentScore.VERY_POSITIVE
        elif score >= 0.1:
            return SentimentScore.POSITIVE
        elif score <= -0.3:
            return SentimentScore.VERY_NEGATIVE
        elif score <= -0.1:
            return SentimentScore.NEGATIVE
        else:
            return SentimentScore.NEUTRAL
    
    def analyze_business_reviews(self, reviews: List[str]) -> Dict[str, any]:
        """
        Analyze sentiment across multiple business reviews
        
        Args:
            reviews: List of review texts
            
        Returns:
            Dictionary with aggregated sentiment analysis
        """
        if not reviews:
            return {
                "overall_sentiment": "neutral",
                "average_score": 3.0,
                "sentiment_distribution": {},
                "confidence": 0.0,
                "total_reviews": 0,
                "common_positive_words": [],
                "common_negative_words": []
            }
        
        results = []
        all_positive_words = []
        all_negative_words = []
        
        for review in reviews:
            result = self.analyze_text(review)
            results.append(result)
            all_positive_words.extend(result.positive_words)
            all_negative_words.extend(result.negative_words)
        
        # Calculate aggregated metrics
        scores = [result.score.value for result in results]
        average_score = sum(scores) / len(scores)
        
        # Sentiment distribution
        sentiment_counts = {}
        for result in results:
            sentiment = result.overall_sentiment
            sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
        
        # Most common sentiment words
        from collections import Counter
        common_positive = [word for word, count in Counter(all_positive_words).most_common(10)]
        common_negative = [word for word, count in Counter(all_negative_words).most_common(10)]
        
        # Overall confidence
        average_confidence = sum(result.confidence for result in results) / len(results)
        
        # Determine overall sentiment
        if average_score >= 4:
            overall_sentiment = "very positive"
        elif average_score >= 3.5:
            overall_sentiment = "positive"
        elif average_score <= 2:
            overall_sentiment = "very negative"
        elif average_score <= 2.5:
            overall_sentiment = "negative"
        else:
            overall_sentiment = "neutral"
        
        return {
            "overall_sentiment": overall_sentiment,
            "average_score": round(average_score, 2),
            "sentiment_distribution": sentiment_counts,
            "confidence": round(average_confidence, 2),
            "total_reviews": len(reviews),
            "common_positive_words": common_positive,
            "common_negative_words": common_negative,
            "detailed_results": [result.to_dict() for result in results]
        }


class BusinessSentimentAnalyzer:
    """
    Specialized sentiment analyzer for business social media data
    """
    
    def __init__(self):
        self.analyzer = SimpleSentimentAnalyzer()
    
    def analyze_business_mentions(self, mentions: List[str], business_name: str) -> Dict[str, any]:
        """
        Analyze sentiment of social media mentions for a specific business
        
        Args:
            mentions: List of social media posts/comments mentioning the business
            business_name: Name of the business being analyzed
            
        Returns:
            Sentiment analysis results focused on business reputation
        """
        # Filter mentions that actually reference the business
        relevant_mentions = []
        business_name_lower = business_name.lower()
        
        for mention in mentions:
            if business_name_lower in mention.lower():
                relevant_mentions.append(mention)
        
        if not relevant_mentions:
            return {
                "business_name": business_name,
                "relevant_mentions": 0,
                "sentiment_summary": "No relevant mentions found"
            }
        
        # Analyze sentiment of relevant mentions
        sentiment_results = self.analyzer.analyze_business_reviews(relevant_mentions)
        
        # Add business-specific context
        sentiment_results.update({
            "business_name": business_name,
            "relevant_mentions": len(relevant_mentions),
            "total_mentions_analyzed": len(mentions),
            "mention_relevance_rate": len(relevant_mentions) / len(mentions) if mentions else 0
        })
        
        return sentiment_results
    
    def get_reputation_score(self, sentiment_analysis: Dict[str, any]) -> Tuple[float, str]:
        """
        Calculate a business reputation score based on sentiment analysis
        
        Args:
            sentiment_analysis: Results from analyze_business_mentions
            
        Returns:
            Tuple of (reputation_score, reputation_level)
            Score is 0-100, level is text description
        """
        if sentiment_analysis.get("total_reviews", 0) == 0:
            return 50.0, "Unknown"
        
        average_score = sentiment_analysis.get("average_score", 3.0)
        confidence = sentiment_analysis.get("confidence", 0.0)
        
        # Convert 1-5 scale to 0-100 scale
        base_score = ((average_score - 1) / 4) * 100
        
        # Adjust based on confidence
        adjusted_score = base_score * (0.5 + 0.5 * confidence)
        
        # Determine reputation level
        if adjusted_score >= 80:
            level = "Excellent"
        elif adjusted_score >= 65:
            level = "Good"
        elif adjusted_score >= 50:
            level = "Average"
        elif adjusted_score >= 35:
            level = "Poor"
        else:
            level = "Very Poor"
        
        return round(adjusted_score, 1), level


# Convenience functions
def analyze_business_sentiment(reviews: List[str]) -> Dict[str, any]:
    """Quick sentiment analysis for business reviews"""
    analyzer = SimpleSentimentAnalyzer()
    return analyzer.analyze_business_reviews(reviews)


def get_business_reputation_score(mentions: List[str], business_name: str) -> Tuple[float, str]:
    """Quick reputation score calculation"""
    analyzer = BusinessSentimentAnalyzer()
    sentiment_results = analyzer.analyze_business_mentions(mentions, business_name)
    return analyzer.get_reputation_score(sentiment_results)