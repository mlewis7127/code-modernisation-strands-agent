#!/usr/bin/env python3
"""
Lambda packaging script for Agents-as-Tools Strands Agent.

This script packages the Lambda function code and dependencies for deployment.
It creates two zip files:
1. dependencies.zip - Lambda layer with Python packages
2. app.zip - Lambda function code
"""

import os
import sys
import shutil
import zipfile
import subprocess
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a shell command and return the result."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running command: {cmd}")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        sys.exit(1)
    return result

def create_directories():
    """Create necessary directories for packaging."""
    packaging_dir = Path("packaging")
    dependencies_dir = packaging_dir / "_dependencies"
    
    # Clean and create directories
    if packaging_dir.exists():
        shutil.rmtree(packaging_dir)
    
    packaging_dir.mkdir(exist_ok=True)
    dependencies_dir.mkdir(exist_ok=True)
    
    return packaging_dir, dependencies_dir

def install_dependencies(dependencies_dir):
    """Install Python dependencies for Lambda layer."""
    print("Installing Python dependencies for Lambda layer...")
    
    # Install dependencies with ARM64 architecture for Lambda
    cmd = f"""pip install -r requirements.txt \
        --python-version 3.12 \
        --platform manylinux2014_aarch64 \
        --target {dependencies_dir} \
        --only-binary=:all:"""
    
    run_command(cmd)

def create_dependencies_zip(packaging_dir, dependencies_dir):
    """Create the dependencies.zip file for Lambda layer."""
    print("Creating dependencies.zip for Lambda layer...")
    
    zip_path = packaging_dir / "dependencies.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(dependencies_dir):
            for file in files:
                file_path = Path(root) / file
                # Calculate relative path from dependencies directory
                # Lambda layers need python/ prefix for Python packages
                arcname = Path("python") / file_path.relative_to(dependencies_dir)
                zipf.write(file_path, arcname)
    
    print(f"Created {zip_path} ({zip_path.stat().st_size / 1024 / 1024:.1f} MB)")
    return zip_path

def create_app_zip(packaging_dir):
    """Create the app.zip file for Lambda function code."""
    print("Creating app.zip for Lambda function...")
    
    zip_path = packaging_dir / "app.zip"
    lambda_dir = Path("lambda")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add all Python files from lambda directory
        for root, dirs, files in os.walk(lambda_dir):
            # Skip __pycache__ directories
            dirs[:] = [d for d in dirs if d != '__pycache__']
            
            for file in files:
                if file.endswith(('.py', '.json', '.txt', '.md')):
                    file_path = Path(root) / file
                    # Calculate relative path from lambda directory
                    arcname = file_path.relative_to(lambda_dir)
                    zipf.write(file_path, arcname)
    
    print(f"Created {zip_path} ({zip_path.stat().st_size / 1024:.1f} KB)")
    return zip_path

def verify_packages(dependencies_dir):
    """Verify that required packages are installed."""
    print("Verifying required packages...")
    
    required_packages = [
        'strands',
        'strands_tools',  # This is the actual package name
        'boto3',
        'botocore',
        'bedrock_agentcore'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        package_path = dependencies_dir / package
        if not package_path.exists():
            # Try with underscores replaced with dashes
            alt_package = package.replace('_', '-')
            alt_path = dependencies_dir / alt_package
            if not alt_path.exists():
                missing_packages.append(package)
    
    if missing_packages:
        print(f"Warning: Missing packages: {missing_packages}")
        print("This might cause runtime errors in Lambda.")
    else:
        print("✅ All required packages found!")

def main():
    """Main packaging function."""
    print("🚀 Starting Lambda packaging for Agents-as-Tools...")
    
    # Ensure we're in the project root
    if not Path("requirements.txt").exists():
        print("Error: requirements.txt not found. Run this script from the project root.")
        sys.exit(1)
    
    if not Path("lambda").exists():
        print("Error: lambda directory not found. Run this script from the project root.")
        sys.exit(1)
    
    try:
        # Create directories
        packaging_dir, dependencies_dir = create_directories()
        
        # Install dependencies
        install_dependencies(dependencies_dir)
        
        # Verify packages
        verify_packages(dependencies_dir)
        
        # Create zip files
        deps_zip = create_dependencies_zip(packaging_dir, dependencies_dir)
        app_zip = create_app_zip(packaging_dir)
        
        print("\n✅ Lambda packaging completed successfully!")
        print(f"📦 Dependencies: {deps_zip}")
        print(f"📦 Application: {app_zip}")
        print("\nYou can now deploy with: npx cdk deploy")
        
    except Exception as e:
        print(f"\n❌ Packaging failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()