"""
S3 output handler for translated code and metadata.

This module handles saving translated Python code, metadata, and processing results
to S3 with proper naming conventions and backward compatibility.
"""

import json
import logging
import boto3
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import asdict

from .models import TranslationResult, CompilationResult, ProcessingOutput

logger = logging.getLogger(__name__)


class S3OutputHandler:
    """
    Handles S3 output operations for translated code and metadata.
    
    This class manages:
    - Saving translated Python code with proper naming conventions
    - Storing translation metadata and processing information
    - Maintaining backward compatibility with existing analysis output
    - Organizing files into appropriate S3 directory structure
    """
    
    def __init__(self, s3_client=None):
        """
        Initialize the S3 output handler.
        
        Args:
            s3_client: Optional boto3 S3 client. If None, creates a new client.
        """
        self.s3_client = s3_client or boto3.client('s3')
        
        # S3 directory structure
        self.directories = {
            'analysis': 'analysis/',
            'translated': 'translated/python/',
            'metadata': 'translated/metadata/',
            'errors': 'translated/errors/',
            'logs': 'logs/'
        }
        
        logger.info("S3 output handler initialized")
    
    def save_translation_output(self,
                              bucket: str,
                              original_key: str,
                              processing_output: ProcessingOutput,
                              request_id: str) -> Dict[str, str]:
        """
        Save complete translation processing output to S3.
        
        Args:
            bucket: S3 bucket name
            original_key: Original file key from input
            processing_output: Complete processing results
            request_id: Request ID for tracking
            
        Returns:
            Dict[str, str]: Dictionary of saved file paths
            
        Raises:
            Exception: If S3 operations fail
        """
        saved_files = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # Save original analysis (backward compatibility)
            if processing_output.original_analysis:
                analysis_key = self._generate_analysis_key(original_key, timestamp)
                self._save_analysis_result(bucket, analysis_key, processing_output.original_analysis, 
                                         original_key, request_id)
                saved_files['analysis'] = analysis_key
                logger.info(f"Saved original analysis to: s3://{bucket}/{analysis_key}")
            
            # Save translated code if available
            if processing_output.translated_code:
                python_key = self._generate_python_code_key(original_key, timestamp)
                self._save_translated_code(bucket, python_key, processing_output.translated_code,
                                         original_key, request_id)
                saved_files['translated_code'] = python_key
                logger.info(f"Saved translated Python code to: s3://{bucket}/{python_key}")
            
            # Save error information if processing failed
            if not processing_output.processing_success or processing_output.error_message:
                error_key = self._generate_error_key(original_key, timestamp)
                self._save_error_information(bucket, error_key, processing_output,
                                           original_key, request_id)
                saved_files['errors'] = error_key
                logger.info(f"Saved error information to: s3://{bucket}/{error_key}")
            
            # Generate metadata key first
            metadata_key = self._generate_metadata_key(original_key, timestamp)
            saved_files['metadata'] = metadata_key
            
            # Update processing output with ALL saved file paths (including metadata)
            processing_output.output_files = list(saved_files.values())
            
            # Also update processing metadata with file information
            if not hasattr(processing_output, 'processing_metadata') or processing_output.processing_metadata is None:
                processing_output.processing_metadata = {}
            
            processing_output.processing_metadata.update({
                'files_saved': len(saved_files),
                'file_types_saved': list(saved_files.keys()),
                'total_output_size': sum(len(str(v)) for v in saved_files.values())
            })
            
            # Save metadata AFTER updating output_files and processing_metadata
            self._save_processing_metadata(bucket, metadata_key, processing_output, 
                                         original_key, request_id)
            logger.info(f"Saved processing metadata to: s3://{bucket}/{metadata_key}")
            
            return saved_files
            
        except Exception as e:
            logger.error(f"Failed to save translation output to S3: {str(e)}")
            raise
    
    def save_translation_result(self,
                              bucket: str,
                              original_key: str,
                              translation_result: TranslationResult,
                              request_id: str) -> str:
        """
        Save translation result as Python code file.
        
        Args:
            bucket: S3 bucket name
            original_key: Original file key
            translation_result: Translation result to save
            request_id: Request ID for tracking
            
        Returns:
            str: S3 key of saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        python_key = self._generate_python_code_key(original_key, timestamp)
        
        self._save_translated_code(bucket, python_key, translation_result.translated_code,
                                 original_key, request_id, translation_result)
        
        return python_key
    
    def save_compilation_result(self,
                              bucket: str,
                              original_key: str,
                              compilation_result: CompilationResult,
                              request_id: str) -> str:
        """
        Save compilation result metadata.
        
        Args:
            bucket: S3 bucket name
            original_key: Original file key
            compilation_result: Compilation result to save
            request_id: Request ID for tracking
            
        Returns:
            str: S3 key of saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if compilation_result.compilation_success:
            metadata_key = self._generate_metadata_key(original_key, timestamp, "compilation")
        else:
            metadata_key = self._generate_error_key(original_key, timestamp, "compilation")
        
        # Prepare compilation data
        compilation_data = {
            'compilation_result': compilation_result.to_dict(),
            'original_file': original_key,
            'timestamp': timestamp,
            'request_id': request_id
        }
        
        self.s3_client.put_object(
            Bucket=bucket,
            Key=metadata_key,
            Body=json.dumps(compilation_data, indent=2),
            ContentType='application/json',
            Metadata={
                'source-key': original_key,
                'request-id': request_id,
                'content-type': 'compilation-result',
                'timestamp': timestamp
            }
        )
        
        return metadata_key
    
    def _generate_analysis_key(self, original_key: str, timestamp: str) -> str:
        """Generate S3 key for analysis results (backward compatibility)."""
        safe_key = original_key.replace('/', '_')
        return f"{self.directories['analysis']}{safe_key}_{timestamp}_analysis.md"
    
    def _generate_python_code_key(self, original_key: str, timestamp: str) -> str:
        """Generate S3 key for translated Python code."""
        # Extract filename without extension
        filename = original_key.split('/')[-1]
        if '.' in filename:
            base_name = '.'.join(filename.split('.')[:-1])
        else:
            base_name = filename
        
        return f"{self.directories['translated']}{base_name}_{timestamp}_translated.py"
    
    def _generate_metadata_key(self, original_key: str, timestamp: str, suffix: str = "") -> str:
        """Generate S3 key for metadata files."""
        safe_key = original_key.replace('/', '_')
        suffix_part = f"_{suffix}" if suffix else ""
        return f"{self.directories['metadata']}{safe_key}_{timestamp}{suffix_part}_metadata.json"
    
    def _generate_error_key(self, original_key: str, timestamp: str, suffix: str = "") -> str:
        """Generate S3 key for error files."""
        safe_key = original_key.replace('/', '_')
        suffix_part = f"_{suffix}" if suffix else ""
        return f"{self.directories['errors']}{safe_key}_{timestamp}{suffix_part}_errors.json"
    
    def _save_analysis_result(self,
                            bucket: str,
                            key: str,
                            analysis_content: str,
                            original_key: str,
                            request_id: str) -> None:
        """Save original analysis result (backward compatibility)."""
        self.s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=analysis_content,
            ContentType='text/markdown',
            Metadata={
                'source-key': original_key,
                'request-id': request_id,
                'content-type': 'analysis-result',
                'timestamp': datetime.now().isoformat()
            }
        )
    
    def _save_translated_code(self,
                            bucket: str,
                            key: str,
                            python_code: str,
                            original_key: str,
                            request_id: str,
                            translation_result: Optional[TranslationResult] = None) -> None:
        """Save translated Python code."""
        # Prepare metadata
        metadata = {
            'source-key': original_key,
            'request-id': request_id,
            'content-type': 'translated-python-code',
            'timestamp': datetime.now().isoformat()
        }
        
        # Add translation-specific metadata if available
        if translation_result:
            metadata.update({
                'source-language': translation_result.source_language,
                'target-language': translation_result.target_language,
                'translation-success': str(translation_result.translation_success),
                'confidence-score': str(translation_result.confidence_score),
                'translation-time': str(translation_result.translation_time),
                'original-size': str(translation_result.original_size),
                'translated-size': str(translation_result.translated_size)
            })
        
        self.s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=python_code,
            ContentType='text/x-python',
            Metadata=metadata
        )
    
    def _save_processing_metadata(self,
                                bucket: str,
                                key: str,
                                processing_output: ProcessingOutput,
                                original_key: str,
                                request_id: str) -> None:
        """Save complete processing metadata."""
        metadata_content = {
            'processing_summary': {
                'original_file': original_key,
                'processing_success': processing_output.processing_success,
                'processing_time': processing_output.processing_time,
                'error_message': processing_output.error_message,
                'output_files': processing_output.output_files,
                'timestamp': datetime.now().isoformat(),
                'request_id': request_id
            },
            'processing_metadata': processing_output.processing_metadata,
            'compilation_result': processing_output.compilation_result.to_dict() if processing_output.compilation_result else None
        }
        
        self.s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(metadata_content, indent=2),
            ContentType='application/json',
            Metadata={
                'source-key': original_key,
                'request-id': request_id,
                'content-type': 'processing-metadata',
                'timestamp': datetime.now().isoformat()
            }
        )
    
    def _save_error_information(self,
                              bucket: str,
                              key: str,
                              processing_output: ProcessingOutput,
                              original_key: str,
                              request_id: str) -> None:
        """Save error information for failed processing."""
        error_content = {
            'error_summary': {
                'original_file': original_key,
                'processing_success': processing_output.processing_success,
                'error_message': processing_output.error_message,
                'timestamp': datetime.now().isoformat(),
                'request_id': request_id
            },
            'compilation_errors': processing_output.compilation_result.to_dict() if processing_output.compilation_result else None,
            'processing_metadata': processing_output.processing_metadata
        }
        
        self.s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(error_content, indent=2),
            ContentType='application/json',
            Metadata={
                'source-key': original_key,
                'request-id': request_id,
                'content-type': 'error-information',
                'timestamp': datetime.now().isoformat()
            }
        )
    
    def get_output_structure_info(self) -> Dict[str, Any]:
        """
        Get information about the S3 output directory structure.
        
        Returns:
            Dict[str, Any]: Information about output directories and naming conventions
        """
        return {
            'directories': self.directories,
            'naming_conventions': {
                'analysis': '{original_key}_{timestamp}_analysis.md',
                'translated_code': '{base_name}_{timestamp}_translated.py',
                'metadata': '{original_key}_{timestamp}_metadata.json',
                'errors': '{original_key}_{timestamp}_errors.json'
            },
            'content_types': {
                'analysis': 'text/markdown',
                'translated_code': 'text/x-python',
                'metadata': 'application/json',
                'errors': 'application/json'
            }
        }


