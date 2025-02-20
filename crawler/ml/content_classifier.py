import logging
from typing import List, Dict, Any, Optional
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.ensemble import RandomForestClassifier
import numpy as np
import joblib
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class ContentClassifier:
    """Advanced content classification using transformers and ML models."""
    
    def __init__(self, model_dir: str = "models"):
        self.model_dir = model_dir
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Create model directory if it doesn't exist
        os.makedirs(model_dir, exist_ok=True)
        
        # Initialize models
        self.initialize_models()
        
    def initialize_models(self):
        """Initialize or load pre-trained models."""
        try:
            # Zero-shot classifier for dynamic categories
            self.zero_shot_model = AutoModelForSequenceClassification.from_pretrained(
                "facebook/bart-large-mnli"
            ).to(self.device)
            self.zero_shot_tokenizer = AutoTokenizer.from_pretrained("facebook/bart-large-mnli")
            
            # Sentence embeddings model
            self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Load custom trained models if they exist
            self.load_custom_models()
            
        except Exception as e:
            logger.error(f"Error initializing models: {e}")
            raise
            
    def load_custom_models(self):
        """Load custom trained models if they exist."""
        try:
            model_path = os.path.join(self.model_dir, "content_classifier.joblib")
            mlb_path = os.path.join(self.model_dir, "multilabel_binarizer.joblib")
            
            if os.path.exists(model_path) and os.path.exists(mlb_path):
                self.custom_classifier = joblib.load(model_path)
                self.mlb = joblib.load(mlb_path)
                logger.info("Loaded custom trained models")
            else:
                self.custom_classifier = RandomForestClassifier(n_estimators=100)
                self.mlb = MultiLabelBinarizer()
                logger.info("Initialized new custom models")
                
        except Exception as e:
            logger.error(f"Error loading custom models: {e}")
            raise
            
    async def classify_content(
        self,
        text: str,
        title: Optional[str] = None,
        custom_categories: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Classify content using multiple approaches."""
        try:
            # Combine title and text
            full_text = f"{title}. {text}" if title else text
            
            # Get embeddings
            embeddings = self.sentence_model.encode(full_text)
            
            # Zero-shot classification
            if custom_categories:
                zero_shot_results = await self._zero_shot_classify(
                    full_text,
                    custom_categories
                )
            else:
                zero_shot_results = await self._zero_shot_classify(
                    full_text,
                    [
                        "technology", "business", "science", "health",
                        "politics", "entertainment", "sports", "education"
                    ]
                )
                
            # Custom classification if model is trained
            custom_results = None
            if hasattr(self, 'custom_classifier') and hasattr(self, 'mlb'):
                custom_results = self._custom_classify(embeddings)
                
            return {
                "zero_shot_classification": zero_shot_results,
                "custom_classification": custom_results,
                "embeddings": embeddings.tolist(),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error classifying content: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            
    async def _zero_shot_classify(
        self,
        text: str,
        categories: List[str]
    ) -> Dict[str, float]:
        """Perform zero-shot classification."""
        try:
            results = {}
            for category in categories:
                # Create hypothesis
                hypothesis = f"This text is about {category}."
                
                # Tokenize
                inputs = self.zero_shot_tokenizer(
                    text,
                    hypothesis,
                    truncation=True,
                    max_length=512,
                    return_tensors="pt"
                ).to(self.device)
                
                # Get prediction
                with torch.no_grad():
                    outputs = self.zero_shot_model(**inputs)
                    scores = torch.softmax(outputs.logits, dim=1)
                    results[category] = float(scores[0][1])  # Probability of entailment
                    
            return results
            
        except Exception as e:
            logger.error(f"Error in zero-shot classification: {e}")
            return {}
            
    def _custom_classify(self, embeddings: np.ndarray) -> Dict[str, float]:
        """Perform classification using custom trained model."""
        try:
            # Reshape embeddings for prediction
            embeddings = embeddings.reshape(1, -1)
            
            # Get predictions
            predictions = self.custom_classifier.predict_proba(embeddings)
            
            # Convert to dictionary
            results = {}
            for i, label in enumerate(self.mlb.classes_):
                results[label] = float(predictions[0][i])
                
            return results
            
        except Exception as e:
            logger.error(f"Error in custom classification: {e}")
            return {}
            
    async def train_custom_model(
        self,
        texts: List[str],
        labels: List[List[str]],
        validation_split: float = 0.2
    ) -> Dict[str, Any]:
        """Train custom classification model."""
        try:
            # Get embeddings for all texts
            embeddings = self.sentence_model.encode(texts)
            
            # Transform labels
            y = self.mlb.fit_transform(labels)
            
            # Split data
            split_idx = int(len(texts) * (1 - validation_split))
            X_train, X_val = embeddings[:split_idx], embeddings[split_idx:]
            y_train, y_val = y[:split_idx], y[split_idx:]
            
            # Train model
            self.custom_classifier.fit(X_train, y_train)
            
            # Evaluate
            train_score = self.custom_classifier.score(X_train, y_train)
            val_score = self.custom_classifier.score(X_val, y_val)
            
            # Save models
            joblib.dump(
                self.custom_classifier,
                os.path.join(self.model_dir, "content_classifier.joblib")
            )
            joblib.dump(
                self.mlb,
                os.path.join(self.model_dir, "multilabel_binarizer.joblib")
            )
            
            return {
                "train_score": train_score,
                "validation_score": val_score,
                "num_categories": len(self.mlb.classes_),
                "num_samples": len(texts)
            }
            
        except Exception as e:
            logger.error(f"Error training custom model: {e}")
            return {"error": str(e)} 