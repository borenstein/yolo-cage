#!/bin/bash
# Build yolo-cage as a zipapp (single-file executable)
#
# Usage:
#   ./scripts/build-zipapp.sh [VERSION]
#
# If VERSION is not provided, uses "dev".

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
VERSION="${1:-dev}"

cd "$REPO_ROOT"

# Create dist directory
mkdir -p dist

# Update version in __init__.py
if [[ "$VERSION" != "dev" ]]; then
    sed -i "s/__version__ = \"dev\"/__version__ = \"$VERSION\"/" yolo_cage/__init__.py
fi

# Create zipapp
# Note: We need to copy the package to a temp location because zipapp
# expects the package to be the only thing in the source directory
TEMP_DIR=$(mktemp -d)
cp -r yolo_cage "$TEMP_DIR/"

python3 -m zipapp "$TEMP_DIR" \
    --output dist/yolo-cage \
    --python "/usr/bin/env python3" \
    --main "yolo_cage.cli:main"

rm -rf "$TEMP_DIR"

# Restore dev version if we changed it
if [[ "$VERSION" != "dev" ]]; then
    git checkout yolo_cage/__init__.py 2>/dev/null || sed -i "s/__version__ = \"$VERSION\"/__version__ = \"dev\"/" yolo_cage/__init__.py
fi

echo "Built dist/yolo-cage (version: $VERSION)"
chmod +x dist/yolo-cage
