import os
import re
from google import genai

client = genai.Client()


def generate_json_from_idea(idea: str) -> str:
    """Generates a detailed JSON prompt from a simple idea using a Gemini model."""

    # The prompt template includes the desired JSON schema structure.
    schema_template = """Convert the attached user idea into a detailed JSON object for generating an image. The output should only be the raw JSON object, without any markdown formatting like ```json ... ```.

Idea: "{idea}"

Schema:
{{
    "meta": {{
        "styleName": "...", // A unique, descriptive name for this specific image style or preset (e.g., "Ethereal Forest Magic", "Cyberpunk Noir Alley").
        "aspectRatio": "...", // The proportional relationship between the width and height of the image (e.g., "16:9", "1:1", "4:5", "21:9").
        "promptPrefix": "..." // Optional text to prepend to a generated prompt, like a file name, a version number, or a specific trigger word.
    }},
    "camera": {{
        "model": "...", // Describes the camera, lens, or artistic medium used (e.g., "DSLR", "iPhone 15 Pro", "8x10 view camera", "Watercolor on cold-press paper", "3D render in Blender").
        "focalLength": "...", // The lens's focal length, which affects the field of view and perspective distortion (e.g., "16mm wide-angle", "85mm portrait", "200mm telephoto", "Isometric perspective").
        "angle": "...", // The camera's angle relative to the main subject or scene (e.g., "eye-level", "high-angle", "dutch angle", "drone shot", "worm's-eye view").
        "type": "..." // The genre or type of photography or art style (e.g., "macro photography", "landscape", "fantasy illustration", "architectural rendering", "abstract art").
    }},
    "subject": {{
        "primary": "...", // The main focal point or subject of the image (e.g., "a majestic mountain range", "a lone wolf", "an ancient wizard", "a futuristic cityscape", "an abstract shape").
        "emotion": "...", // The dominant emotion or mood conveyed by the subject or the overall scene (e.g., "serene and peaceful", "joyful", "melancholy", "menacing", "awe-inspiring").
        "pose": "...", // The posture, action, or arrangement of the subject(s) (e.g., "running towards the camera", "sitting in quiet contemplation", "a winding river", "a chaotic explosion").
        "gaze": "..." // The direction of the subject's gaze or the directional focus of the composition (e.g., "looking off-camera", "breaking the fourth wall", "facing away from the viewer", "pointing towards the horizon").
    }},
    "character": {{
        "appearance": "...", // Detailed physical description of a character or key object (e.g., "weathered face with a long white beard", "sleek, chrome-plated robot", "moss-covered ancient tree").
        "wardrobe": "...", // Clothing, armor, or any form of covering on the subject (e.g., "ornate golden armor", "tattered rags", "a vibrant kimono", "a car's glossy paint job").
        "accessories": "..." // Additional items worn by or associated with the subject (e.g., "a magical amulet", "cybernetic implants", "a pair of glasses", "a sword and shield").
    }},
    "composition": {{
        "theory": "...", // The compositional rules or theories applied (e.g., "rule of thirds", "golden ratio", "leading lines", "symmetrical balance", "negative space").
        "visualHierarchy": "..." // Describes the order in which the viewer's eye is drawn to different elements in the scene, from most to least prominent.
    }},
    "setting": {{
        "environment": "...", // The general environment or location of the scene (e.g., "a mystical forest", "a bustling cyberpunk city", "a tranquil beach at sunset", "a minimalist white room", "the surface of Mars").
        "architecture": "...", // Describes any buildings, ruins, or significant natural structures (e.g., "gothic cathedrals", "brutalist architecture", "alien monoliths", "towering rock formations").
        "furniture": "..." // Key objects, props, or furniture within the setting that add context or detail (e.g., "a single throne", "scattered futuristic debris", "a rustic wooden fence").
    }},
    "lighting": {{
        "source": "...", // The primary source of light in the scene (e.g., "dramatic moonlight", "soft window light", "flickering candlelight", "neon signs", "magical glow").
        "direction": "...", // The direction from which the light originates (e.g., "backlighting", "rim lighting", "top-down light", "light from below").
        "quality": "..." // The quality and characteristics of the light and shadows (e.g., "soft and diffused", "hard and high-contrast", "dappled", "volumetric light rays", "caustic reflections").
    }},
    "style": {{
        "artDirection": "...", // The overarching artistic style, movement, or influence (e.g., "impressionism", "art deco", "cyberpunk", "vaporwave", "ghibli-inspired", "cinematic").
        "mood": "..." // The overall mood, feeling, or atmosphere of the image (e.g., "ethereal and dreamy", "dystopian and gritty", "whimsical and cheerful", "epic and dramatic").
    }},
    "rendering": {{
        "engine": "...", // The rendering engine, technique, or medium used to create the final image (e.g., "Octane Render", "oil painting", "cross-hatching", "pixel art", "Unreal Engine 5").
        "fidelitySpec": "...", // Specific details about the image's texture and fidelity (e.g., "heavy film grain", "sharp digital focus", "visible brushstrokes", "chromatic aberration", "lens flare").
        "postProcessing": "..." // Any post-processing or finishing effects applied (e.g., "color grading with a teal and orange look", "vignette", "bloom and glare", "a vintage photo filter").
    }},
    "colorPalette": {{
        "primaryColors": [ // The most dominant colors that define the overall color scheme of the image.
            {{ "name": "...", "hex": "...", "percentage": "..." }},
            {{ "name": "...", "hex": "...", "percentage": "..." }}
        ],
        "accentColors": [ // Complementary or contrasting colors used for emphasis, detail, or highlights.
            {{ "name": "...", "hex": "...", "percentage": "..." }},
            {{ "name": "...", "hex": "...", "percentage": "..." }}
        ]
    }}
}}
"""
    prompt = schema_template.format(idea=idea)

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
    )

    return response.text


