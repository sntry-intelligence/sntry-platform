import numpy as np
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging
import re
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """Document representation for vector storage"""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    created_at: Optional[datetime] = None


@dataclass
class DocumentChunk:
    """Document chunk for processing"""
    id: str
    document_id: str
    content: str
    chunk_index: int
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


@dataclass
class SearchResult:
    """Search result with similarity score"""
    document: Document
    score: float
    chunk_id: Optional[str] = None


class DocumentChunker:
    """Handles document chunking strategies"""
    
    def __init__(self):
        self.strategies = {
            'fixed_size': self._chunk_fixed_size,
            'sentence': self._chunk_by_sentence,
            'paragraph': self._chunk_by_paragraph,
            'semantic': self._chunk_semantic,
        }
    
    def chunk_document(
        self, 
        document: Document, 
        strategy: str = 'fixed_size',
        chunk_size: int = 512,
        overlap: int = 50
    ) -> List[DocumentChunk]:
        """Chunk document using specified strategy"""
        
        if strategy not in self.strategies:
            raise ValueError(f"Unknown chunking strategy: {strategy}")
        
        return self.strategies[strategy](document, chunk_size, overlap)
    
    def _chunk_fixed_size(
        self, 
        document: Document, 
        chunk_size: int, 
        overlap: int
    ) -> List[DocumentChunk]:
        """Chunk document into fixed-size pieces"""
        chunks = []
        content = document.content
        
        start = 0
        chunk_index = 0
        
        while start < len(content):
            end = min(start + chunk_size, len(content))
            chunk_content = content[start:end]
            
            chunk = DocumentChunk(
                id=f"{document.id}_chunk_{chunk_index}",
                document_id=document.id,
                content=chunk_content,
                chunk_index=chunk_index,
                metadata={
                    **document.metadata,
                    'chunk_strategy': 'fixed_size',
                    'chunk_size': chunk_size,
                    'overlap': overlap,
                    'start_pos': start,
                    'end_pos': end
                }
            )
            chunks.append(chunk)
            
            start = end - overlap
            chunk_index += 1
            
            if start >= len(content):
                break
        
        return chunks
    
    def _chunk_by_sentence(
        self, 
        document: Document, 
        chunk_size: int, 
        overlap: int
    ) -> List[DocumentChunk]:
        """Chunk document by sentences"""
        # Simple sentence splitting (in production, use proper NLP library)
        sentences = re.split(r'[.!?]+', document.content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        chunks = []
        current_chunk = []
        current_length = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            if current_length + sentence_length > chunk_size and current_chunk:
                # Create chunk from current sentences
                chunk_content = '. '.join(current_chunk) + '.'
                chunk = DocumentChunk(
                    id=f"{document.id}_chunk_{chunk_index}",
                    document_id=document.id,
                    content=chunk_content,
                    chunk_index=chunk_index,
                    metadata={
                        **document.metadata,
                        'chunk_strategy': 'sentence',
                        'sentence_count': len(current_chunk)
                    }
                )
                chunks.append(chunk)
                
                # Handle overlap
                if overlap > 0 and len(current_chunk) > 1:
                    overlap_sentences = current_chunk[-overlap:]
                    current_chunk = overlap_sentences + [sentence]
                    current_length = sum(len(s) for s in current_chunk)
                else:
                    current_chunk = [sentence]
                    current_length = sentence_length
                
                chunk_index += 1
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
        
        # Add remaining sentences as final chunk
        if current_chunk:
            chunk_content = '. '.join(current_chunk) + '.'
            chunk = DocumentChunk(
                id=f"{document.id}_chunk_{chunk_index}",
                document_id=document.id,
                content=chunk_content,
                chunk_index=chunk_index,
                metadata={
                    **document.metadata,
                    'chunk_strategy': 'sentence',
                    'sentence_count': len(current_chunk)
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def _chunk_by_paragraph(
        self, 
        document: Document, 
        chunk_size: int, 
        overlap: int
    ) -> List[DocumentChunk]:
        """Chunk document by paragraphs"""
        paragraphs = document.content.split('\n\n')
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        chunks = []
        current_chunk = []
        current_length = 0
        chunk_index = 0
        
        for paragraph in paragraphs:
            paragraph_length = len(paragraph)
            
            if current_length + paragraph_length > chunk_size and current_chunk:
                # Create chunk from current paragraphs
                chunk_content = '\n\n'.join(current_chunk)
                chunk = DocumentChunk(
                    id=f"{document.id}_chunk_{chunk_index}",
                    document_id=document.id,
                    content=chunk_content,
                    chunk_index=chunk_index,
                    metadata={
                        **document.metadata,
                        'chunk_strategy': 'paragraph',
                        'paragraph_count': len(current_chunk)
                    }
                )
                chunks.append(chunk)
                
                # Handle overlap
                if overlap > 0 and len(current_chunk) > 1:
                    overlap_paragraphs = current_chunk[-overlap:]
                    current_chunk = overlap_paragraphs + [paragraph]
                    current_length = sum(len(p) for p in current_chunk)
                else:
                    current_chunk = [paragraph]
                    current_length = paragraph_length
                
                chunk_index += 1
            else:
                current_chunk.append(paragraph)
                current_length += paragraph_length
        
        # Add remaining paragraphs as final chunk
        if current_chunk:
            chunk_content = '\n\n'.join(current_chunk)
            chunk = DocumentChunk(
                id=f"{document.id}_chunk_{chunk_index}",
                document_id=document.id,
                content=chunk_content,
                chunk_index=chunk_index,
                metadata={
                    **document.metadata,
                    'chunk_strategy': 'paragraph',
                    'paragraph_count': len(current_chunk)
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def _chunk_semantic(
        self, 
        document: Document, 
        chunk_size: int, 
        overlap: int
    ) -> List[DocumentChunk]:
        """Semantic chunking (simplified version)"""
        # This is a simplified semantic chunking
        # In production, would use proper semantic analysis
        
        # For now, combine sentence and paragraph strategies
        sentences = re.split(r'[.!?]+', document.content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        chunks = []
        current_chunk = []
        current_length = 0
        chunk_index = 0
        
        for i, sentence in enumerate(sentences):
            sentence_length = len(sentence)
            
            # Simple semantic boundary detection (look for topic changes)
            is_topic_boundary = self._detect_topic_boundary(sentence, sentences[i-1] if i > 0 else "")
            
            if (current_length + sentence_length > chunk_size or is_topic_boundary) and current_chunk:
                # Create chunk
                chunk_content = '. '.join(current_chunk) + '.'
                chunk = DocumentChunk(
                    id=f"{document.id}_chunk_{chunk_index}",
                    document_id=document.id,
                    content=chunk_content,
                    chunk_index=chunk_index,
                    metadata={
                        **document.metadata,
                        'chunk_strategy': 'semantic',
                        'sentence_count': len(current_chunk),
                        'topic_boundary': is_topic_boundary
                    }
                )
                chunks.append(chunk)
                
                current_chunk = [sentence]
                current_length = sentence_length
                chunk_index += 1
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
        
        # Add remaining sentences
        if current_chunk:
            chunk_content = '. '.join(current_chunk) + '.'
            chunk = DocumentChunk(
                id=f"{document.id}_chunk_{chunk_index}",
                document_id=document.id,
                content=chunk_content,
                chunk_index=chunk_index,
                metadata={
                    **document.metadata,
                    'chunk_strategy': 'semantic',
                    'sentence_count': len(current_chunk)
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def _detect_topic_boundary(self, current_sentence: str, previous_sentence: str) -> bool:
        """Simple topic boundary detection"""
        # Look for transition words/phrases
        transition_words = [
            'however', 'moreover', 'furthermore', 'in addition', 'on the other hand',
            'meanwhile', 'subsequently', 'consequently', 'therefore', 'in conclusion',
            'first', 'second', 'third', 'finally', 'next', 'then'
        ]
        
        current_lower = current_sentence.lower()
        for word in transition_words:
            if current_lower.startswith(word):
                return True
        
        return False


class SimpleEmbeddingGenerator:
    """Simple embedding generator (in production, use proper models like sentence-transformers)"""
    
    def __init__(self, embedding_dim: int = 384):
        self.embedding_dim = embedding_dim
        # Simple vocabulary for demonstration
        self.vocab = {}
        self.vocab_size = 10000
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text (simplified version)"""
        # This is a very simplified embedding generation
        # In production, use proper models like sentence-transformers, OpenAI embeddings, etc.
        
        # Create a simple hash-based embedding
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        # Convert hash to numbers and normalize
        embedding = []
        for i in range(0, len(text_hash), 2):
            hex_pair = text_hash[i:i+2]
            value = int(hex_pair, 16) / 255.0  # Normalize to 0-1
            embedding.append(value)
        
        # Pad or truncate to desired dimension
        while len(embedding) < self.embedding_dim:
            embedding.extend(embedding[:min(len(embedding), self.embedding_dim - len(embedding))])
        
        embedding = embedding[:self.embedding_dim]
        
        # Add some text-based features
        text_lower = text.lower()
        word_count = len(text.split())
        char_count = len(text)
        
        # Modify embedding based on text characteristics
        if word_count > 0:
            embedding[0] = min(1.0, word_count / 100.0)  # Word count feature
        if char_count > 0:
            embedding[1] = min(1.0, char_count / 1000.0)  # Character count feature
        
        # Normalize the embedding
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = [x / norm for x in embedding]
        
        return embedding
    
    def batch_generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        return [self.generate_embedding(text) for text in texts]


class VectorDatabase:
    """Simple in-memory vector database (in production, use Pinecone, Weaviate, etc.)"""
    
    def __init__(self, embedding_dim: int = 384):
        self.embedding_dim = embedding_dim
        self.documents: Dict[str, Document] = {}
        self.chunks: Dict[str, DocumentChunk] = {}
        self.embeddings: Dict[str, np.ndarray] = {}
        self.embedding_generator = SimpleEmbeddingGenerator(embedding_dim)
        self.chunker = DocumentChunker()
    
    def add_document(
        self, 
        content: str, 
        metadata: Dict[str, Any], 
        document_id: Optional[str] = None,
        chunking_strategy: str = 'fixed_size',
        chunk_size: int = 512,
        overlap: int = 50
    ) -> str:
        """Add document to vector database"""
        
        if document_id is None:
            document_id = str(uuid.uuid4())
        
        # Create document
        document = Document(
            id=document_id,
            content=content,
            metadata=metadata,
            created_at=datetime.utcnow()
        )
        
        # Generate document embedding
        document.embedding = self.embedding_generator.generate_embedding(content)
        
        # Store document
        self.documents[document_id] = document
        self.embeddings[document_id] = np.array(document.embedding)
        
        # Chunk document
        chunks = self.chunker.chunk_document(
            document, 
            strategy=chunking_strategy,
            chunk_size=chunk_size,
            overlap=overlap
        )
        
        # Generate embeddings for chunks and store them
        for chunk in chunks:
            chunk.embedding = self.embedding_generator.generate_embedding(chunk.content)
            self.chunks[chunk.id] = chunk
            self.embeddings[chunk.id] = np.array(chunk.embedding)
        
        logger.info(f"Added document {document_id} with {len(chunks)} chunks")
        return document_id
    
    def search(
        self, 
        query: str, 
        top_k: int = 5,
        search_chunks: bool = True,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search for similar documents/chunks"""
        
        # Generate query embedding
        query_embedding = np.array(self.embedding_generator.generate_embedding(query))
        
        results = []
        
        # Search in chunks if requested
        if search_chunks:
            for chunk_id, chunk in self.chunks.items():
                # Apply metadata filter if provided
                if metadata_filter and not self._matches_filter(chunk.metadata, metadata_filter):
                    continue
                
                # Calculate similarity
                chunk_embedding = self.embeddings[chunk_id]
                similarity = self._cosine_similarity(query_embedding, chunk_embedding)
                
                # Get parent document
                document = self.documents[chunk.document_id]
                
                result = SearchResult(
                    document=document,
                    score=similarity,
                    chunk_id=chunk_id
                )
                results.append(result)
        else:
            # Search in full documents
            for doc_id, document in self.documents.items():
                # Apply metadata filter if provided
                if metadata_filter and not self._matches_filter(document.metadata, metadata_filter):
                    continue
                
                # Calculate similarity
                doc_embedding = self.embeddings[doc_id]
                similarity = self._cosine_similarity(query_embedding, doc_embedding)
                
                result = SearchResult(
                    document=document,
                    score=similarity
                )
                results.append(result)
        
        # Sort by similarity score (descending)
        results.sort(key=lambda x: x.score, reverse=True)
        
        return results[:top_k]
    
    def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Hybrid search combining semantic and keyword matching"""
        
        # Get semantic search results
        semantic_results = self.search(query, top_k * 2, metadata_filter=metadata_filter)
        
        # Get keyword search results
        keyword_results = self._keyword_search(query, top_k * 2, metadata_filter)
        
        # Combine and rerank results
        combined_scores = {}
        
        # Add semantic scores
        for result in semantic_results:
            key = result.chunk_id or result.document.id
            combined_scores[key] = {
                'result': result,
                'semantic_score': result.score,
                'keyword_score': 0.0
            }
        
        # Add keyword scores
        for result in keyword_results:
            key = result.chunk_id or result.document.id
            if key in combined_scores:
                combined_scores[key]['keyword_score'] = result.score
            else:
                combined_scores[key] = {
                    'result': result,
                    'semantic_score': 0.0,
                    'keyword_score': result.score
                }
        
        # Calculate combined scores
        final_results = []
        for key, scores in combined_scores.items():
            combined_score = (
                semantic_weight * scores['semantic_score'] +
                keyword_weight * scores['keyword_score']
            )
            
            result = scores['result']
            result.score = combined_score
            final_results.append(result)
        
        # Sort by combined score
        final_results.sort(key=lambda x: x.score, reverse=True)
        
        return final_results[:top_k]
    
    def _keyword_search(
        self,
        query: str,
        top_k: int,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Simple keyword-based search"""
        
        query_words = set(query.lower().split())
        results = []
        
        # Search in chunks
        for chunk_id, chunk in self.chunks.items():
            # Apply metadata filter if provided
            if metadata_filter and not self._matches_filter(chunk.metadata, metadata_filter):
                continue
            
            # Calculate keyword overlap
            chunk_words = set(chunk.content.lower().split())
            overlap = len(query_words.intersection(chunk_words))
            score = overlap / len(query_words) if query_words else 0
            
            if score > 0:
                document = self.documents[chunk.document_id]
                result = SearchResult(
                    document=document,
                    score=score,
                    chunk_id=chunk_id
                )
                results.append(result)
        
        # Sort by keyword score
        results.sort(key=lambda x: x.score, reverse=True)
        
        return results[:top_k]
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)
    
    def _matches_filter(self, metadata: Dict[str, Any], filter_dict: Dict[str, Any]) -> bool:
        """Check if metadata matches filter criteria"""
        for key, value in filter_dict.items():
            if key not in metadata or metadata[key] != value:
                return False
        return True
    
    def get_document(self, document_id: str) -> Optional[Document]:
        """Get document by ID"""
        return self.documents.get(document_id)
    
    def get_chunk(self, chunk_id: str) -> Optional[DocumentChunk]:
        """Get chunk by ID"""
        return self.chunks.get(chunk_id)
    
    def delete_document(self, document_id: str) -> bool:
        """Delete document and its chunks"""
        if document_id not in self.documents:
            return False
        
        # Remove document
        del self.documents[document_id]
        del self.embeddings[document_id]
        
        # Remove associated chunks
        chunks_to_remove = [
            chunk_id for chunk_id, chunk in self.chunks.items()
            if chunk.document_id == document_id
        ]
        
        for chunk_id in chunks_to_remove:
            del self.chunks[chunk_id]
            del self.embeddings[chunk_id]
        
        logger.info(f"Deleted document {document_id} and {len(chunks_to_remove)} chunks")
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        return {
            'total_documents': len(self.documents),
            'total_chunks': len(self.chunks),
            'embedding_dimension': self.embedding_dim,
            'total_embeddings': len(self.embeddings)
        }


class KnowledgeManager:
    """High-level knowledge management interface"""
    
    def __init__(self, vector_db: Optional[VectorDatabase] = None):
        self.vector_db = vector_db or VectorDatabase()
    
    def ingest_documents(
        self,
        documents: List[Dict[str, Any]],
        chunking_strategy: str = 'fixed_size',
        chunk_size: int = 512,
        overlap: int = 50
    ) -> List[str]:
        """Ingest multiple documents"""
        
        document_ids = []
        
        for doc_data in documents:
            content = doc_data.get('content', '')
            metadata = doc_data.get('metadata', {})
            doc_id = doc_data.get('id')
            
            if not content:
                logger.warning("Skipping document with empty content")
                continue
            
            document_id = self.vector_db.add_document(
                content=content,
                metadata=metadata,
                document_id=doc_id,
                chunking_strategy=chunking_strategy,
                chunk_size=chunk_size,
                overlap=overlap
            )
            
            document_ids.append(document_id)
        
        logger.info(f"Ingested {len(document_ids)} documents")
        return document_ids
    
    def search_knowledge(
        self,
        query: str,
        search_type: str = 'semantic',
        top_k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search knowledge base"""
        
        if search_type == 'semantic':
            results = self.vector_db.search(
                query=query,
                top_k=top_k,
                search_chunks=True,
                metadata_filter=metadata_filter
            )
        elif search_type == 'hybrid':
            results = self.vector_db.hybrid_search(
                query=query,
                top_k=top_k,
                metadata_filter=metadata_filter
            )
        else:
            raise ValueError(f"Unknown search type: {search_type}")
        
        # Format results
        formatted_results = []
        for result in results:
            chunk = None
            if result.chunk_id:
                chunk = self.vector_db.get_chunk(result.chunk_id)
            
            formatted_result = {
                'document_id': result.document.id,
                'content': chunk.content if chunk else result.document.content,
                'score': result.score,
                'metadata': result.document.metadata,
                'chunk_id': result.chunk_id,
                'chunk_index': chunk.chunk_index if chunk else None
            }
            formatted_results.append(formatted_result)
        
        return formatted_results
    
    def get_knowledge_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        return self.vector_db.get_stats()