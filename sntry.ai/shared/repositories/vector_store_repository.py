from typing import Any, Dict, List, Optional
from prisma import Prisma
from prisma.models import VectorStore, Embedding
from shared.models.base import PaginationParams
from shared.models.vector_store import VectorStoreStatus, VectorStoreType
from .base import CacheableRepository, AuditableRepository


class VectorStoreRepository(CacheableRepository[VectorStore], AuditableRepository[VectorStore]):
    """Repository for VectorStore entities"""
    
    def __init__(self, db: Prisma):
        super().__init__(db, cache_ttl=600)  # 10 minutes cache
    
    async def create(self, data: Dict[str, Any]) -> VectorStore:
        """Create a new vector store"""
        vector_store = await self.db.vectorstore.create(data=data)
        
        # Cache the new vector store
        cache_key = self._get_cache_key("id", vector_store.id)
        await self._set_cache(cache_key, vector_store.dict())
        
        # Create audit log
        await self._create_audit_log(
            action="CREATE",
            entity_id=vector_store.id,
            entity_type="VectorStore",
            new_data=vector_store.dict()
        )
        
        return vector_store
    
    async def get_by_id(self, id: str) -> Optional[VectorStore]:
        """Get vector store by ID with caching"""
        # Try cache first
        cache_key = self._get_cache_key("id", id)
        cached_store = await self._get_from_cache(cache_key)
        if cached_store:
            return VectorStore(**cached_store)
        
        # Fetch from database
        vector_store = await self.db.vectorstore.find_unique(where={"id": id})
        if vector_store:
            await self._set_cache(cache_key, vector_store.dict())
        
        return vector_store
    
    async def update(self, id: str, data: Dict[str, Any]) -> Optional[VectorStore]:
        """Update vector store by ID"""
        # Get old data for audit
        old_store = await self.get_by_id(id)
        if not old_store:
            return None
        
        # Update vector store
        updated_store = await self.db.vectorstore.update(
            where={"id": id},
            data=data
        )
        
        # Invalidate cache
        await self.invalidate_cache(id)
        
        # Create audit log
        await self._create_audit_log(
            action="UPDATE",
            entity_id=id,
            entity_type="VectorStore",
            old_data=old_store.dict(),
            new_data=updated_store.dict()
        )
        
        return updated_store
    
    async def delete(self, id: str) -> bool:
        """Delete vector store by ID"""
        # Get store for audit
        vector_store = await self.get_by_id(id)
        if not vector_store:
            return False
        
        # Delete vector store (cascade will handle embeddings)
        await self.db.vectorstore.delete(where={"id": id})
        
        # Invalidate cache
        await self.invalidate_cache(id)
        
        # Create audit log
        await self._create_audit_log(
            action="DELETE",
            entity_id=id,
            entity_type="VectorStore",
            old_data=vector_store.dict()
        )
        
        return True
    
    async def list(
        self,
        pagination: PaginationParams,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[Dict[str, str]] = None
    ) -> tuple[List[VectorStore], int]:
        """List vector stores with pagination and filtering"""
        skip, take = self._calculate_pagination(pagination)
        where = self._build_where_clause(filters)
        order = self._build_order_by(order_by)
        
        # Get vector stores and total count
        stores, total = await self.db.vectorstore.find_many_and_count(
            where=where,
            skip=skip,
            take=take,
            order=order
        )
        
        return stores, total
    
    async def exists(self, id: str) -> bool:
        """Check if vector store exists"""
        store = await self.db.vectorstore.find_unique(
            where={"id": id},
            select={"id": True}
        )
        return store is not None
    
    async def get_by_name(self, name: str) -> Optional[VectorStore]:
        """Get vector store by name"""
        return await self.db.vectorstore.find_first(where={"name": name})
    
    async def get_by_type(self, store_type: VectorStoreType) -> List[VectorStore]:
        """Get vector stores by type"""
        return await self.db.vectorstore.find_many(where={"type": store_type})
    
    async def get_by_status(self, status: VectorStoreStatus) -> List[VectorStore]:
        """Get vector stores by status"""
        return await self.db.vectorstore.find_many(where={"status": status})
    
    async def update_status(self, id: str, status: VectorStoreStatus) -> Optional[VectorStore]:
        """Update vector store status"""
        return await self.update(id, {"status": status, "updated_at": "now()"})
    
    async def update_statistics(
        self,
        id: str,
        statistics: Dict[str, Any]
    ) -> Optional[VectorStore]:
        """Update vector store statistics"""
        return await self.update(id, {
            "statistics": statistics,
            "updated_at": "now()"
        })
    
    async def get_ready_stores(self) -> List[VectorStore]:
        """Get all ready vector stores"""
        return await self.db.vectorstore.find_many(
            where={"status": VectorStoreStatus.READY}
        )
    
    async def search_stores(
        self,
        query: str,
        pagination: PaginationParams
    ) -> tuple[List[VectorStore], int]:
        """Search vector stores by name"""
        skip, take = self._calculate_pagination(pagination)
        
        where = {
            "name": {"contains": query, "mode": "insensitive"}
        }
        
        stores, total = await self.db.vectorstore.find_many_and_count(
            where=where,
            skip=skip,
            take=take,
            order=[{"updated_at": "desc"}]
        )
        
        return stores, total


