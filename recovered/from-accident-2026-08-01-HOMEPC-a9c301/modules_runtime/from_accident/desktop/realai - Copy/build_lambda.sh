#!/bin/bash
# Build script for Lambda deployment
# This script prepares each Lambda function for deployment

set -e

echo "=============================================="
echo "Building RealAI Lambda Functions"
echo "=============================================="

# Create build directory
mkdir -p build

# Function to build a Lambda package
build_lambda() {
    local name=$1
    local handler=$2
    local requirements=$3

    echo ""
    echo "Building $name..."

    # Create function directory
    mkdir -p build/$name

    # Copy Lambda handler
    cp $handler build/$name/

    # Copy shared core module
    cp lambda_core_shared.py build/$name/

    # Copy realai.py (core module)
    cp realai.py build/$name/

    # Install dependencies if requirements file exists
    if [ -f "$requirements" ]; then
        echo "Installing dependencies from $requirements..."
        pip install -r $requirements -t build/$name/ --upgrade
    fi

    # Create ZIP package
    cd build/$name
    zip -r ../${name}.zip . -q
    cd ../..

    # Get size
    size=$(du -h build/${name}.zip | cut -f1)
    echo "✓ $name built successfully (size: $size)"
}

# Build each Lambda function
build_lambda "lambda-core" "lambda_core.py" "requirements-lambda-core.txt"
build_lambda "lambda-chat" "lambda_chat.py" "requirements-lambda-chat.txt"
build_lambda "lambda-image" "lambda_image.py" "requirements-lambda-image.txt"
build_lambda "lambda-video" "lambda_video.py" "requirements-lambda-video.txt"
build_lambda "lambda-embeddings-audio" "lambda_embeddings_audio.py" "requirements-lambda-embeddings-audio.txt"
build_lambda "lambda-advanced" "lambda_advanced.py" "requirements-lambda-advanced.txt"

echo ""
echo "=============================================="
echo "Build Summary"
echo "=============================================="
ls -lh build/*.zip

echo ""
echo "✓ All Lambda functions built successfully!"
echo ""
echo "Package files are in the build/ directory:"
echo "  - lambda-core.zip"
echo "  - lambda-chat.zip"
echo "  - lambda-image.zip"
echo "  - lambda-video.zip"
echo "  - lambda-embeddings-audio.zip"
echo "  - lambda-advanced.zip"
echo ""
echo "Next steps:"
echo "  1. Deploy using AWS SAM: sam deploy --guided"
echo "  2. Or manually upload ZIP files to AWS Lambda console"
echo "  3. See LAMBDA_DEPLOYMENT.md for detailed instructions"
