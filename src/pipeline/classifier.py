import os
import logging
import pickle
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import re
from config import Config

logger = logging.getLogger(__name__)

class DocumentClassifier:
    """Document classification using scikit-learn"""
    
    def __init__(self, model_path=None, vectorizer_path=None):
        """
        Initialize document classifier
        
        Args:
            model_path: Path to saved model
            vectorizer_path: Path to saved vectorizer
        """
        self.model_path = model_path or Config.CLASSIFICATION_MODEL_PATH
        self.vectorizer_path = vectorizer_path or Config.VECTORIZER_PATH
        self.model = None
        self.vectorizer = None
        self.is_trained = False
        
        # Default document types
        self.default_categories = [
            'invoice', 'contract', 'report', 'letter', 'form', 
            'manual', 'presentation', 'academic', 'legal', 'other'
        ]
        
        # Load existing model if available
        self.load_model()
    
    def preprocess_text(self, text):
        """
        Preprocess text for classification
        
        Args:
            text: Raw text string
            
        Returns:
            str: Preprocessed text
        """
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\;\:]', ' ', text)
        
        # Remove very short words (less than 2 characters)
        words = text.split()
        words = [word for word in words if len(word) >= 2]
        
        return ' '.join(words)
    
    def extract_features(self, text):
        """
        Extract features from text for classification
        
        Args:
            text: Preprocessed text
            
        Returns:
            dict: Feature dictionary
        """
        features = {}
        
        # Basic statistics
        features['char_count'] = len(text)
        features['word_count'] = len(text.split())
        features['sentence_count'] = len([s for s in text.split('.') if s.strip()])
        features['avg_word_length'] = np.mean([len(word) for word in text.split()]) if text.split() else 0
        
        # Document structure indicators
        features['has_table_markers'] = 1 if any(marker in text for marker in ['table', 'row', 'column']) else 0
        features['has_financial_terms'] = 1 if any(term in text for term in ['invoice', 'amount', 'total', 'payment', 'due']) else 0
        features['has_legal_terms'] = 1 if any(term in text for term in ['contract', 'agreement', 'clause', 'party', 'hereby']) else 0
        features['has_technical_terms'] = 1 if any(term in text for term in ['system', 'process', 'method', 'analysis', 'data']) else 0
        
        return features
    
    def train_model(self, training_data, labels=None, test_size=0.2):
        """
        Train the classification model
        
        Args:
            training_data: List of texts or DataFrame with 'text' and 'category' columns
            labels: List of labels (if training_data is just texts)
            test_size: Fraction of data to use for testing
            
        Returns:
            dict: Training results
        """
        try:
            # Handle different input formats
            if isinstance(training_data, pd.DataFrame):
                texts = training_data['text'].tolist()
                categories = training_data['category'].tolist()
            elif isinstance(training_data, list) and labels is not None:
                texts = training_data
                categories = labels
            else:
                raise ValueError("Invalid training data format")
            
            # Preprocess texts
            processed_texts = [self.preprocess_text(text) for text in texts]
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                processed_texts, categories, test_size=test_size, random_state=42, stratify=categories
            )
            
            # Create and train pipeline
            self.vectorizer = TfidfVectorizer(
                max_features=5000,
                ngram_range=(1, 2),
                stop_words='english',
                min_df=2,
                max_df=0.95
            )
            
            self.model = MultinomialNB(alpha=1.0)
            
            # Fit vectorizer and model
            X_train_vectorized = self.vectorizer.fit_transform(X_train)
            self.model.fit(X_train_vectorized, y_train)
            
            # Evaluate on test set
            X_test_vectorized = self.vectorizer.transform(X_test)
            y_pred = self.model.predict(X_test_vectorized)
            
            accuracy = accuracy_score(y_test, y_pred)
            report = classification_report(y_test, y_pred, output_dict=True)
            
            self.is_trained = True
            
            # Save model
            self.save_model()
            
            results = {
                'success': True,
                'accuracy': accuracy,
                'classification_report': report,
                'training_samples': len(X_train),
                'test_samples': len(X_test),
                'categories': list(set(categories))
            }
            
            logger.info(f"Model training completed with accuracy: {accuracy:.3f}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def classify_document(self, text):
        """
        Classify a document
        
        Args:
            text: Document text
            
        Returns:
            dict: Classification result
        """
        try:
            if not self.is_trained:
                return {
                    'category': 'other',
                    'confidence': 0.0,
                    'probabilities': {},
                    'error': 'Model not trained'
                }
            
            # Preprocess text
            processed_text = self.preprocess_text(text)
            
            if not processed_text.strip():
                return {
                    'category': 'other',
                    'confidence': 0.0,
                    'probabilities': {},
                    'error': 'Empty text after preprocessing'
                }
            
            # Vectorize text
            text_vectorized = self.vectorizer.transform([processed_text])
            
            # Predict
            prediction = self.model.predict(text_vectorized)[0]
            probabilities = self.model.predict_proba(text_vectorized)[0]
            
            # Get class names
            classes = self.model.classes_
            
            # Create probability dictionary
            prob_dict = {classes[i]: prob for i, prob in enumerate(probabilities)}
            
            # Get confidence (max probability)
            confidence = max(probabilities)
            
            result = {
                'category': prediction,
                'confidence': confidence,
                'probabilities': prob_dict,
                'features': self.extract_features(processed_text)
            }
            
            logger.info(f"Document classified as '{prediction}' with confidence {confidence:.3f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error classifying document: {str(e)}")
            return {
                'category': 'other',
                'confidence': 0.0,
                'probabilities': {},
                'error': str(e)
            }
    
    def save_model(self):
        """Save trained model and vectorizer"""
        try:
            Config.create_directories()
            
            if self.model is not None:
                with open(self.model_path, 'wb') as f:
                    pickle.dump(self.model, f)
                logger.info(f"Model saved to {self.model_path}")
            
            if self.vectorizer is not None:
                with open(self.vectorizer_path, 'wb') as f:
                    pickle.dump(self.vectorizer, f)
                logger.info(f"Vectorizer saved to {self.vectorizer_path}")
                
        except Exception as e:
            logger.error(f"Error saving model: {str(e)}")
    
    def load_model(self):
        """Load trained model and vectorizer"""
        try:
            if os.path.exists(self.model_path) and os.path.exists(self.vectorizer_path):
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)
                
                with open(self.vectorizer_path, 'rb') as f:
                    self.vectorizer = pickle.load(f)
                
                self.is_trained = True
                logger.info("Model and vectorizer loaded successfully")
                return True
            else:
                logger.info("No saved model found, will need to train")
                return False
                
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            return False
    
    def create_sample_training_data(self):
        """
        Create sample training data for demonstration
        
        Returns:
            pandas.DataFrame: Sample training data
        """
        sample_data = [
            ("Invoice number 12345. Total amount due: $1,500.00. Payment due by January 15, 2024.", "invoice"),
            ("This agreement is entered into between Party A and Party B. The terms and conditions are as follows.", "contract"),
            ("Annual financial report for fiscal year 2023. Revenue increased by 15% compared to previous year.", "report"),
            ("Dear Sir/Madam, We are writing to inform you about the upcoming changes to our service.", "letter"),
            ("Application form for employment. Please fill out all required fields.", "form"),
            ("User manual for software installation. Step 1: Download the installer package.", "manual"),
            ("Quarterly sales presentation. Q4 results show significant growth in all segments.", "presentation"),
            ("Research paper on machine learning applications in healthcare. Abstract: This study examines...", "academic"),
            ("Legal brief regarding the case of Smith vs. Johnson. The plaintiff claims damages of...", "legal"),
            ("Meeting minutes from board meeting held on December 1, 2023.", "other")
        ]
        
        df = pd.DataFrame(sample_data, columns=['text', 'category'])
        
        # Add more samples by duplicating and slightly modifying
        additional_samples = []
        for text, category in sample_data:
            # Create variations
            additional_samples.append((text.replace("2023", "2024"), category))
            additional_samples.append((text.upper(), category))
        
        additional_df = pd.DataFrame(additional_samples, columns=['text', 'category'])
        final_df = pd.concat([df, additional_df], ignore_index=True)
        
        return final_df
    
    def get_model_info(self):
        """Get information about the current model"""
        if not self.is_trained:
            return {
                'trained': False,
                'message': 'No model trained'
            }
        
        try:
            info = {
                'trained': True,
                'model_type': type(self.model).__name__,
                'vectorizer_type': type(self.vectorizer).__name__,
                'categories': list(self.model.classes_),
                'feature_count': len(self.vectorizer.get_feature_names_out()) if hasattr(self.vectorizer, 'get_feature_names_out') else 'unknown',
                'model_path': self.model_path,
                'vectorizer_path': self.vectorizer_path
            }
            
            return info
            
        except Exception as e:
            return {
                'trained': True,
                'error': str(e)
            }