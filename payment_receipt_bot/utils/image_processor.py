"""
Image processing utilities
"""
from PIL import Image
from pathlib import Path
from typing import Optional, Tuple


def compress_image(input_path: Path, output_path: Optional[Path] = None,
                   quality: int = 85,
                   max_size: Tuple[int, int] = (1080, 1920)) -> Path:
    """
    Compress and optimize image for Telegram
    Telegram max: 10MB for photos
    """
    if output_path is None:
        output_path = input_path.with_name(f"{input_path.stem}_compressed.jpg")
    
    with Image.open(input_path) as img:
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # Resize if too large
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Save as JPEG with compression
        img.save(
            output_path,
            'JPEG',
            quality=quality,
            optimize=True,
            progressive=True
        )
    
    return output_path


def get_image_size(file_path: Path) -> int:
    """Get file size in bytes"""
    return file_path.stat().st_size