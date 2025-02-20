import gradio as gr
import fal_client
import requests
import datetime
import os
import random
from PIL import Image
from typing import List, Optional
import logging
import json

# Ensure output directory exists for logs
LOG_DIR = "output"
LOG_FILE = os.path.join(LOG_DIR, "prompts.log")
os.makedirs(LOG_DIR, exist_ok=True)

# Create log file if it doesn't exist
if not os.path.exists(LOG_FILE):
    open(LOG_FILE, 'a').close()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
SAVE_PREFIX = "output/"
SAVE_PATH = f"{SAVE_PREFIX}{datetime.datetime.now().strftime('%m-%Y')}"
SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png"}
PROMPT_FILE = "prompts.md"

# Create save directory if it doesn't exist, recursively
os.makedirs(SAVE_PATH, exist_ok=True)

def save_image(url: str, base_path: str, save_last: bool = False) -> str:
    """Save an image from a URL to disk."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        file_path = os.path.normpath(os.path.join(base_path, url.split('/')[-1]))
        with open(file_path, "wb") as file:
            logger.info(f"Saving image to {file_path}")
            file.write(response.content)
            
        if save_last:
            last_path = f"last0.jpg"
            with open(last_path, "wb") as file:
                file.write(response.content)
                
        return file_path.replace("\\", "/")
    except Exception as e:
        logger.error(f"Error saving image: {e}")
        raise

def generate_image(
    prompt: str,
    aspect_ratio: str,
    image_input_url: Optional[str] = None,
    image_prompt_strength: float = 0.4,
    raw: bool = False,
    seed: int = -1
) -> List[str]:
    """Generate images using the FAL API."""
    try:
        model = "fal-ai/flux-pro/v1.1-ultra/redux" if image_input_url else "fal-ai/flux-pro/v1.1-ultra"
        
        # Log the request details
        request_details = {
            "timestamp": datetime.datetime.now().isoformat(),
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "model": model,
            "raw_mode": raw,
            "seed": seed if seed != -1 else "random"
        }
        
        if image_input_url:
            request_details["image_prompt"] = True
            request_details["image_prompt_strength"] = image_prompt_strength
        
        logger.info(f"New generation request: {json.dumps(request_details, indent=2)}")
        
        arguments = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "num_images": 1,
            "enable_safety_checker": False,
            "safety_tolerance": "5",
            "raw": raw,
            "seed": seed if seed != -1 else None
        }
        
        if image_input_url:
            logger.info(f"Using image {image_input_url}")
            arguments["image_url"] = image_input_url
            arguments["image_prompt_strength"] = image_prompt_strength

        logger.info(f"Submitting request to FAL with model {model}")
        handler = fal_client.submit(model, arguments=arguments)
        result = handler.get()
        
        # Create output directory if it doesn't exist
        os.makedirs(SAVE_PATH, exist_ok=True)
        
        generated_paths = [save_image(image["url"], SAVE_PATH, save_last=True) 
                         for image in result["images"]]
        
        # Log the results
        logger.info(f"Successfully generated {len(generated_paths)} images: {generated_paths}")
        
        return generated_paths
                
    except Exception as e:
        logger.error(f"Error generating image: {e}")
        raise

def load_random_prompts() -> List[str]:
    """Load random prompts from file."""
    if not os.path.exists(PROMPT_FILE):
        return []
    try:
        with open(PROMPT_FILE, "r", encoding="utf-8") as file:
            return [line.strip() for line in file if line.strip()]
    except Exception as e:
        logger.error(f"Error loading prompts: {e}")
        return []

def load_previous_images() -> List[str]:
    """Load existing images from the save directory."""
    try:
        images = [
            os.path.join(SAVE_PATH, file).replace("\\", "/")
            for file in os.listdir(SAVE_PATH)
            if os.path.splitext(file)[1].lower() in SUPPORTED_FORMATS
        ]
        return sorted(images, key=os.path.getmtime, reverse=True)
    except Exception as e:
        logger.error(f"Error loading previous images: {e}")
        return []

def create_interface():
    """Create and configure the Gradio interface."""
    random_prompts = load_random_prompts()
    previous_images = load_previous_images()

    with gr.Blocks(css="footer {display: none !important}") as interface:
        gr.Markdown(
            """
            # 🎨 AI Image Generator
            Create stunning images using advanced AI models. Upload an image for variations or start from scratch!
            """
        )
        
        with gr.Row():
            with gr.Column(scale=2):
                prompt_input = gr.Textbox(
                    label="Prompt",
                    lines=3,
                    placeholder="Describe the image you want to create..."
                )
                
                with gr.Row():
                    random_prompt_btn = gr.Button("🎲 Random Prompt", variant="secondary")
                    generate_btn = gr.Button("🚀 Generate", variant="primary")
                
                with gr.Row():
                    with gr.Column():
                        aspect_ratio_input = gr.Radio(
                            choices=["21:9", "16:9", "4:3", "1:1", "3:4", "9:16", "9:21"],
                            label="Aspect Ratio",
                            value="4:3"
                        )
                        raw_checkbox = gr.Checkbox(label="Raw Mode")
                        seed_input = gr.Textbox(
                            label="Seed",
                            placeholder="Optional: Enter a seed for reproducible results"
                        )
            
            with gr.Column(scale=1):
                input_gallery = gr.Gallery(
                    label="Optional: Upload Image for Variations",
                    show_label=True,
                    height=200
                )
                img_prompt_strength_input = gr.Slider(
                    label="Image Influence",
                    minimum=0,
                    maximum=1,
                    step=0.1,
                    value=0.4
                )

        output_gallery = gr.Gallery(
            label="Generated Images",
            show_label=True,
            columns=4,
            height=400
        )

        def update_prompt():
            return gr.update(value=random.choice(random_prompts)) if random_prompts else gr.update()

        random_prompt_btn.click(
            update_prompt,
            outputs=prompt_input
        )

        generate_btn.click(
            fn=lambda *args: gradio_interface(*args, previous_images),
            inputs=[
                prompt_input,
                aspect_ratio_input,
                input_gallery,
                img_prompt_strength_input,
                raw_checkbox,
                seed_input
            ],
            outputs=output_gallery
        )

    return interface

def gradio_interface(
    prompt: str,
    aspect_ratio: str,
    image_to_upload: Optional[List] = None,
    img_prompt_strength: float = 0.4,
    raw: bool = False,
    seed: str = "",
    previous_images: List[str] = []
) -> List[str]:
    """Main interface function for image generation."""
    try:
        uploaded_image_url = None
        if image_to_upload:
            image_path = os.path.normpath(image_to_upload[0][0])
            logger.info(f"Processing uploaded image: {image_path}")
            with Image.open(image_path) as img:
                uploaded_image_url = fal_client.upload_image(img, img.format)

        seed_value = int(seed) if seed.strip() else -1
        generated_images = generate_image(
            prompt,
            aspect_ratio,
            uploaded_image_url,
            img_prompt_strength,
            raw,
            seed_value
        )
        
        return generated_images + previous_images
        
    except Exception as e:
        logger.error(f"Error in interface: {e}")
        raise gr.Error(f"Generation failed: {str(e)}")

if __name__ == "__main__":
    interface = create_interface()
    interface.launch(server_name="0.0.0.0", server_port=3000)