def generate_images(
    idea: str,
    prompt: str,
    aspectRatio: str = "1:1",  # "1:1", "3:4", "4:3", "9:16", and "16:9".
    output_dir: str = "images",
    num_images: int = 1,
):
    """Generates images using Imagen and saves them to the output directory."""
    print(f"Generating {num_images} images for {idea}")

    try:
        response = client.models.generate_images(
            model="imagen-4.0-generate-preview-06-06",
            prompt=prompt,
            config=genai.types.GenerateImagesConfig(
                number_of_images=num_images,
                aspect_ratio=aspectRatio,
            ),
        )

        for i, generated_image in enumerate(response.generated_images):
            clean_idea = (
                re.sub(r"[^a-zA-Z0-9\s]", "", idea[:30]).lower().replace(" ", "-")
            )
            image_path = os.path.join(output_dir, f"{clean_idea}-{i+1}.png")
            generated_image.image.save(image_path)
            with open(os.path.join(output_dir, f"{clean_idea}.json"), "w") as f:
                f.write(prompt)
            print(f"Saved image and prompt to {image_path}")

    except Exception as e:
        print(f"An error occurred during image generation: {e}")


def generate(
    idea: str,
    output_dir: str = "images",
    aspectRatio: str = "1:1",
    num_images: int = 2,
):
    """Orchestrates the process of generating JSON and then generating images."""
    os.makedirs(output_dir, exist_ok=True)

    prompt_data = generate_json_from_idea(idea)

    generate_images(
        idea=idea,
        prompt=prompt_data,
        aspectRatio="3:4",
        output_dir=output_dir,
        num_images=num_images,
    )


if __name__ == "__main__":
    ideas = [
        "A energy drink with water drops on it, ultra realistic, for a commercial.",
        "Graffiti with the text 'JSON Schema' on a brick wall.",
        "A LEGO knight fighting a huge, fire-breathing dragon on a castle wall.",
        "A stylish woman sipping coffee at a Parisian cafe, with the Eiffel Tower in the background. Shot in golden hour.",
        "An emotional, close-up portrait of an old fisherman.",
        "A vast, alien landscape on a distant planet with two suns, strange, towering rock formations, and bioluminescent plants. Epic sci-fi concept art.",
        "A whimsical illustration of a friendly fox reading a book in a cozy, cluttered library. The text 'The Midnight Reader' should be subtly integrated on a book spine.",
        "A magical man with sparkling pink hair and large from an anime.",
        "A cartoon robot waving happily, with a simple, bold outline and bright, flat colors. ",
        "A full-body character sheet of a realistic pirate captain, showing front, back, and side views.",
    ]

    for idea in ideas:
        generate(idea=idea)
