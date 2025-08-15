from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class VectorStoreType(str, Enum):
    VERTEX_AI = "VERTEX_AI"
    PINECONE = "PINECONE"
    WEAVIATE = "WEAVIATE"
    QDRANT = "QDRANT"


class VectorStoreStatus(str, Enum):
    CREATED = "CREATED"
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    ERROR = "ERROR"
    DELETED = "DELETED"


class IndexingConfig(BaseModel):
    """Vector store indexing configuration"""
    dimension: int
    metric: str = "cosine"  # cosine, euclidean, dot_product
    index_type: str = "hnsw"
    parameters: Dict[str, Any] = Field(default_factory=dict)


class EmbeddingModelConfig(BaseModel):
    """Embedding model configuration"""
    model_id: str
    provider: str  # vertex-ai, openai, huggingface
    parameters: Dict[str, Any] = Field(default_factory=dict)
    max_batch_size: int = 100


class VectorStoreConfiguration(BaseModel):
    """Vector store configuration"""
    type: VectorStoreType
    connection_details: Dict[str, Any] = Field(default_factory=dict)
    indexing_parameters: IndexingConfig
    embedding_model: EmbeddingModelConfig
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChunkingStrategy(BaseModel):
    """Document chunking strategy"""
    method: str = "fixed_size"  # fixed_size, semantic, sentence
    chunk_size: int = 1000
    chunk_overlap: int = 200
    separators: List[str] = Field(default_factory=lambda: ["\n\n", "\n", " ", ""])
    metadata_keys: List[str] = Field(default_factory=list)


class DataSource(BaseModel):
    """Data source for embedding ingestion"""
    type: str  # text, file, url, database
    content: Optional[str] = None
    file_path: Optional[str] = None
    url: Optional[str] = None
    query: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class QueryFilter(BaseModel):
    """Filter for vector queries"""
    field: str
    operator: str  # eq, ne, gt, lt, gte, lte, in, nin
    value: Any


class VectorStoreStats(BaseModel):
    """Vector store statistics"""
    total_vectors: int = 0
    total_documents: int = 0
    index_size_mb: float = 0.0
    last_updated: Optional[datetime] = None
    query_count: int = 0
    avg_query_time_ms: float = 0.0


class VectorStore(BaseModel):
    """Vector store model"""
    id: str
    name: str
    type: VectorStoreType
    configuration: Dict[str, Any]
    status: VectorStoreStatus
    statistics: VectorStoreStats = Field(default_factory=VectorStoreStats)
    created_at: datetime
    updated_at: datetime


class Embedding(BaseModel):
    """Embedding record"""
    id: str
    vector_store_id: str
    document_id: str
    chunk_index: int
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    vector: List[float]
    created_at: datetime


class VectorStoreCreateRequest(BaseModel):
    """Request model for creating a vector store"""
    name: str = Field(..., min_length=1, max_length=100)
    configuration: VectorStoreConfiguration


class VectorStoreUpdateRequest(BaseModel):
    """Request model for updating a vector store"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    configuration: Optional[VectorStoreConfiguration] = None


class EmbeddingIngestionRequest(BaseModel):
    """Request model for embedding ingestion"""
    data_source: DataSource
    chunking_strategy: ChunkingStrategy = Field(default_factory=ChunkingStrategy)
    embedding_model_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VectorQuery(BaseModel):
    """Vector query request"""
    query_text: Optional[str] = None
    query_vector: Optional[List[float]] = None
    top_k: int = Field(default=10, ge=1, le=100)
    filters: List[QueryFilter] = Field(default_factory=list)
    include_metadata: bool = True
    include_content: bool = True


class VectorQueryResult(BaseModel):
    """Vector query result"""
    id: str
    document_id: str
    chunk_index: int
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    score: float
    vector: Optional[List[float]] = None


class VectorStoreResponse(BaseModel):
    """Response model for vector store operations"""
    vector_store: VectorStore


class VectorStoreListResponse(BaseModel):
    """Response model for listing vector stores"""
    vector_stores: List[VectorStore]
    total: int


class EmbeddingIngestionResponse(BaseModel):
    """Response model for embedding ingestion"""
    job_id: str
    status: str
    total_chunks: int
    processed_chunks: int = 0


class VectorQueryResponse(BaseModel):
    """Response model for vector queries"""
    results: List[VectorQueryResult]
    query_time_ms: float
    total_results: int