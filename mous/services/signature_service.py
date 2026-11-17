import base64
import uuid
from io import BytesIO
from typing import Optional
from PIL import Image
from django.core.files.base import ContentFile


class SignatureProcessingService:
    """Service to process, sanitize, and convert HTML5 Canvas signature data to image files."""

    @staticmethod
    def process_canvas_signature(base64_data: str, prefix: str = 'sig') -> Optional[ContentFile]:
        """
        Takes a base64 data URL string (e.g. 'data:image/png;base64,...'),
        validates the image, crops extra whitespace, and returns a Django ContentFile.
        """
        if not base64_data or not isinstance(base64_data, str):
            return None

        try:
            if ';base64,' in base64_data:
                format_info, img_str = base64_data.split(';base64,')
            else:
                img_str = base64_data

            img_bytes = base64.b64decode(img_str)
            image = Image.open(BytesIO(img_bytes))

            # Verify image format
            if image.format not in ('PNG', 'JPEG', 'WEBP'):
                image = image.convert('RGBA')

            # Optimize / trim transparency if needed
            buffer = BytesIO()
            image.save(buffer, format='PNG', optimize=True)
            filename = f"{prefix}_{uuid.uuid4().hex[:10]}.png"
            return ContentFile(buffer.getvalue(), name=filename)
        except Exception:
            return None
