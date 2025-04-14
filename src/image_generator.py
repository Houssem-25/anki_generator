# src/image_generator.py
import subprocess # For calling curl
import json # For parsing curl response
import base64 # For decoding/encoding image data

def generate_image_for_prompt(word_translation: str, english_sentence: str, account_id: str, api_token: str) -> str | None:
    """Constructs a prompt and generates an image using Cloudflare AI (Flux Schnell) via curl, returning base64 data."""
    # Construct the prompt using the provided word and sentence
    prompt = f"""
                Create a vibrant, flashcard illustration for the word '{word_translation}'.
                SCENE DETAILS:
                - Illustrate this example sentence: '{english_sentence}'
                - Create a clear, engaging scene that instantly communicates the word's meaning
                - Include characters demonstrating the word through their actions/interactions
                - Maintain a clean, uncluttered background to help with focus and memory retention

                LEARNING EFFECTIVENESS:
                - Position the key concept centrally with strong visual hierarchy
                - Include 1-2 distinctive visual elements that serve as memory anchors
                - Use color psychology to enhance emotional connection
                - Create a visual that works effectively at flashcard size
            """

    # Update the API endpoint back to Flux Schnell
    api_endpoint = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    # The payload only requires the prompt, defaults for other params are used
    data = json.dumps({"prompt": prompt})

    try:
        # Use subprocess.run to execute curl
        # Set timeout to avoid hanging indefinitely (e.g., 60 seconds)
        command = [
            "curl", "-s", "-X", "POST", api_endpoint,
            "-H", f"Authorization: {headers['Authorization']}",
            "-H", f"Content-Type: {headers['Content-Type']}",
            "-d", data
        ]
        process = subprocess.run(
            command, # Use the constructed command list
            capture_output=True,
            text=True, # Use text=True as the response is JSON
            check=True, # Raise CalledProcessError on non-zero exit code
            timeout=60 
        )

        # Parse the JSON response from stdout
        response_json = json.loads(process.stdout)
        
        # Check if image data is present in the expected format
        if "result" in response_json and "image" in response_json["result"]:
             # Cloudflare wraps the result in a "result" object
             # The image data is already base64 encoded by the API
            return response_json["result"]["image"]
        else:
            # Log the unexpected format
            print(f"  Error: Unexpected JSON response format from Cloudflare AI for word '{word_translation}'. Response: {response_json}")
            return None

    except subprocess.CalledProcessError as e:
        print(f"  Error calling Cloudflare AI (curl failed): {e}")
        # Decode stderr if possible
        stderr_output = e.stderr # Already text due to text=True
        print(f"  Stderr: {stderr_output}")
        return None
    except subprocess.TimeoutExpired:
        # Modify the error message to show the word being processed
        print(f"  Error: Cloudflare AI request timed out for word: '{word_translation}'")
        return None
    # Reinstate JSONDecodeError handling
    except json.JSONDecodeError as e:
         print(f"  Error decoding JSON response from Cloudflare AI: {e}")
         # Ensure process.stdout exists and is a string before printing
         raw_response = process.stdout if hasattr(process, 'stdout') and isinstance(process.stdout, str) else "N/A"
         print(f"  Raw Response: {raw_response}")
         return None
    except Exception as e:
        print(f"  An unexpected error occurred during image generation: {e}")
        return None 