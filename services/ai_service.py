"""
AI Service - Face detection, embedding generation, and similarity search
Uses InsightFace for detection/embedding and FAISS for vector search
"""
import numpy as np
import cv2
import faiss
from typing import List, Tuple, Optional, Dict
from pathlib import Path
import pickle
from config import settings
import logging

logger = logging.getLogger(__name__)


class AIService:
    """
    Main AI service for face recognition
    Pipeline: Detection -> Embedding -> Similarity Search
    """
    
    def __init__(self):
        self.model = None
        self.initialized = False
        
    def initialize(self):
        """Initialize InsightFace model (lazy loading)"""
        if self.initialized:
            return
            
        try:
            import insightface
            from insightface.app import FaceAnalysis
            
            logger.info("Initializing InsightFace model...")
            
            # Initialize FaceAnalysis with lighter model for low memory
            self.model = FaceAnalysis(
                name='buffalo_sc',  # Smaller model (buffalo_sc instead of buffalo_l)
                providers=['CPUExecutionProvider']  # CPU only to save memory
            )
            
            self.model.prepare(
                ctx_id=-1,  # -1 for CPU (saves memory vs GPU context)
                det_size=(320, 320)  # Smaller detection size to save memory
            )
            
            self.initialized = True
            logger.info("InsightFace model initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize InsightFace: {e}")
            raise
    
    def detect_faces(self, image_path: str) -> List[Dict]:
        """
        Detect faces in an image
        
        Returns:
            List of face dictionaries with 'bbox', 'embedding', 'det_score'
        """
        self.initialize()
        
        try:
            # Read image
            img = cv2.imread(str(image_path))
            if img is None:
                logger.warning(f"Could not read image: {image_path}")
                return []
            
            # Detect faces
            faces = self.model.get(img)
            
            if not faces:
                logger.debug(f"No faces detected in {image_path}")
                return []
            
            # Filter by confidence
            faces = [
                face for face in faces 
                if face.det_score >= settings.face_detection_confidence
            ]
            
            logger.info(f"Detected {len(faces)} faces in {image_path}")
            
            # Convert to serializable format
            results = []
            for face in faces:
                results.append({
                    'bbox': face.bbox.tolist(),
                    'embedding': face.embedding,  # numpy array
                    'det_score': float(face.det_score)
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error detecting faces in {image_path}: {e}")
            return []
    
    def get_embedding(self, image_path: str) -> Optional[np.ndarray]:
        """
        Get face embedding from an image (expects single face)
        
        Returns:
            numpy array of embedding (512 dimensions) or None if no face found
        """
        faces = self.detect_faces(image_path)
        
        if not faces:
            return None
        
        # Return the face with highest confidence
        best_face = max(faces, key=lambda x: x['det_score'])
        return best_face['embedding']
    
    def get_embeddings_batch(self, image_paths: List[str]) -> List[Optional[np.ndarray]]:
        """
        Get embeddings for multiple images
        
        Returns:
            List of embeddings (or None for failed detections)
        """
        embeddings = []
        for image_path in image_paths:
            embedding = self.get_embedding(image_path)
            embeddings.append(embedding)
        
        return embeddings
    
    def compare_embeddings(
        self, 
        embedding1: np.ndarray, 
        embedding2: np.ndarray
    ) -> float:
        """
        Compare two embeddings using cosine similarity
        
        Returns:
            Similarity score (0-1, where 1 is identical)
        """
        # Normalize
        embedding1 = embedding1 / np.linalg.norm(embedding1)
        embedding2 = embedding2 / np.linalg.norm(embedding2)
        
        # Cosine similarity
        similarity = np.dot(embedding1, embedding2)
        
        return float(similarity)
    
    def find_matches(
        self,
        query_embedding: np.ndarray,
        target_embeddings: List[np.ndarray],
        threshold: float = None
    ) -> List[Tuple[int, float]]:
        """
        Find matches between query embedding and target embeddings
        
        Returns:
            List of (index, similarity_score) tuples above threshold
        """
        if threshold is None:
            threshold = settings.face_match_threshold
        
        matches = []
        
        for idx, target_embedding in enumerate(target_embeddings):
            similarity = self.compare_embeddings(query_embedding, target_embedding)
            
            if similarity >= threshold:
                matches.append((idx, similarity))
        
        # Sort by similarity (descending)
        matches.sort(key=lambda x: x[1], reverse=True)
        
        return matches
    
    def create_faiss_index(
        self,
        embeddings: List[np.ndarray]
    ) -> Tuple[faiss.Index, np.ndarray]:
        """
        Create FAISS index from embeddings for fast similarity search
        
        Returns:
            (faiss_index, embeddings_array)
        """
        if not embeddings:
            raise ValueError("Cannot create index from empty embeddings list")
        
        # Stack embeddings
        embeddings_array = np.vstack(embeddings).astype('float32')
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings_array)
        
        # Create index (Inner Product = Cosine Similarity for normalized vectors)
        dimension = embeddings_array.shape[1]
        index = faiss.IndexFlatIP(dimension)
        
        # Add embeddings to index
        index.add(embeddings_array)
        
        logger.info(f"Created FAISS index with {len(embeddings)} embeddings")
        
        return index, embeddings_array
    
    def search_faiss_index(
        self,
        index: faiss.Index,
        query_embeddings: List[np.ndarray],
        k: int = 10,
        threshold: float = None
    ) -> List[List[Tuple[int, float]]]:
        """
        Search FAISS index with query embeddings
        
        Args:
            index: FAISS index
            query_embeddings: List of query embeddings
            k: Number of nearest neighbors to return
            threshold: Minimum similarity threshold
        
        Returns:
            List of [(index, score), ...] for each query
        """
        if threshold is None:
            threshold = settings.face_match_threshold
        
        # Stack and normalize query embeddings
        queries = np.vstack(query_embeddings).astype('float32')
        faiss.normalize_L2(queries)
        
        # Search
        distances, indices = index.search(queries, k)
        
        # Filter by threshold and format results
        results = []
        for dist_row, idx_row in zip(distances, indices):
            matches = [
                (int(idx), float(dist))
                for idx, dist in zip(idx_row, dist_row)
                if dist >= threshold and idx != -1
            ]
            results.append(matches)
        
        return results
    
    def save_index(self, index: faiss.Index, save_path: str):
        """Save FAISS index to disk"""
        faiss.write_index(index, str(save_path))
        logger.info(f"Saved FAISS index to {save_path}")
    
    def load_index(self, index_path: str) -> faiss.Index:
        """Load FAISS index from disk"""
        index = faiss.read_index(str(index_path))
        logger.info(f"Loaded FAISS index from {index_path}")
        return index
    
    def validate_face_image(self, image_path: str) -> Tuple[bool, str]:
        """
        Validate if image contains a clear face
        
        Returns:
            (is_valid, message)
        """
        faces = self.detect_faces(image_path)
        
        if not faces:
            return False, "לא הצלחתי לזהות פנים ברורות בתמונה הזו. אנא נסה/י תמונה אחרת (פנים קדמיות, תאורה טובה, ללא משקפי שמש)."
        
        # Check if face is too small
        best_face = max(faces, key=lambda x: x['det_score'])
        bbox = best_face['bbox']
        face_width = bbox[2] - bbox[0]
        face_height = bbox[3] - bbox[1]
        
        if face_width < settings.min_face_size or face_height < settings.min_face_size:
            return False, "הפנים בתמונה קטנות מדי. אנא שלח/י תמונה בה הפנים גדולות ובולטות יותר."
        
        return True, "זוהו פנים ברורות"


# Global AI service instance
ai_service = AIService()
