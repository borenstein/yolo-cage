#!/bin/bash
# Build yolo-cage zipapp
set -e

cd "$(dirname "$0")/.."

VERSION=${1:-dev}

# Update version in __init__.py
sed -i "s/__version__ = \"dev\"/__version__ = \"$VERSION\"/" yolo_cage/__init__.py

# Create dist directory
mkdir -p dist

# Build zipapp
python3 -m zipapp yolo_cage -o dist/yolo-cage -p "/usr/bin/env python3" -c

# Restore dev version
git checkout yolo_cage/__init__.py

echo "Built dist/yolo-cage (version: $VERSION)"
