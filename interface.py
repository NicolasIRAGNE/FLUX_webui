import gradio as gr
import fal_client
import requests
import datetime
import os
import random
from PIL import Image

SAVE_PATH = datetime.datetime.now().strftime("%m-%Y")
# Create a folder to save the images
if not os.path.exists(SAVE_PATH):
    os.makedirs(SAVE_PATH)

# Define the function that will generate the image
def generate_image(prompt, aspect_ratio, image_input_url, image_prompt_strength, raw, seed):
    model = "fal-ai/flux-pro/v1.1-ultra"
    if image_input_url is not None:
        model = "fal-ai/flux-pro/v1.1-ultra/redux"
    arguments = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "num_images": 1,
        "enable_safety_checker": False,
        "safety_tolerance": "5",
        "raw": raw,
    }
    if image_input_url is not None:
        print(f"Using image {image_input_url}")
        arguments["image_url"] = image_input_url
        arguments["image_prompt_strength"] = image_prompt_strength
        # remove "aspect_ratio" from the arguments
        # arguments.pop("aspect_ratio")

    print(f"Submitting request to FAL with model {model} and arguments {arguments}")
    handler = fal_client.submit(
        model,
        arguments=arguments
    )
    result = handler.get()
    print("Got result")


    # Save and return the first image
    images = []
    for i, image in enumerate(result["images"]):
        url = image["url"]
        response = requests.get(url)
        file_path = os.path.join(SAVE_PATH, url.split('/')[-1])
        file_path = os.path.normpath(file_path)
        with open(file_path, "wb") as file:
            print(f"Saving image to {file_path}")
            file.write(response.content)
        # Save the last image as "last{i}.jpg for easy access"
        with open(f"last{str(i)}.jpg", "wb") as file:
            print(f"Saving image to last{str(i)}.jpg")
            file.write(response.content)
        images.append(file_path)
    return images


# REPLACE THIS WITH THE PATH TO YOUR PROMPTS FILE
prompt_file = "C:/Users/nicor/source/repos/golmon_radio_archives/prompts.md"

random_prompts = []
if prompt_file != "":
    # read a random line from the file that is not empty
    if os.path.exists(prompt_file):
        with open(prompt_file, "r", encoding="utf-8") as file:
            random_prompts = file.readlines()

# Load existing images to add to the gallery
previous_images = []
for file in os.listdir(SAVE_PATH):
    if file.endswith(".jpg") or file.endswith(".jpeg") or file.endswith(".png"):
        file_name = os.path.join(SAVE_PATH, file)
        file_name = file_name.replace("\\", "/")
        previous_images.append(file_name)

# sort images by date
previous_images.sort(key=os.path.getmtime, reverse=True)

# Gradio Interface
def gradio_interface(prompt, aspect_ratio, image_to_upload, img_prompt_strength, raw, seed, previous_images=previous_images):
    try:
        # Open the image file as PIL image
        # Then upload it to FAL
        if image_to_upload is not None:
            image_to_upload = image_to_upload[0][0]
            image_to_upload = os.path.normpath(image_to_upload)
            print(f"Opening image {image_to_upload}")
            with Image.open(image_to_upload) as img:
                print(f"Uploading image")
                uploaded_image_url = fal_client.upload_image(img, img.format)
                print(f"Uploaded image to {uploaded_image_url}")
        print(f"Generating image with prompt {prompt}, aspect ratio {aspect_ratio}" + (f" and image prompt strength {img_prompt_strength}" if image_to_upload is not None else ""))
        if seed == "":
            seed = -1
        else:
            seed = int(seed)
        generated_images = generate_image(prompt, aspect_ratio, uploaded_image_url if image_to_upload is not None else None, img_prompt_strength, raw, seed)
        print(f"Generated images: {generated_images}")
        normalized_generated_images = []
        for img in generated_images:
            normalized_generated_images.append(img.replace("\\", "/"))
        previous_images = normalized_generated_images + previous_images
        print(f"Previous images: {previous_images}")
        return previous_images
    except Exception as e:
        print(f"Error: {e}")
        return f"Error: {e}"

def change_lines():
    return gr.update(value=random.choice(random_prompts))

if __name__ == "__main__":

    print("Initializing interface...")
    with gr.Blocks() as interface:
        random_prompt_button = gr.Button("Random Prompt")
        # Define Gradio inputs and outputs
        prompt_input = gr.Textbox(label="Prompt", lines=5, placeholder="Enter your prompt here...")
        raw_checkbox = gr.Checkbox(label="Raw")
        random_prompt_button.click(change_lines, outputs=prompt_input)
        aspect_ratio_input = gr.Radio(
            choices=["21:9", "16:9", "4:3", "1:1", "3:4", "9:16", "9:21"],
            label="Aspect Ratio",
            value="4:3"
        )
        seed_input = gr.Textbox(label="Seed", placeholder="Enter a seed here...")
        input_gallery = gr.Gallery(label="Upload Image")
        img_prompt_strength_input = gr.Slider(label="Image Prompt Strength", minimum=0, maximum=1, step=0.1, value=0.4)
        output_gallery = gr.Gallery(label="Generated Images")
        # Define Gradio interface
        itf = gr.Interface(
            fn=gradio_interface,
            inputs=[prompt_input, aspect_ratio_input, input_gallery, img_prompt_strength_input, raw_checkbox, seed_input],
            outputs=output_gallery,
            title="Image Generator with FAL Client",
            description="Generate images based on a textual prompt using FAL Client."
        )

    interface.launch(server_name="0.0.0.0", server_port=3000)
    interface.launch()