class EmbeddingRepository(CacheableRepository[Embedding], AuditableRepository[Embedding]):
    """Repository for Embedding entities"""
    
    def __init__(self, db: Prisma):
        super().__init__(db, cache_ttl=300)  # 5 minutes cache
    
    async def create(self, data: Dict[str, Any]) -> Embedding:
        """Create a new embedding"""
        embedding = await self.db.embedding.create(data=data)
        
        # Update vector store statistics
        await self._update_vector_store_stats(embedding.vector_store_id)
        
        # Cache the new embedding
        cache_key = self._get_cache_key("id", embedding.id)
        await self._set_cache(cache_key, embedding.dict())
        
        # Create audit log
        await self._create_audit_log(
            action="CREATE",
            entity_id=embedding.id,
            entity_type="Embedding",
            new_data=embedding.dict()
        )
        
        return embedding
    
    async def get_by_id(self, id: str) -> Optional[Embedding]:
        """Get embedding by ID with caching"""
        # Try cache first
        cache_key = self._get_cache_key("id", id)
        cached_embedding = await self._get_from_cache(cache_key)
        if cached_embedding:
            return Embedding(**cached_embedding)
        
        # Fetch from database
        embedding = await self.db.embedding.find_unique(where={"id": id})
        if embedding:
            await self._set_cache(cache_key, embedding.dict())
        
        return embedding
    
    async def update(self, id: str, data: Dict[str, Any]) -> Optional[Embedding]:
        """Update embedding by ID"""
        # Get old data for audit
        old_embedding = await self.get_by_id(id)
        if not old_embedding:
            return None
        
        # Update embedding
        updated_embedding = await self.db.embedding.update(
            where={"id": id},
            data=data
        )
        
        # Invalidate cache
        await self.invalidate_cache(id)
        
        # Create audit log
        await self._create_audit_log(
            action="UPDATE",
            entity_id=id,
            entity_type="Embedding",
            old_data=old_embedding.dict(),
            new_data=updated_embedding.dict()
        )
        
        return updated_embedding
    
    async def delete(self, id: str) -> bool:
        """Delete embedding by ID"""
        # Get embedding for audit
        embedding = await self.get_by_id(id)
        if not embedding:
            return False
        
        # Delete embedding
        await self.db.embedding.delete(where={"id": id})
        
        # Update vector store statistics
        await self._update_vector_store_stats(embedding.vector_store_id)
        
        # Invalidate cache
        await self.invalidate_cache(id)
        
        # Create audit log
        await self._create_audit_log(
            action="DELETE",
            entity_id=id,
            entity_type="Embedding",
            old_data=embedding.dict()
        )
        
        return True
    
    async def list(
        self,
        pagination: PaginationParams,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[Dict[str, str]] = None
    ) -> tuple[List[Embedding], int]:
        """List embeddings with pagination and filtering"""
        skip, take = self._calculate_pagination(pagination)
        where = self._build_where_clause(filters)
        order = self._build_order_by(order_by)
        
        # Get embeddings and total count
        embeddings, total = await self.db.embedding.find_many_and_count(
            where=where,
            skip=skip,
            take=take,
            order=order
        )
        
        return embeddings, total
    
    async def exists(self, id: str) -> bool:
        """Check if embedding exists"""
        embedding = await self.db.embedding.find_unique(
            where={"id": id},
            select={"id": True}
        )
        return embedding is not None
    
    async def get_by_vector_store_id(self, vector_store_id: str) -> List[Embedding]:
        """Get embeddings by vector store ID"""
        return await self.db.embedding.find_many(
            where={"vector_store_id": vector_store_id},
            order=[{"created_at": "desc"}]
        )
    
    async def get_by_document_id(
        self,
        vector_store_id: str,
        document_id: str
    ) -> List[Embedding]:
        """Get embeddings by document ID"""
        return await self.db.embedding.find_many(
            where={
                "vector_store_id": vector_store_id,
                "document_id": document_id
            },
            order=[{"chunk_index": "asc"}]
        )
    
    async def create_batch(self, embeddings_data: List[Dict[str, Any]]) -> List[Embedding]:
        """Create multiple embeddings in batch"""
        embeddings = []
        
        # Use transaction for batch creation
        async with self.db.tx() as transaction:
            for data in embeddings_data:
                embedding = await transaction.embedding.create(data=data)
                embeddings.append(embedding)
        
        # Update vector store statistics for all affected stores
        vector_store_ids = set(emb.vector_store_id for emb in embeddings)
        for store_id in vector_store_ids:
            await self._update_vector_store_stats(store_id)
        
        return embeddings
    
    async def delete_by_document_id(
        self,
        vector_store_id: str,
        document_id: str
    ) -> int:
        """Delete all embeddings for a document"""
        result = await self.db.embedding.delete_many(
            where={
                "vector_store_id": vector_store_id,
                "document_id": document_id
            }
        )
        
        # Update vector store statistics
        await self._update_vector_store_stats(vector_store_id)
        
        return result.count
    
    async def search_similar_embeddings(
        self,
        vector_store_id: str,
        query_vector: List[float],
        limit: int = 10,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search for similar embeddings using vector similarity"""
        # This is a simplified version - in practice, you'd use vector database specific queries
        # For PostgreSQL with pgvector extension, you might use something like:
        
        query = """
        SELECT id, document_id, chunk_index, content, metadata,
               1 - (vector <=> $2::vector) as similarity
        FROM embeddings 
        WHERE vector_store_id = $1
          AND 1 - (vector <=> $2::vector) > $3
        ORDER BY vector <=> $2::vector
        LIMIT $4
        """
        
        # Convert vector to string format expected by pgvector
        vector_str = f"[{','.join(map(str, query_vector))}]"
        
        results = await self.db.query_raw(
            query,
            vector_store_id,
            vector_str,
            threshold,
            limit
        )
        
        return results
    
    async def get_embedding_stats(self, vector_store_id: str) -> Dict[str, Any]:
        """Get embedding statistics for a vector store"""
        # Total embeddings
        total = await self.db.embedding.count(
            where={"vector_store_id": vector_store_id}
        )
        
        # Unique documents
        unique_docs = await self.db.embedding.group_by(
            by=["document_id"],
            where={"vector_store_id": vector_store_id}
        )
        
        # Average chunks per document
        avg_chunks = total / len(unique_docs) if unique_docs else 0
        
        return {
            "total_embeddings": total,
            "unique_documents": len(unique_docs),
            "average_chunks_per_document": avg_chunks
        }
    
    async def _update_vector_store_stats(self, vector_store_id: str) -> None:
        """Update vector store statistics"""
        try:
            stats = await self.get_embedding_stats(vector_store_id)
            
            # Update the vector store with new statistics
            await self.db.vectorstore.update(
                where={"id": vector_store_id},
                data={
                    "statistics": {
                        "total_vectors": stats["total_embeddings"],
                        "total_documents": stats["unique_documents"],
                        "last_updated": "now()"
                    },
                    "updated_at": "now()"
                }
            )
        except Exception as e:
            # Log error but don't fail the main operation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to update vector store stats: {e}")
    
    async def cleanup_orphaned_embeddings(self) -> int:
        """Clean up embeddings that reference non-existent vector stores"""
        # Find embeddings with invalid vector store references
        orphaned = await self.db.query_raw("""
            SELECT e.id FROM embeddings e
            LEFT JOIN vector_stores vs ON e.vector_store_id = vs.id
            WHERE vs.id IS NULL
        """)
        
        if not orphaned:
            return 0
        
        # Delete orphaned embeddings
        orphaned_ids = [row["id"] for row in orphaned]
        result = await self.db.embedding.delete_many(
            where={"id": {"in": orphaned_ids}}
        )
        
        return result.count