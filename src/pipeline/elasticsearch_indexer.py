import os
import logging
import hashlib
from datetime import datetime
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from config import Config

logger = logging.getLogger(__name__)

class ElasticsearchIndexer:
    """Handles indexing of processed documents to Elasticsearch"""
    
    def __init__(self, es_url=None, index_name=None):
        """
        Initialize Elasticsearch indexer
        
        Args:
            es_url: Elasticsearch URL
            index_name: Index name for documents
        """
        self.es_url = es_url or Config.ELASTICSEARCH_URL
        self.index_name = index_name or Config.ELASTICSEARCH_INDEX
        self.es = None
        self.is_connected = False
        
        # Connect to Elasticsearch
        self.connect()
    
    def connect(self):
        """Connect to Elasticsearch"""
        try:
            self.es = Elasticsearch([self.es_url])
            
            # Test connection
            if self.es.ping():
                self.is_connected = True
                logger.info(f"Connected to Elasticsearch at {self.es_url}")
                
                # Create index if it doesn't exist
                self.create_index()
            else:
                logger.error(f"Cannot connect to Elasticsearch at {self.es_url}")
                self.is_connected = False
                
        except Exception as e:
            logger.error(f"Error connecting to Elasticsearch: {str(e)}")
            self.is_connected = False
    
    def create_index(self):
        """Create index with proper mapping"""
        try:
            if not self.es.indices.exists(index=self.index_name):
                mapping = {
                    "mappings": {
                        "properties": {
                            "document_id": {"type": "keyword"},
                            "filename": {"type": "keyword"},
                            "file_path": {"type": "keyword"},
                            "file_size": {"type": "integer"},
                            "content": {
                                "type": "text",
                                "analyzer": "standard",
                                "fields": {
                                    "keyword": {"type": "keyword", "ignore_above": 256}
                                }
                            },
                            "title": {"type": "text"},
                            "document_type": {"type": "keyword"},
                            "classification": {
                                "type": "object",
                                "properties": {
                                    "category": {"type": "keyword"},
                                    "confidence": {"type": "float"},
                                    "probabilities": {"type": "object"}
                                }
                            },
                            "metadata": {
                                "type": "object",
                                "properties": {
                                    "author": {"type": "text"},
                                    "creator": {"type": "text"},
                                    "subject": {"type": "text"},
                                    "keywords": {"type": "text"},
                                    "creation_date": {"type": "date"},
                                    "modification_date": {"type": "date"}
                                }
                            },
                            "processing_info": {
                                "type": "object",
                                "properties": {
                                    "extraction_method": {"type": "keyword"},
                                    "ocr_confidence": {"type": "float"},
                                    "processing_time": {"type": "float"},
                                    "total_pages": {"type": "integer"}
                                }
                            },
                            "indexed_at": {"type": "date"},
                            "processed_at": {"type": "date"}
                        }
                    }
                }
                
                self.es.indices.create(index=self.index_name, body=mapping)
                logger.info(f"Created index: {self.index_name}")
            else:
                logger.info(f"Index {self.index_name} already exists")
                
        except Exception as e:
            logger.error(f"Error creating index: {str(e)}")
    
    def generate_document_id(self, file_path):
        """Generate unique document ID based on file path and content"""
        return hashlib.md5(file_path.encode()).hexdigest()
    
    def index_document(self, document_data):
        """
        Index a single document
        
        Args:
            document_data: Dictionary containing document information
            
        Returns:
            dict: Indexing result
        """
        try:
            if not self.is_connected:
                return {
                    'success': False,
                    'error': 'Not connected to Elasticsearch'
                }
            
            # Generate document ID
            doc_id = self.generate_document_id(document_data.get('file_path', ''))
            
            # Prepare document for indexing
            doc = {
                'document_id': doc_id,
                'filename': document_data.get('filename', ''),
                'file_path': document_data.get('file_path', ''),
                'file_size': document_data.get('file_size', 0),
                'content': document_data.get('text', ''),
                'title': self._extract_title(document_data.get('text', '')),
                'document_type': document_data.get('document_type', ''),
                'classification': {
                    'category': document_data.get('classification', {}).get('category', 'other'),
                    'confidence': document_data.get('classification', {}).get('confidence', 0.0),
                    'probabilities': document_data.get('classification', {}).get('probabilities', {})
                },
                'metadata': self._clean_metadata(document_data.get('metadata', {})),
                'processing_info': {
                    'extraction_method': document_data.get('extraction_method', ''),
                    'ocr_confidence': document_data.get('ocr_confidence'),
                    'processing_time': document_data.get('processing_time'),
                    'total_pages': document_data.get('total_pages', 0)
                },
                'indexed_at': datetime.utcnow().isoformat(),
                'processed_at': document_data.get('processed_at', datetime.utcnow().isoformat())
            }
            
            # Index document
            response = self.es.index(
                index=self.index_name,
                id=doc_id,
                body=doc
            )
            
            logger.info(f"Indexed document {document_data.get('filename', 'unknown')} with ID: {doc_id}")
            
            return {
                'success': True,
                'document_id': doc_id,
                'elasticsearch_response': response
            }
            
        except Exception as e:
            logger.error(f"Error indexing document: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def index_documents_bulk(self, documents_data):
        """
        Index multiple documents in bulk
        
        Args:
            documents_data: List of document dictionaries
            
        Returns:
            dict: Bulk indexing result
        """
        try:
            if not self.is_connected:
                return {
                    'success': False,
                    'error': 'Not connected to Elasticsearch'
                }
            
            actions = []
            
            for doc_data in documents_data:
                doc_id = self.generate_document_id(doc_data.get('file_path', ''))
                
                action = {
                    '_index': self.index_name,
                    '_id': doc_id,
                    '_source': {
                        'document_id': doc_id,
                        'filename': doc_data.get('filename', ''),
                        'file_path': doc_data.get('file_path', ''),
                        'file_size': doc_data.get('file_size', 0),
                        'content': doc_data.get('text', ''),
                        'title': self._extract_title(doc_data.get('text', '')),
                        'document_type': doc_data.get('document_type', ''),
                        'classification': {
                            'category': doc_data.get('classification', {}).get('category', 'other'),
                            'confidence': doc_data.get('classification', {}).get('confidence', 0.0),
                            'probabilities': doc_data.get('classification', {}).get('probabilities', {})
                        },
                        'metadata': self._clean_metadata(doc_data.get('metadata', {})),
                        'processing_info': {
                            'extraction_method': doc_data.get('extraction_method', ''),
                            'ocr_confidence': doc_data.get('ocr_confidence'),
                            'processing_time': doc_data.get('processing_time'),
                            'total_pages': doc_data.get('total_pages', 0)
                        },
                        'indexed_at': datetime.utcnow().isoformat(),
                        'processed_at': doc_data.get('processed_at', datetime.utcnow().isoformat())
                    }
                }
                actions.append(action)
            
            # Perform bulk indexing
            success_count, failed_items = bulk(self.es, actions)
            
            logger.info(f"Bulk indexed {success_count} documents successfully")
            
            if failed_items:
                logger.warning(f"Failed to index {len(failed_items)} documents")
            
            return {
                'success': True,
                'indexed_count': success_count,
                'failed_count': len(failed_items),
                'failed_items': failed_items
            }
            
        except Exception as e:
            logger.error(f"Error in bulk indexing: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def search_documents(self, query, filters=None, size=10, from_=0):
        """
        Search documents in Elasticsearch
        
        Args:
            query: Search query string
            filters: Dictionary of filters
            size: Number of results to return
            from_: Offset for pagination
            
        Returns:
            dict: Search results
        """
        try:
            if not self.is_connected:
                return {
                    'success': False,
                    'error': 'Not connected to Elasticsearch'
                }
            
            # Build search query
            search_body = {
                'query': {
                    'bool': {
                        'must': []
                    }
                },
                'size': size,
                'from': from_,
                'sort': [
                    {'indexed_at': {'order': 'desc'}}
                ]
            }
            
            # Add text query
            if query:
                search_body['query']['bool']['must'].append({
                    'multi_match': {
                        'query': query,
                        'fields': ['content', 'title', 'filename'],
                        'type': 'best_fields',
                        'fuzziness': 'AUTO'
                    }
                })
            
            # Add filters
            if filters:
                filter_clauses = []
                
                if 'category' in filters:
                    filter_clauses.append({
                        'term': {'classification.category': filters['category']}
                    })
                
                if 'document_type' in filters:
                    filter_clauses.append({
                        'term': {'document_type': filters['document_type']}
                    })
                
                if 'date_from' in filters:
                    filter_clauses.append({
                        'range': {
                            'indexed_at': {
                                'gte': filters['date_from']
                            }
                        }
                    })
                
                if 'date_to' in filters:
                    filter_clauses.append({
                        'range': {
                            'indexed_at': {
                                'lte': filters['date_to']
                            }
                        }
                    })
                
                if filter_clauses:
                    search_body['query']['bool']['filter'] = filter_clauses
            
            # If no query and no filters, match all
            if not query and not filters:
                search_body['query'] = {'match_all': {}}
            
            # Execute search
            response = self.es.search(index=self.index_name, body=search_body)
            
            # Format results
            hits = response['hits']['hits']
            total = response['hits']['total']['value']
            
            documents = []
            for hit in hits:
                doc = hit['_source']
                doc['_score'] = hit['_score']
                documents.append(doc)
            
            return {
                'success': True,
                'total': total,
                'documents': documents,
                'took': response['took']
            }
            
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_document_by_id(self, doc_id):
        """Get document by ID"""
        try:
            if not self.is_connected:
                return None
            
            response = self.es.get(index=self.index_name, id=doc_id)
            return response['_source']
            
        except Exception as e:
            logger.error(f"Error getting document {doc_id}: {str(e)}")
            return None
    
    def delete_document(self, doc_id):
        """Delete document by ID"""
        try:
            if not self.is_connected:
                return False
            
            self.es.delete(index=self.index_name, id=doc_id)
            logger.info(f"Deleted document {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {str(e)}")
            return False
    
    def get_index_stats(self):
        """Get index statistics"""
        try:
            if not self.is_connected:
                return {}
            
            stats = self.es.indices.stats(index=self.index_name)
            count = self.es.count(index=self.index_name)
            
            return {
                'document_count': count['count'],
                'index_size': stats['indices'][self.index_name]['total']['store']['size_in_bytes'],
                'index_name': self.index_name
            }
            
        except Exception as e:
            logger.error(f"Error getting index stats: {str(e)}")
            return {}
    
    def _extract_title(self, text, max_length=100):
        """Extract title from document text"""
        if not text:
            return "Untitled Document"
        
        # Take first line or first sentence
        lines = text.strip().split('\n')
        first_line = lines[0].strip() if lines else ""
        
        if first_line:
            # Truncate if too long
            if len(first_line) > max_length:
                return first_line[:max_length] + "..."
            return first_line
        
        return "Untitled Document"
    
    def _clean_metadata(self, metadata):
        """Clean metadata for Elasticsearch"""
        cleaned = {}
        
        for key, value in metadata.items():
            if value is not None:
                # Convert dates to ISO format
                if 'date' in key.lower() and hasattr(value, 'isoformat'):
                    cleaned[key] = value.isoformat()
                elif isinstance(value, str):
                    cleaned[key] = value
                elif isinstance(value, (int, float)):
                    cleaned[key] = value
        
        return cleaned
    
    def test_connection(self):
        """Test Elasticsearch connection"""
        try:
            if not self.es:
                return {
                    'connected': False,
                    'error': 'Elasticsearch client not initialized'
                }
            
            if self.es.ping():
                info = self.es.info()
                return {
                    'connected': True,
                    'cluster_name': info['cluster_name'],
                    'version': info['version']['number']
                }
            else:
                return {
                    'connected': False,
                    'error': 'Cannot reach Elasticsearch'
                }
                
        except Exception as e:
            return {
                'connected': False,
                'error': str(e)
            }