class BackwardCompatibilityHandler:
    """
    Ensures backward compatibility with existing S3 output structure.
    
    This class maintains the existing analysis workflow while adding
    translation capabilities as additional features.
    """
    
    def __init__(self, s3_output_handler: S3OutputHandler):
        """
        Initialize backward compatibility handler.
        
        Args:
            s3_output_handler: S3 output handler instance
        """
        self.s3_output_handler = s3_output_handler
        logger.info("Backward compatibility handler initialized")
    
    def save_with_compatibility(self,
                              bucket: str,
                              original_key: str,
                              analysis_result: str,
                              processing_output: Optional[ProcessingOutput],
                              request_id: str) -> Dict[str, str]:
        """
        Save results maintaining backward compatibility.
        
        This method ensures that:
        1. Original analysis is saved in the existing format and location
        2. Translation results are saved as additional files
        3. Existing S3 bucket structure is preserved
        4. Existing naming conventions are maintained for analysis files
        
        Args:
            bucket: S3 bucket name
            original_key: Original file key
            analysis_result: Original analysis result (required for compatibility)
            processing_output: Optional translation processing output
            request_id: Request ID for tracking
            
        Returns:
            Dict[str, str]: Dictionary of all saved file paths
        """
        saved_files = {}
        
        try:
            # Always save original analysis first (backward compatibility)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            analysis_key = self.s3_output_handler._generate_analysis_key(original_key, timestamp)
            
            self.s3_output_handler._save_analysis_result(
                bucket, analysis_key, analysis_result, original_key, request_id
            )
            saved_files['analysis'] = analysis_key
            
            logger.info(f"Saved original analysis (backward compatible): s3://{bucket}/{analysis_key}")
            
            # If no processing_output exists, create a minimal one to track the analysis file
            if processing_output is None:
                processing_output = ProcessingOutput(
                    original_analysis=analysis_result,
                    processing_success=True,
                    processing_time=0.0,
                    output_files=[analysis_key],
                    processing_metadata={
                        'analysis_only': True,
                        'files_saved': 1,
                        'file_types_saved': ['analysis']
                    }
                )
            else:
                # Update existing processing_output with analysis file
                if not processing_output.output_files:
                    processing_output.output_files = []
                processing_output.output_files.append(analysis_key)
                
                if processing_output.processing_metadata is None:
                    processing_output.processing_metadata = {}
                processing_output.processing_metadata.update({
                    'analysis_saved': True,
                    'analysis_file': analysis_key
                })
            
            # Save translation results if available (additive feature)
            if processing_output and (processing_output.translated_code or processing_output.compilation_result):
                # Create a new ProcessingOutput with the analysis included
                enhanced_output = ProcessingOutput(
                    original_analysis=analysis_result,
                    translated_code=processing_output.translated_code,
                    compilation_result=processing_output.compilation_result,
                    processing_metadata=processing_output.processing_metadata or {},
                    processing_success=processing_output.processing_success,
                    processing_time=processing_output.processing_time,
                    error_message=processing_output.error_message,
                    output_files=[analysis_key]  # Start with analysis file
                )
                
                # Save additional translation files
                translation_files = self.s3_output_handler.save_translation_output(
                    bucket, original_key, enhanced_output, request_id
                )
                
                # Merge saved files (avoid duplicating analysis)
                for key, value in translation_files.items():
                    if key != 'analysis':  # Don't duplicate analysis file
                        saved_files[key] = value
                
                # Update the original processing_output with the enhanced metadata
                processing_output.output_files = enhanced_output.output_files
                if processing_output.processing_metadata is None:
                    processing_output.processing_metadata = {}
                processing_output.processing_metadata.update(enhanced_output.processing_metadata)
                
                logger.info(f"Saved translation results as additional files: {list(translation_files.keys())}")
            else:
                # For analysis-only cases, save a simple metadata file
                metadata_key = self.s3_output_handler._generate_metadata_key(original_key, timestamp)
                saved_files['metadata'] = metadata_key
                
                # Update output_files BEFORE saving metadata
                processing_output.output_files.append(metadata_key)
                
                # Update processing metadata with file information
                if processing_output.processing_metadata is None:
                    processing_output.processing_metadata = {}
                processing_output.processing_metadata.update({
                    'files_saved': len(saved_files),
                    'file_types_saved': list(saved_files.keys())
                })
                
                # Now save the metadata with the updated output_files list
                self.s3_output_handler._save_processing_metadata(
                    bucket, metadata_key, processing_output, original_key, request_id
                )
                logger.info(f"Saved analysis-only metadata to: s3://{bucket}/{metadata_key}")
            
            return saved_files
            
        except Exception as e:
            logger.error(f"Failed to save with backward compatibility: {str(e)}")
            raise
    
    def validate_existing_structure(self, bucket: str) -> bool:
        """
        Validate that the existing S3 bucket structure is preserved.
        
        Args:
            bucket: S3 bucket name to validate
            
        Returns:
            bool: True if structure is valid and compatible
        """
        try:
            # Check if analysis directory exists and is accessible
            s3_client = self.s3_output_handler.s3_client
            
            # List objects in analysis directory
            response = s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix=self.s3_output_handler.directories['analysis'],
                MaxKeys=1
            )
            
            # If we can list objects, the structure is accessible
            logger.info(f"Validated existing S3 structure in bucket: {bucket}")
            return True
            
        except Exception as e:
            logger.warning(f"Could not validate existing S3 structure: {str(e)}")
            return False


# Convenience functions for easy usage

def create_s3_output_handler(s3_client=None) -> S3OutputHandler:
    """
    Create an S3 output handler with default configuration.
    
    Args:
        s3_client: Optional boto3 S3 client
        
    Returns:
        S3OutputHandler: Configured S3 output handler
    """
    return S3OutputHandler(s3_client)


def save_translation_with_compatibility(bucket: str,
                                      original_key: str,
                                      analysis_result: str,
                                      processing_output: Optional[ProcessingOutput],
                                      request_id: str,
                                      s3_client=None) -> Dict[str, str]:
    """
    Save translation results with backward compatibility.
    
    Args:
        bucket: S3 bucket name
        original_key: Original file key
        analysis_result: Original analysis result
        processing_output: Optional translation processing output
        request_id: Request ID for tracking
        s3_client: Optional boto3 S3 client
        
    Returns:
        Dict[str, str]: Dictionary of saved file paths
    """
    output_handler = S3OutputHandler(s3_client)
    compatibility_handler = BackwardCompatibilityHandler(output_handler)
    
    return compatibility_handler.save_with_compatibility(
        bucket, original_key, analysis_result, processing_output, request_id
    )