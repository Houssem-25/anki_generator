"""
Image generation service using Cloudflare AI.
Handles image generation and management.
"""

import json
import base64
import subprocess
import shutil
from pathlib import Path
from typing import Optional
from abc import ABC, abstractmethod

from structures import MediaFile


class ImageService(ABC):
    """Abstract base class for image services."""
    
    @abstractmethod
    def generate_image(self, prompt: str, filename: str, output_dir: Path) -> Optional[MediaFile]:
        """Generate image from prompt."""
        pass
    
    @abstractmethod
    def copy_to_anki_media(self, media_file: MediaFile, anki_media_path: Path) -> bool:
        """Copy image file to Anki media directory."""
        pass


class CloudflareImageService(ImageService):
    """Cloudflare AI implementation for image generation."""
    
    def __init__(self, account_id: str, api_token: str):
        self.account_id = account_id
        self.api_token = api_token
        self.api_endpoint = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    
    def generate_image(self, prompt: str, filename: str, output_dir: Path) -> Optional[MediaFile]:
        """Generate image from prompt using Cloudflare AI."""
        if not prompt or not filename:
            print("Warning: generate_image called with empty prompt or filename.")
            return None
        
        try:
            # Ensure output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create full file path
            safe_filename = self._sanitize_filename(filename)
            image_filename = f"{safe_filename}.png"
            output_path = output_dir / image_filename
            
            # Check if file already exists
            if output_path.exists():
                print(f"Image file already exists: {output_path}")
                return MediaFile(
                    filename=image_filename,
                    file_path=output_path,
                    file_type="image"
                )
            
            # Generate image using Cloudflare AI
            base64_image = self._call_cloudflare_api(prompt)
            if not base64_image:
                return None
            
            # Save image to file
            image_bytes = base64.b64decode(base64_image)
            with open(output_path, 'wb') as img_file:
                img_file.write(image_bytes)
            
            print(f"Image saved to: {output_path}")
            
            return MediaFile(
                filename=image_filename,
                file_path=output_path,
                file_type="image"
            )
            
        except Exception as e:
            print(f"Error generating image for '{filename}': {e}")
            return None
    
    def copy_to_anki_media(self, media_file: MediaFile, anki_media_path: Path) -> bool:
        """Copy image file to Anki media directory."""
        if not anki_media_path or not anki_media_path.is_dir():
            print(f"Warning: Anki media directory not found or not a directory: {anki_media_path}")
            return False
        
        try:
            # Ensure Anki media directory exists
            anki_media_path.mkdir(parents=True, exist_ok=True)
            
            # Create destination path
            dest_path = anki_media_path / media_file.filename
            
            # Copy file
            shutil.copy2(media_file.file_path, dest_path)
            print(f"Image file copied to Anki media: {dest_path}")
            
            return True
            
        except Exception as e:
            print(f"Warning: Failed to copy image '{media_file.filename}' to Anki media: {e}")
            return False
    
    def _call_cloudflare_api(self, prompt: str) -> Optional[str]:
        """Call Cloudflare AI API to generate image."""
        try:
            # Construct the enhanced prompt
            enhanced_prompt = self._create_enhanced_prompt(prompt)
            
            # Prepare API call
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            data = json.dumps({"prompt": enhanced_prompt})
            
            # Execute curl command
            command = [
                "curl", "-s", "-X", "POST", self.api_endpoint,
                "-H", f"Authorization: {headers['Authorization']}",
                "-H", f"Content-Type: {headers['Content-Type']}",
                "-d", data
            ]
            
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                timeout=60
            )
            
            # Parse response
            response_json = json.loads(process.stdout)
            
            if "result" in response_json and "image" in response_json["result"]:
                return response_json["result"]["image"]
            else:
                print(f"Error: Unexpected JSON response format from Cloudflare AI. Response: {response_json}")
                return None
                
        except subprocess.CalledProcessError as e:
            print(f"Error calling Cloudflare AI (curl failed): {e}")
            if e.stderr:
                print(f"Stderr: {e.stderr}")
            return None
        except subprocess.TimeoutExpired:
            print(f"Error: Cloudflare AI request timed out")
            return None
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON response from Cloudflare AI: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred during image generation: {e}")
            return None
    
    def _create_enhanced_prompt(self, base_prompt: str) -> str:
        """Create enhanced prompt for better image generation."""
        return f"""
Create a vibrant, flashcard illustration for the word '{base_prompt}'.
SCENE DETAILS:
- Create a clear, engaging scene that instantly communicates the word's meaning
- Include characters demonstrating the word through their actions/interactions
- Maintain a clean, uncluttered background to help with focus and memory retention

LEARNING EFFECTIVENESS:
- Position the key concept centrally with strong visual hierarchy
- Include 1-2 distinctive visual elements that serve as memory anchors
- Use color psychology to enhance emotional connection
- Create a visual that works effectively at flashcard size
"""
    
    def _sanitize_filename(self, text: str) -> str:
        """Sanitize text for use as a filename."""
        # Replace spaces and special characters with underscores
        # Keep umlauts and other German characters
        sanitized = text.strip()
        sanitized = ''.join(c if c.isalnum() or c in 'äöüÄÖÜß' else '_' for c in sanitized)
        return sanitized
    
    def create_image_tag(self, filename: str) -> str:
        """Create Anki image tag for the image file."""
        return f'<img src="{filename}"><br>'


class MockImageService(ImageService):
    """Mock image service for testing."""
    
    def __init__(self):
        self.generated_files = []
        self.copied_files = []
    
    def generate_image(self, prompt: str, filename: str, output_dir: Path) -> Optional[MediaFile]:
        """Mock image generation."""
        safe_filename = self._sanitize_filename(filename)
        image_filename = f"{safe_filename}.png"
        output_path = output_dir / image_filename
        
        # Create empty file for testing
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path.touch()
        
        media_file = MediaFile(
            filename=image_filename,
            file_path=output_path,
            file_type="image"
        )
        
        self.generated_files.append(media_file)
        return media_file
    
    def copy_to_anki_media(self, media_file: MediaFile, anki_media_path: Path) -> bool:
        """Mock copy to Anki media."""
        self.copied_files.append((media_file, anki_media_path))
        return True
    
    def _sanitize_filename(self, text: str) -> str:
        """Sanitize text for use as a filename."""
        sanitized = text.strip()
        sanitized = ''.join(c if c.isalnum() or c in 'äöüÄÖÜß' else '_' for c in sanitized)
        return sanitized
    
    def create_image_tag(self, filename: str) -> str:
        """Create Anki image tag for the image file."""
        return f'<img src="{filename}"><br>'


def create_image_service(account_id: str, api_token: str) -> ImageService:
    """Factory function to create image service."""
    return CloudflareImageService(account_id, api_token)


def create_mock_image_service() -> ImageService:
    """Factory function to create mock image service for testing."""
    return MockImageService()
