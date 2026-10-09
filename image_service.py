import os
import uuid
from PIL import Image
from werkzeug.utils import secure_filename
from flask import current_app

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB per image

def is_allowed_file(filename: str) -> bool:
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS

def validate_and_save_image(file_storage, folder_type: str = 'before') -> tuple[str, str, int]:
    """
    Validates an uploaded image and saves it securely.
    
    Args:
        file_storage: Werkzeug FileStorage object
        folder_type: 'before' or 'after'
        
    Returns:
        tuple of (relative_file_path, original_filename, file_size_bytes)
        
    Raises:
        ValueError: If file is invalid, unsupported format, or too large.
    """
    if not file_storage or not file_storage.filename:
        raise ValueError("No file provided.")

    original_filename = secure_filename(file_storage.filename)
    if not is_allowed_file(original_filename):
        raise ValueError("Unsupported file format. Please upload JPG, PNG, or WEBP images only.")

    # Read bytes to check file size and inspect with Pillow
    file_bytes = file_storage.read()
    file_size = len(file_bytes)
    
    if file_size > MAX_FILE_SIZE:
        raise ValueError(f"File size exceeds maximum limit of {MAX_FILE_SIZE // (1024 * 1024)} MB.")
    
    if file_size == 0:
        raise ValueError("Uploaded file is empty.")

    # Reset stream for Pillow
    file_storage.seek(0)
    
    try:
        # Verify genuine image structure using Pillow
        with Image.open(file_storage) as img:
            img_format = img.format.lower()
            if img_format not in {'jpeg', 'png', 'webp'}:
                raise ValueError("Image file format verification failed. Unrecognized image stream.")
            
            # Sanitize image by converting to RGB / RGBA and re-saving
            # This strips potential malicious payloads or corrupt metadata
            ext = 'jpg' if img_format == 'jpeg' else img_format
            unique_filename = f"{uuid.uuid4().hex}.{ext}"
            
            target_dir = current_app.config['UPLOAD_BEFORE_FOLDER'] if folder_type == 'before' else current_app.config['UPLOAD_AFTER_FOLDER']
            os.makedirs(target_dir, exist_ok=True)
            save_path = os.path.join(target_dir, unique_filename)
            
            # Save normalized image
            if img.mode in ('RGBA', 'LA') and ext == 'jpg':
                # Convert transparent PNG to RGB before saving as JPG
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                background.save(save_path, 'JPEG', quality=85)
            elif img.mode not in ('RGB', 'RGBA', 'L'):
                rgb_img = img.convert('RGB')
                rgb_img.save(save_path, 'JPEG' if ext == 'jpg' else ext.upper(), quality=85)
            else:
                img.save(save_path, 'JPEG' if ext == 'jpg' else ext.upper(), quality=85)

        relative_path = f"uploads/{folder_type}/{unique_filename}"
        return relative_path, original_filename, file_size

    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Invalid image file: {str(e)}")
