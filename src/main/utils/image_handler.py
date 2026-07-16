"""
Image Handler Utility
Handles image uploads, storage, and path management
"""
import os
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional


class ImageHandler:
    """Manages image uploads and storage for the application."""
    
    def __init__(self, base_dir: str = None):
        """
        Initialize image handler.
        
        Args:
            base_dir: Base directory for storing images. 
                     Defaults to ~/.disassembly_diagram/images/
        """
        if base_dir is None:
            app_dir = os.path.join(os.path.expanduser("~"), ".disassembly_diagram")
            self.images_dir = os.path.join(app_dir, "images")
        else:
            self.images_dir = os.path.join(base_dir, "images")
        
        # Create images directory if it doesn't exist
        os.makedirs(self.images_dir, exist_ok=True)
    
    def upload_image(self, source_path: str, entity_type: str = "component", 
                    entity_id: Optional[int] = None, product_name: str = None, 
                    existing_path: str = None) -> Optional[str]:
        """
        Upload and store an image file with duplicate detection.
        
        Args:
            source_path: Path to the source image file
            entity_type: Type of entity ('component', 'action', 'step')
            entity_id: Optional ID of the entity
            product_name: Product name for folder organization
            
        Returns:
            Relative path to the stored image, or None if upload failed
        """
        if not os.path.exists(source_path):
            return None
        
        # Validate image format
        valid_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
        file_ext = os.path.splitext(source_path)[1].lower()
        
        if file_ext not in valid_extensions:
            return None
        
        # Create product-specific folder structure
        if product_name:
            # Sanitize product name for folder
            safe_name = self._sanitize_filename(product_name)
            product_dir = os.path.join(self.images_dir, safe_name)
        else:
            # Default to 'default_product' if no name
            product_dir = os.path.join(self.images_dir, "default_product")
        
        # Create subdirectories within product folder
        if entity_type == "action":
            target_dir = os.path.join(product_dir, "actions")
            prefix = "action"
        elif entity_type == "step":
            target_dir = os.path.join(product_dir, "steps")
            prefix = "step"
        else:
            target_dir = os.path.join(product_dir, "components")
            prefix = "component"
        
        # Ensure directory exists
        os.makedirs(target_dir, exist_ok=True)
        
        # Calculate hash of source file
        source_hash = self._calculate_file_hash(source_path)
        
        # Check if file with same content already exists
        existing_file = self._find_existing_by_hash(target_dir, source_hash)
        if existing_file:
            # Return path to existing file (no copy needed)
            relative_path = os.path.relpath(existing_file, self.images_dir)
            return f"images/{relative_path}".replace("\\", "/")
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if entity_id:
            filename = f"{prefix}_{entity_id}_{timestamp}{file_ext}"
        else:
            filename = f"{prefix}_{timestamp}{file_ext}"
        
        target_path = os.path.join(target_dir, filename)
        
        # Copy the file
        try:
            shutil.copy2(source_path, target_path)
            
            # Return relative path from images directory
            relative_path = os.path.relpath(target_path, self.images_dir)
            return f"images/{relative_path}".replace("\\", "/")
            
        except (OSError, shutil.Error, ValueError):
            return None
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate MD5 hash of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            MD5 hash string
        """
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                # Read in chunks to handle large files
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except (OSError, ValueError):
            return ""
    
    def _find_existing_by_hash(self, directory: str, target_hash: str) -> Optional[str]:
        """
        Find existing file in directory with matching hash.
        
        Args:
            directory: Directory to search in
            target_hash: Hash to match
            
        Returns:
            Full path to existing file, or None if not found
        """
        if not target_hash or not os.path.exists(directory):
            return None
        
        try:
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                if os.path.isfile(file_path):
                    file_hash = self._calculate_file_hash(file_path)
                    if file_hash == target_hash:
                        return file_path
        except (OSError, ValueError):
            pass
        
        return None
    
    def _sanitize_filename(self, name: str) -> str:
        """Sanitize product name for use as folder name."""
        import re
        # Replace spaces and special chars with underscore
        safe = re.sub(r'[^\w\-]', '_', name)
        # Remove consecutive underscores
        safe = re.sub(r'_+', '_', safe)
        # Limit length
        return safe[:50].strip('_')
    
    def get_full_path(self, relative_path: str) -> str:
        """
        Get full path from relative path stored in database.
        
        Args:
            relative_path: Relative path from database (e.g., 'images/components/...')
            
        Returns:
            Full absolute path to the image
        """
        if not relative_path:
            return ""
        
        # If it's already an absolute path, return it
        if os.path.isabs(relative_path):
            return relative_path
        
        # Remove 'images/' prefix if present
        if relative_path.startswith("images/"):
            relative_path = relative_path[7:]
        
        return os.path.join(self.images_dir, relative_path)
    
    def image_exists(self, relative_path: str) -> bool:
        """Check if image file exists."""
        if not relative_path:
            return False
        
        full_path = self.get_full_path(relative_path)
        return os.path.exists(full_path)
    
    def delete_image(self, relative_path: str) -> bool:
        """
        Delete an image file.
        
        Args:
            relative_path: Relative path to the image
            
        Returns:
            True if deleted successfully, False otherwise
        """
        if not relative_path:
            return False
        
        full_path = self.get_full_path(relative_path)
        
        try:
            if os.path.exists(full_path):
                os.remove(full_path)
                return True
        except (OSError, ValueError):
            return False
        
        return False


# Singleton instance
_image_handler = None


def get_image_handler() -> ImageHandler:
    """Get singleton image handler instance."""
    global _image_handler
    if _image_handler is None:
        _image_handler = ImageHandler()
    return _image_handler
