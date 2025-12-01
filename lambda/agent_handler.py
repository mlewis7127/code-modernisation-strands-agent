from strands import Agent
from strands_tools import http_request
from typing import Dict, Any
import json
import logging
import time
import boto3
import os
from datetime import datetime

# Import translation components
from translation.intelligent_orchestrator import CodeModernisationOrchestrator
from translation.language_detector import LanguageDetector
from translation.s3_output_handler import BackwardCompatibilityHandler, S3OutputHandler

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def validate_eventbridge_s3_event(event: Dict[str, Any]) -> tuple[bool, str]:
    """
    Validate that the event is a properly formatted EventBridge S3 event.
    
    Args:
        event: The incoming event to validate
        
    Returns:
        tuple: (is_valid: bool, error_message: str)
               Returns (True, "") if valid, (False, error_message) if invalid
    """
    if not isinstance(event, dict):
        error_msg = "EventBridge S3 event must be a dictionary object"
        logger.error(f"Event validation failed: {error_msg}")
        return False, error_msg
    
    required_fields = ['source', 'bucket', 'key', 'outputBucket']
    
    # Check if all required fields are present
    for field in required_fields:
        if field not in event:
            error_msg = f"Missing required field '{field}' in EventBridge S3 event. Required fields: {', '.join(required_fields)}"
            logger.error(f"EventBridge S3 event validation failed: {error_msg}")
            return False, error_msg
    
    # Validate that source indicates EventBridge
    source = event.get('source')
    if source != 'eventbridge':
        error_msg = f"Invalid event source '{source}'. Expected 'eventbridge' for EventBridge S3 events"
        logger.error(f"EventBridge S3 event validation failed: {error_msg}")
        return False, error_msg
    
    # Validate that bucket is a non-empty string
    bucket = event.get('bucket')
    if not isinstance(bucket, str) or not bucket.strip():
        error_msg = f"Invalid bucket name '{bucket}'. Must be a non-empty string"
        logger.error(f"EventBridge S3 event validation failed: {error_msg}")
        return False, error_msg
    
    # Validate that key is a non-empty string
    key = event.get('key')
    if not isinstance(key, str) or not key.strip():
        error_msg = f"Invalid object key '{key}'. Must be a non-empty string"
        logger.error(f"EventBridge S3 event validation failed: {error_msg}")
        return False, error_msg
    
    # Validate that outputBucket is a non-empty string
    output_bucket = event.get('outputBucket')
    if not isinstance(output_bucket, str) or not output_bucket.strip():
        error_msg = f"Invalid output bucket name '{output_bucket}'. Must be a non-empty string"
        logger.error(f"EventBridge S3 event validation failed: {error_msg}")
        return False, error_msg
    
    # Optional field validations with warnings
    if 'size' in event and not isinstance(event.get('size'), (int, float)):
        logger.warning(f"EventBridge S3 event contains invalid file size '{event.get('size')}'. Expected numeric value")
    
    if 'etag' in event and not isinstance(event.get('etag'), str):
        logger.warning(f"EventBridge S3 event contains invalid etag '{event.get('etag')}'. Expected string value")
    
    if 'timestamp' in event and not isinstance(event.get('timestamp'), str):
        logger.warning(f"EventBridge S3 event contains invalid timestamp '{event.get('timestamp')}'. Expected string value")
    
    logger.debug("EventBridge S3 event validation successful - all required fields present")
    return True, ""

def handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Lambda handler for EventBridge S3 events only.
    
    Args:
        event: EventBridge S3 event containing file upload information
        context: Lambda context
        
    Returns:
        Dict: Response with S3 analysis results
    """
    start_time = time.time()
    request_id = context.aws_request_id if context else "unknown"
    
    logger.info(f"[{request_id}] Starting EventBridge S3 event processing")
    logger.info(f"[{request_id}] Event source: {event.get('source', 'unknown')}, bucket: {event.get('bucket', 'unknown')}, key: {event.get('key', 'unknown')}")
    
    try:
        # Validate that this is an EventBridge S3 event
        is_valid, validation_error = validate_eventbridge_s3_event(event)
        if not is_valid:
            logger.error(f"[{request_id}] EventBridge S3 event validation failed: {validation_error}")
            return {
                'status': 'error',
                'message': f"Invalid EventBridge S3 event: {validation_error}",
                'request_id': request_id
            }
        
        logger.info(f"[{request_id}] EventBridge S3 event validation successful")
        
        # Process the S3 event
        return process_s3_event(event, context, start_time)
            
    except Exception as e:
        logger.error(f"[{request_id}] Critical error processing EventBridge S3 event: {str(e)}")
        return {
            'status': 'error',
            'message': f"EventBridge S3 event processing failed: {str(e)}",
            'request_id': request_id
        }

def process_s3_event(event: Dict[str, Any], context, start_time: float) -> Dict[str, Any]:
    """Process S3 events from EventBridge for translation workflow only."""
    request_id = context.aws_request_id if context else "unknown"
    
    logger.info(f"[{request_id}] Beginning S3 file translation from EventBridge event")
    logger.info(f"[{request_id}] EventBridge S3 event details: {json.dumps(event, default=str)}")
    
    try:
        # Extract S3 information from EventBridge event with enhanced validation
        bucket_name = event.get('bucket')
        object_key = event.get('key')
        output_bucket = event.get('outputBucket')
        file_size = event.get('size', 0)
        etag = event.get('etag', '')
        timestamp = event.get('timestamp', '')
        
        if not bucket_name or not object_key:
            error_msg = "Missing bucket name or object key in S3 event"
            logger.error(error_msg)
            return {'status': 'error', 'message': error_msg}
        
        logger.info(f"[{request_id}] Starting translation check for S3 file: s3://{bucket_name}/{object_key}")
        
        # Read the file from S3 with enhanced error handling
        s3_client = boto3.client('s3')
        
        try:
            # First, check if the object exists and get metadata
            try:
                head_response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
                actual_file_size = head_response['ContentLength']
                
                logger.info(f"[{request_id}] S3 file metadata retrieved: {object_key} ({actual_file_size:,} bytes)")

            except Exception as e:
                if "AccessDenied" in str(e) or "Forbidden" in str(e):
                    error_msg = f"Access denied to file: s3://{bucket_name}/{object_key}. Check IAM permissions for S3 GetObject operation."
                    logger.error(f"[{request_id}] S3 access denied: {error_msg}")
                    return {'status': 'error', 'message': error_msg, 'request_id': request_id}
                else:
                    error_msg = f"Failed to access file metadata: s3://{bucket_name}/{object_key}. Error: {str(e)}"
                    logger.error(f"[{request_id}] S3 metadata access failed: {error_msg}")
                    return {'status': 'error', 'message': error_msg, 'request_id': request_id}
            
            # Now read the file content
            response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
            
            try:
                file_content = response['Body'].read().decode('utf-8')
                logger.info(f"[{request_id}] Successfully read S3 file content: {object_key} ({actual_file_size:,} bytes)")
                
            except UnicodeDecodeError as e:
                error_msg = f"Failed to decode file as UTF-8: s3://{bucket_name}/{object_key}. The file may be binary or use a different encoding. Error: {str(e)}"
                logger.error(f"[{request_id}] S3 file encoding error: {error_msg}")
                return {'status': 'error', 'message': error_msg, 'request_id': request_id}
            except Exception as e:
                error_msg = f"Failed to read file content: s3://{bucket_name}/{object_key}. Error: {str(e)}"
                logger.error(f"[{request_id}] S3 file read error: {error_msg}")
                return {'status': 'error', 'message': error_msg, 'request_id': request_id}
            
        except Exception as e:
            # Catch-all for any other S3-related errors
            if "AccessDenied" in str(e) or "Forbidden" in str(e):
                error_msg = f"Access denied to S3 resource: s3://{bucket_name}/{object_key}. Verify IAM permissions for S3 operations."
            elif "NoSuchKey" in str(e):
                error_msg = f"File not found: s3://{bucket_name}/{object_key}. The object may have been deleted or moved."
            elif "NoSuchBucket" in str(e):
                error_msg = f"Bucket not found: '{bucket_name}'. Verify the bucket name and region."
            else:
                error_msg = f"S3 operation failed for s3://{bucket_name}/{object_key}. Error: {str(e)}"
            
            logger.error(f"[{request_id}] S3 operation failed: {error_msg}")
            return {'status': 'error', 'message': error_msg, 'request_id': request_id}
        
        # Determine file type from extension
        file_extension = object_key.split('.')[-1].lower() if '.' in object_key else 'unknown'
        
        # Check if translation is needed and supported
        language_detector = LanguageDetector()
        detected_language = language_detector.detect_language(object_key, file_content)
        
        logger.info(f"[{request_id}] Detected language: {detected_language}")
        
        # Initialize translation workflow variables
        translation_output = None
        translation_error = None
        translation_error_type = None
        
        # Process any supported language (including Python) through the intelligent orchestrator
        if detected_language != 'unknown' and language_detector.is_supported_language(detected_language):
            
            is_python = detected_language.lower() == 'python'
            workflow_type = "Python quality analysis" if is_python else "Translation workflow"
            
            logger.info(f"[{request_id}] Starting {workflow_type} for {detected_language} code")
            
            # Prepare file info for processing
            file_info = {
                'file_path': object_key,
                'key': object_key,
                'bucket': bucket_name,
                'size': actual_file_size,
                'etag': etag,
                'timestamp': timestamp,
                'detected_language': detected_language
            }
            
            logger.info(f"[{request_id}] Running {workflow_type} for {detected_language} code")
            
            try:
                # Initialize CodeModernisationOrchestrator
                # Uses default Claude 3 Sonnet model and us-east-1 region
                orchestrator = CodeModernisationOrchestrator()
                
                # Create user request based on detected language
                if is_python:
                    user_request = "This is Python code. Compile and validate it, analyze code quality, and apply any recommended improvements."
                else:
                    user_request = f"Process this {detected_language} code file: translate to Python if needed, compile and validate the result, fix any errors, and ensure quality."
                
                # Run orchestration workflow with error handling
                try:
                    orchestration_result = orchestrator.process_code_request(
                        file_content, file_info, user_request
                    )
                    
                    translation_output = orchestration_result.processing_output
                    
                    if translation_output.processing_success:
                        logger.info(f"[{request_id}] {workflow_type} completed successfully")
                    else:
                        translation_error = translation_output.error_message or f"{workflow_type} failed without specific error message"
                        translation_error_type = "PYTHON_QUALITY_WARNING" if is_python else "TRANSLATION_PROCESSING_ERROR"
                        logger.warning(f"[{request_id}] {workflow_type} completed with errors: {translation_error}")
   
                except Exception as e:
                    translation_error = f"{workflow_type} failed: {str(e)}"
                    translation_error_type = "PYTHON_ANALYSIS_ERROR" if is_python else "TRANSLATION_ERROR"
                    logger.error(f"[{request_id}] {translation_error}", exc_info=True)
                    
            except Exception as e:
                # Handle orchestrator initialization or execution errors
                translation_error = f"Failed to initialize {workflow_type}: {str(e)}"
                translation_error_type = "PYTHON_INIT_ERROR" if is_python else "TRANSLATION_ERROR"
                logger.error(f"[{request_id}] {translation_error}", exc_info=True)
        elif detected_language == 'unknown':
            logger.info(f"[{request_id}] Could not detect language, skipping translation")
        else:
            logger.info(f"[{request_id}] Language {detected_language} not supported for translation")
        
        # Save translation results if available
        output_save_error = None
        saved_files = {}
        
        if output_bucket and translation_output:
            try:
                # Use S3OutputHandler to save translation results only
                s3_output_handler = S3OutputHandler(s3_client)
                
                # Save translation results only (no analysis)
                saved_files = s3_output_handler.save_translation_output(
                    bucket=output_bucket,
                    original_key=object_key,
                    processing_output=translation_output,
                    request_id=request_id
                )
                
                logger.info(f"[{request_id}] Translation results saved to S3")
                logger.info(f"[{request_id}] Saved files: {list(saved_files.keys())}")
                
            except Exception as e:
                # Handle S3 save errors gracefully
                error_str = str(e)
                if "AccessDenied" in error_str or "Forbidden" in error_str:
                    output_save_error = f"Access denied to output bucket: s3://{output_bucket}. Check IAM permissions for S3 PutObject operation."
                elif "NoSuchBucket" in error_str:
                    output_save_error = f"Output bucket not found: '{output_bucket}'. Verify the bucket exists and is accessible."
                else:
                    output_save_error = f"Failed to save results to output bucket: s3://{output_bucket}. Error: {error_str}"
                
                logger.errorave_error = f"Failed to save results to output bucket: s3://{output_bucket}. Error: {error_str}"
                
                logger.error(f"[{request_id}] Output save failed: {output_save_error}")
        
        # Save translation error information if needed
        if translation_error and translation_error_type and output_bucket:
            try:
                error_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                error_key = f"translated/errors/{object_key.replace('/', '_')}_{error_timestamp}_translation_error.json"
                
                error_info = {
                    'error_type': translation_error_type,
                    'error_message': translation_error,
                    'original_file': object_key,
                    'detected_language': detected_language,
                    'timestamp': error_timestamp,
                    'request_id': request_id,
                    'file_size': actual_file_size
                }
                
                s3_client.put_object(
                    Bucket=output_bucket,
                    Key=error_key,
                    Body=json.dumps(error_info, indent=2),
                    ContentType='application/json',
                    Metadata={
                        'source-key': object_key,
                        'request-id': request_id,
                        'content-type': 'translation-error',
                        'error-type': translation_error_type,
                        'timestamp': error_timestamp
                    }
                )
                
                saved_files['translation_error'] = error_key
                logger.info(f"[{request_id}] Translation error information saved to: s3://{output_bucket}/{error_key}")
                
            except Exception as error_save_exc:
                logger.warning(f"[{request_id}] Failed to save translation error information: {str(error_save_exc)}")
        
        processing_time = time.time() - start_time
        
        # Prepare comprehensive translation summary for response
        translation_summary = {}
        if translation_output:
            translation_summary = {
                'translation_attempted': True,
                'translation_success': translation_output.processing_success,
                'translated_code_available': bool(translation_output.translated_code),
                'compilation_success': translation_output.compilation_result.compilation_success if translation_output.compilation_result else None,
                'processing_time': translation_output.processing_time
            }
            if translation_output.error_message:
                translation_summary['error_message'] = translation_output.error_message
            if translation_output.compilation_result and translation_output.compilation_result.errors:
                translation_summary['compilation_errors'] = translation_output.compilation_result.errors[:3]  # Limit to first 3 errors
        elif translation_error:
            translation_summary = {
                'translation_attempted': True,
                'translation_success': False,
                'error_type': translation_error_type,
                'error_message': translation_error,
                'detected_language': detected_language
            }
        else:
            # Determine why translation was not attempted
            if detected_language == 'unknown':
                reason = 'Could not detect programming language'
            elif detected_language.lower() == 'python':
                reason = 'File is already Python'
            elif not language_detector.is_supported_language(detected_language):
                reason = f'Language {detected_language} not supported for translation'
            else:
                reason = 'Translation not needed'
                
            translation_summary = {
                'translation_attempted': False,
                'reason': reason,
                'detected_language': detected_language
            }
        
        # Response format focused on translation
        result = {
            'status': 'success',
            'message': 'S3 file translation processing completed' + (f' (Warning: {output_save_error})' if output_save_error else ''),
            'request_id': request_id,
            'input': {
                'bucket': bucket_name,
                'key': object_key,
                'file_size': actual_file_size,
                'file_type': file_extension,
                'detected_language': detected_language
            },
            'output': {
                'bucket': output_bucket,
                'saved_files': saved_files if saved_files else {},
                'save_error': output_save_error
            },
            'translation': translation_summary,
            'processing_time_seconds': round(processing_time, 3)
        }
        
        logger.info(f"[{request_id}] EventBridge S3 file translation processing completed in {processing_time:.2f}s")
        return result
        
    except Exception as e:
        processing_time = time.time() - start_time
        error_str = str(e)
        
        # Categorize the error for better debugging
        if "bedrock" in error_str.lower():
            error_category = "BEDROCK_ERROR"
        elif "s3" in error_str.lower():
            error_category = "S3_ERROR"
        elif "translation" in error_str.lower():
            error_category = "TRANSLATION_ERROR"
        elif "timeout" in error_str.lower():
            error_category = "TIMEOUT_ERROR"
        elif "memory" in error_str.lower() or "resource" in error_str.lower():
            error_category = "RESOURCE_ERROR"
        else:
            error_category = "GENERAL_ERROR"
        
        logger.error(f"[{request_id}] Critical error ({error_category}) in EventBridge S3 translation processing after {processing_time:.2f}s: {error_str}")
        
        # Try to save error information if we have the necessary context
        try:
            if 'output_bucket' in locals() and 'object_key' in locals() and output_bucket:
                error_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                error_key = f"logs/{object_key.replace('/', '_')}_{error_timestamp}_processing_error.json"
                
                error_info = {
                    'error_category': error_category,
                    'error_message': error_str,
                    'original_file': object_key,
                    'processing_time': processing_time,
                    'timestamp': error_timestamp,
                    'request_id': request_id
                }
                
                s3_client.put_object(
                    Bucket=output_bucket,
                    Key=error_key,
                    Body=json.dumps(error_info, indent=2),
                    ContentType='application/json'
                )
                
                logger.info(f"[{request_id}] Error information saved to: s3://{output_bucket}/{error_key}")
                
        except Exception as save_error:
            logger.warning(f"[{request_id}] Could not save error information: {str(save_error)}")
        
        return {
            'status': 'error',
            'message': f"EventBridge S3 translation processing failed: {error_str}",
            'error_category': error_category,
            'request_id': request_id,
            'processing_time_seconds': round(processing_time, 3),
            'input': {
                'bucket': locals().get('bucket_name', 'unknown'),
                'key': locals().get('object_key', 'unknown')
            }
        }