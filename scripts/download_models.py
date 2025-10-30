"""
Download InsightFace models
"""
import sys
from pathlib import Path
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_models():
    """Download InsightFace models"""
    logger.info("Downloading InsightFace models...")
    
    try:
        import insightface
        from insightface.app import FaceAnalysis
        
        # Create models directory
        settings.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize FaceAnalysis - this will download models
        logger.info("Initializing FaceAnalysis (buffalo_l model)...")
        
        app = FaceAnalysis(
            name='buffalo_l',
            root=str(settings.models_dir)
        )
        
        app.prepare(ctx_id=-1, det_size=(640, 640))
        
        logger.info("✅ Models downloaded successfully!")
        logger.info(f"Models saved to: {settings.models_dir}")
        
    except ImportError:
        logger.error("❌ insightface not installed. Please run: pip install insightface")
        sys.exit(1)
    
    except Exception as e:
        logger.error(f"❌ Failed to download models: {e}")
        sys.exit(1)


if __name__ == "__main__":
    download_models()
