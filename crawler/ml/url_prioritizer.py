import logging
from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sentence_transformers import SentenceTransformer
import xgboost as xgb
import joblib
import os
from datetime import datetime
from urllib.parse import urlparse, unquote
import re

logger = logging.getLogger(__name__)

class MLURLPrioritizer:
    """Machine learning-based URL prioritization."""
    
    def __init__(self, model_dir: str = "models"):
        self.model_dir = model_dir
        
        # Create model directory if it doesn't exist
        os.makedirs(model_dir, exist_ok=True)
        
        # Initialize models
        self.initialize_models()
        
        # URL feature patterns
        self.patterns = {
            'has_date': r'\d{4}[-/]\d{2}[-/]\d{2}',
            'is_pagination': r'page[=/]\d+',
            'has_keywords': r'(article|post|story|news|blog)',
            'has_file_extension': r'\.(html?|php|aspx?)$',
            'has_query_params': r'\?.*=.*',
        }
        
    def initialize_models(self):
        """Initialize or load pre-trained models."""
        try:
            # URL embedding model
            self.url_encoder = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Load custom trained models if they exist
            self.load_custom_models()
            
        except Exception as e:
            logger.error(f"Error initializing models: {e}")
            raise
            
    def load_custom_models(self):
        """Load custom trained models if they exist."""
        try:
            url_model_path = os.path.join(self.model_dir, "url_priority_model.joblib")
            domain_model_path = os.path.join(self.model_dir, "domain_priority_model.xgb")
            
            if os.path.exists(url_model_path):
                self.url_model = joblib.load(url_model_path)
                logger.info("Loaded URL priority model")
            else:
                self.url_model = GradientBoostingRegressor(
                    n_estimators=100,
                    learning_rate=0.1,
                    max_depth=5
                )
                logger.info("Initialized new URL priority model")
                
            if os.path.exists(domain_model_path):
                self.domain_model = xgb.Booster()
                self.domain_model.load_model(domain_model_path)
                logger.info("Loaded domain priority model")
            else:
                self.domain_model = None
                logger.info("No domain priority model found")
                
        except Exception as e:
            logger.error(f"Error loading custom models: {e}")
            raise
            
    def extract_url_features(self, url: str) -> Dict[str, Any]:
        """Extract features from URL."""
        try:
            # Parse URL
            parsed = urlparse(unquote(url.lower()))
            path = parsed.path
            
            # Basic features
            features = {
                'path_depth': len([p for p in path.split('/') if p]),
                'path_length': len(path),
                'has_query': int(bool(parsed.query)),
                'num_query_params': len(parsed.query.split('&')) if parsed.query else 0
            }
            
            # Pattern-based features
            for name, pattern in self.patterns.items():
                features[name] = int(bool(re.search(pattern, url)))
                
            # Get URL embedding
            url_embedding = self.url_encoder.encode(url)
            
            return {
                'scalar_features': features,
                'embedding': url_embedding
            }
            
        except Exception as e:
            logger.error(f"Error extracting URL features: {e}")
            return {
                'scalar_features': {},
                'embedding': None
            }
            
    def extract_domain_features(
        self,
        domain: str,
        domain_stats: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract features for domain prioritization."""
        try:
            features = {
                'avg_content_length': domain_stats.get('avg_content_length', 0),
                'avg_crawl_time': domain_stats.get('avg_crawl_time', 0),
                'success_rate': domain_stats.get('success_rate', 0),
                'total_pages': domain_stats.get('total_pages', 0),
                'content_type_diversity': domain_stats.get('content_type_count', 0)
            }
            
            # Get domain embedding
            domain_embedding = self.url_encoder.encode(domain)
            
            return {
                'scalar_features': features,
                'embedding': domain_embedding
            }
            
        except Exception as e:
            logger.error(f"Error extracting domain features: {e}")
            return {
                'scalar_features': {},
                'embedding': None
            }
            
    async def calculate_priority(
        self,
        url: str,
        domain_stats: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Calculate priority score for a URL."""
        try:
            # Extract features
            url_features = self.extract_url_features(url)
            domain = urlparse(url).netloc
            domain_features = self.extract_domain_features(domain, domain_stats)
            
            # Calculate base score from URL model
            url_score = 0.5  # Default score
            if hasattr(self, 'url_model'):
                # Combine scalar features and embedding
                X = np.concatenate([
                    np.array(list(url_features['scalar_features'].values())),
                    url_features['embedding']
                ]).reshape(1, -1)
                url_score = float(self.url_model.predict(X)[0])
                
            # Calculate domain score if model exists
            domain_score = 0.5  # Default score
            if self.domain_model is not None:
                # Combine scalar features and embedding
                X = np.concatenate([
                    np.array(list(domain_features['scalar_features'].values())),
                    domain_features['embedding']
                ]).reshape(1, -1)
                domain_score = float(self.domain_model.predict(xgb.DMatrix(X))[0])
                
            # Combine scores
            final_score = 0.7 * url_score + 0.3 * domain_score
            
            return {
                'final_score': final_score,
                'url_score': url_score,
                'domain_score': domain_score,
                'features': {
                    'url': url_features['scalar_features'],
                    'domain': domain_features['scalar_features']
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating priority: {e}")
            return {
                'error': str(e),
                'final_score': 0.5  # Default score on error
            }
            
    async def train_url_model(
        self,
        urls: List[str],
        scores: List[float],
        validation_split: float = 0.2
    ) -> Dict[str, Any]:
        """Train URL priority model."""
        try:
            # Extract features for all URLs
            features_list = []
            for url in urls:
                url_features = self.extract_url_features(url)
                combined_features = np.concatenate([
                    np.array(list(url_features['scalar_features'].values())),
                    url_features['embedding']
                ])
                features_list.append(combined_features)
                
            X = np.array(features_list)
            y = np.array(scores)
            
            # Split data
            split_idx = int(len(urls) * (1 - validation_split))
            X_train, X_val = X[:split_idx], X[split_idx:]
            y_train, y_val = y[:split_idx], y[split_idx:]
            
            # Train model
            self.url_model.fit(X_train, y_train)
            
            # Evaluate
            train_score = self.url_model.score(X_train, y_train)
            val_score = self.url_model.score(X_val, y_val)
            
            # Save model
            joblib.dump(
                self.url_model,
                os.path.join(self.model_dir, "url_priority_model.joblib")
            )
            
            return {
                'train_score': train_score,
                'validation_score': val_score,
                'num_samples': len(urls)
            }
            
        except Exception as e:
            logger.error(f"Error training URL model: {e}")
            return {'error': str(e)}
            
    async def train_domain_model(
        self,
        domains: List[str],
        domain_stats: List[Dict[str, Any]],
        scores: List[float],
        validation_split: float = 0.2
    ) -> Dict[str, Any]:
        """Train domain priority model."""
        try:
            # Extract features for all domains
            features_list = []
            for domain, stats in zip(domains, domain_stats):
                domain_features = self.extract_domain_features(domain, stats)
                combined_features = np.concatenate([
                    np.array(list(domain_features['scalar_features'].values())),
                    domain_features['embedding']
                ])
                features_list.append(combined_features)
                
            X = np.array(features_list)
            y = np.array(scores)
            
            # Split data
            split_idx = int(len(domains) * (1 - validation_split))
            X_train, X_val = X[:split_idx], X[split_idx:]
            y_train, y_val = y[:split_idx], y[split_idx:]
            
            # Create DMatrix for XGBoost
            dtrain = xgb.DMatrix(X_train, label=y_train)
            dval = xgb.DMatrix(X_val, label=y_val)
            
            # Training parameters
            params = {
                'objective': 'reg:squarederror',
                'eval_metric': 'rmse',
                'max_depth': 6,
                'eta': 0.1
            }
            
            # Train model
            self.domain_model = xgb.train(
                params,
                dtrain,
                num_boost_round=100,
                evals=[(dtrain, 'train'), (dval, 'val')]
            )
            
            # Save model
            self.domain_model.save_model(
                os.path.join(self.model_dir, "domain_priority_model.xgb")
            )
            
            # Calculate scores
            train_pred = self.domain_model.predict(dtrain)
            val_pred = self.domain_model.predict(dval)
            
            train_score = np.corrcoef(y_train, train_pred)[0, 1]
            val_score = np.corrcoef(y_val, val_pred)[0, 1]
            
            return {
                'train_score': float(train_score),
                'validation_score': float(val_score),
                'num_samples': len(domains)
            }
            
        except Exception as e:
            logger.error(f"Error training domain model: {e}")
            return {'error': str(e)} 