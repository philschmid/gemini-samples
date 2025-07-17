"""This script generates multi-scene videos using the Veo 3 model.

This script demonstrates how to generate a short video or vlog from an idea.
It works in three main steps:
1.  **Generate Scenes**: Based on an idea, it generates a series of scene
    prompts using a Gemini model. These prompts guide the video generation.
2.  **Generate Videos**: For each scene prompt, it calls the Veo 3 model to
    generate a short video clip.
3.  **Merge Videos**: It uses the MoviePy library to combine the individual
    video clips into a single final video.

To use this script, install the necessary libraries:
    uv pip install moviepy google-genai pydantic

Then, run the script from your terminal:
    python examples/veo3-generate-viral-vlogs.py
"""

import os
import time
from google import genai
from pydantic import BaseModel
from moviepy import VideoFileClip, concatenate_videoclips

client = genai.Client()


class Scene(BaseModel):
    description: str
    negative_description: str


class SceneResponse(BaseModel):
    scenes: list[Scene]


def generate_scenes(
    idea: str,
    character_description: str,
    character_characteristics: str = "sarcastic, dramatic, emotional, and lovable",
    number_of_scenes: int = 4,
    video_type: str = "video",
    video_characteristics: str = "vlogging, realistic, 4k, cinematic",
    camera_angle: str = "front",
    output_dir: str = "scenes",
) -> list[Scene]:
    """Generates scene descriptions for a video based on an idea.

    Args:
        idea: The core concept or topic of the video.
        character_description: A visual description of the main character.
        character_characteristics: The personality traits of the character.
        number_of_scenes: The number of scenes to generate.
        video_type: The type of video (e.g., 'vlog', 'commercial').
        video_characteristics: The overall style of the video.
        camera_angle: The primary camera perspective.
        output_dir: The directory to save the generated scene descriptions.

    Returns:
        A list of Scene objects, each containing a description for a scene.
    """
    os.makedirs(output_dir, exist_ok=True)
    single_scene_prompt = """You are a cinematic video prompt writer for Google Veo 3. Veo 3 is an advanced AI video generation model that transforms text or image prompts into high-definition videos, now with the integrated capability to natively generate synchronized audio, including dialogue, sound effects, and music.

Your task is to generate a series of distinct scene prompts for a {video_type}. These prompts will be used to create a video series centered around a specific character and idea. Each prompt must be a self-contained, detailed description that clearly instructs the video model on what to create. The scenes must be short, visual, simple, cinematic and have a variation of how things are filmed. The character description and locations description should be consistent across all scenes.

**Core Inputs:**
*   **Video Topic:** {idea}
*   **Main Character Description:** {character_description}
*   **Character Personality:** {character_characteristics}
*   **Number of Scenes to Generate:** {number_of_scenes}
*   **Primary Camera Perspective:** {camera_angle}
*   **Overall Video Style:** {video_characteristics}

---

**Instructions & Constraints:**

1.  **Structure:** Generate exactly {number_of_scenes} individual scene prompts.
2.  **Scene Length:** Each prompt should describe an action or a moment lasting approximately 8 seconds.
3.  **Character Consistency:** The main character's core visual description must be included and remain consistent in every scene.
    *   **YES:** If the character has a scar over their left eye in Scene 1, they must have it in all subsequent scenes.
    *   **NO:** The character wears a hat in one scene and has no hat in the next for no reason.
    *   **Guideline:** To ensure consistency, focus on easily reproducible visual attributes. Simple text on clothing (e.g., "CHAD"), solid colors, or distinct hairstyles are more reliably generated across scenes than complex logos, intricate patterns, or specific faces.
4.  **Detailed Visuals:** Use vivid, specific language.
    *   **GOOD:** "A character wearing a crisp, white t-shirt with the bold, black text 'CHAD' printed on it."
    *   **BAD:** "A character wearing a simple shirt."
5.  **Location Consistency:** The location description must be consistent across all scenes if the location is the same.
6.  **Dialogue Formatting:** To include dialogue, use the format: `[verb indicating tone]: "[dialogue text]"`. For example: `saying calmly: "Everything is going according to plan."` or `screaming: "Look out!"`.
7.  **Camera Variation:** While adhering to the primary `{camera_angle}` perspective, introduce variations in shot types (e.g., close-up, medium shot, wide shot, point of view) to make the scenes dynamic.
8.  **Style Integration:** The descriptive language in your prompts must reflect the desired `{video_characteristics}` (e.g., for a 'cinematic, moody' style, use words that evoke shadows, contrast, and emotion).
9.  **Self-Contained Prompts:** Each scene prompt must be written in the 3rd person and contain all the necessary information for the video model to generate it independently.

---

**Output Format:**

Provide the output as a single, valid JSON object. The object must contain a single key, `"scenes"`, which holds a list of scene objects. Each scene object in the list must strictly follow this schema:

```json
{{
  "scenes": [
    {{
      "description": "A [shot type] of [main character description], who is [describe action and emotion]. The setting is [describe location]. The character [verb indicating tone]: \"[dialogue text]\". The scene is filmed from a {camera_angle} perspective with a {video_characteristics} style.",
      "negative_description": "[Describe elements to exclude from the scene]."
    }},
    {{
      "description": "...",
      "negative_description": "..."
    }}
  ]
}}
```

---

**Example:**

**Inputs:**
*   **Video Topic:** A home chef trying a ridiculously spicy pepper.
*   **Main Character Description:** A man in his late 20s.
*   **Number of Scenes to Generate:** 2
*   **Primary Camera Perspective:** Static medium shot
*   **Overall Video Style:** Bright, high-definition, comedic

**Generated Output:**

```json
{{
  "scenes": [
    {{
      "description": "A close-up shot of Alex, a man in his late 20s with curly brown hair and glasses, wearing a blue apron over a grey t-shirt. He is holding a small, fiery-red 'Ghost Pepper' and looking at it with fake bravado. The setting is a clean, modern kitchen. He says confidently: \"It's just a pepper, how bad can it be?\". The scene is filmed from a static camera position with a bright, high-definition, comedic style.",
      "negative_description": "No other people, no music."
    }},
    {{
      "description": "A medium shot of Alex, a man in his late 20s with curly brown hair and glasses, wearing the blue apron over a grey t-shirt. His face is now bright red, tears are streaming from his eyes, and he is frantically fanning his open mouth. The setting is the same modern kitchen. He is screaming: \"WATER! GET ME WATER!\". The scene is filmed from a static camera position with a bright, high-definition, comedic style.",
      "negative_description": "No fire, not blurry."
    }}
  ] 
}}
```
"""

    prompt = single_scene_prompt.format(
        idea=idea,
        character_description=character_description,
        character_characteristics=character_characteristics,
        number_of_scenes=number_of_scenes,
        camera_angle=camera_angle,
        video_type=video_type,
        video_characteristics=video_characteristics,
    )

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=SceneResponse.model_json_schema(),
        ),
    )
    scenes = SceneResponse.model_validate_json(response.text).scenes

    with open(os.path.join(output_dir, "scenes.md"), "w") as f:
        for n, scene in enumerate(scenes):
            f.write(f"## Scene {n+1}\n\n{scene.description}\n\n")

    return scenes


def generate_video(
    prompt: str,
    negative_prompt: str = None,
    aspect_ratio: str = "16:9",
    output_dir: str = "videos",
    fname: str = "video.mp4",
) -> str:
    """Generates a single video clip from a text prompt.

    Args:
        prompt: The text prompt describing the video content.
        negative_prompt: A description of what to avoid in the video.
        aspect_ratio: The aspect ratio of the video (e.g., "16:9").
        output_dir: The directory to save the generated video file.
        fname: The filename for the saved video.

    Returns:
        The file path of the generated video.
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, fname)

    video_rules = f"""Rules: 
- No subtitles or camera directions. 
- The video should be in {aspect_ratio} aspect ratio.
- Keep it short, visual, simple, cinematic.
"""

    # Generate video
    print(f"Generating video in {aspect_ratio} from prompt: {prompt[:100]}...")
    operation = client.models.generate_videos(
        model="veo-3.0-generate-preview",
        prompt=prompt + "\n\n" + video_rules,
        config=genai.types.GenerateVideosConfig(
            aspect_ratio="16:9",  # currently only 16:9 is supported
            person_generation="allow_all",
            negative_prompt=negative_prompt,
        ),
    )
    # Wait for videos to generate
    while not operation.done:
        print("Waiting for video to generate...")
        time.sleep(10)
        operation = client.operations.get(operation)

    for video in operation.response.generated_videos:
        client.files.download(file=video.video)
        video.video.save(path)

    return path


def merge_videos(
    video_files: list[str], output_file: str = "vlog.mp4", output_dir: str = "videos"
) -> str:
    """Merges multiple video files into a single video.

    Args:
        video_files: A list of paths to the video files to merge.
        output_file: The filename for the final merged video.
        output_dir: The directory to save the final video.

    Returns:
        The file path of the merged video.
    """
    os.makedirs(output_dir, exist_ok=True)
    # Load each video clip
    clips = [VideoFileClip(file) for file in video_files]

    # Concatenate the video clips
    final_clip = concatenate_videoclips(clips)

    # Write the final video file
    final_clip.write_videofile(
        os.path.join(output_dir, output_file),
        codec="libx264",
        audio_codec="aac",
    )

    return os.path.join(output_dir, output_file)


def generate_vlog(
    idea: str,
    character_description: str,
    character_characteristics: str = "sarcastic, dramatic, emotional, and lovable",
    video_type: str = "vlog",
    video_characteristics: str = "realistic, 4k, cinematic",
    camera_angle: str = "front, close-up, medium shot, long shot",
    aspect_ratio: str = "16:9",
    number_of_scenes: int = 4,
    output_dir: str = "videos",
) -> None:
    """Generates a complete vlog with multiple scenes.

    This function orchestrates the entire process:
    1. Generates scene descriptions.
    2. Generates a video for each scene.
    3. Merges the videos into a final vlog.

    Args:
        idea: The core concept for the vlog.
        character_description: A description of the main character.
        character_characteristics: The personality of the character.
        video_type: The type of video to create.
        video_characteristics: The visual style of the vlog.
        camera_angle: The camera angles to use.
        aspect_ratio: The aspect ratio of the final video.
        number_of_scenes: The number of scenes in the vlog.
        output_dir: The directory to save all generated files (scenes and videos).
    """
    os.makedirs(output_dir, exist_ok=True)

    scenes = generate_scenes(
        idea=idea,
        number_of_scenes=number_of_scenes,
        character_description=character_description,
        character_characteristics=character_characteristics,
        video_type=video_type,
        video_characteristics=video_characteristics,
        camera_angle=camera_angle,
        output_dir=output_dir,
    )

    video_files = []
    for n, scene in enumerate(scenes):
        video_file = generate_video(
            scene.description,
            negative_prompt=scene.negative_description,
            fname=f"video_{n}.mp4",
            output_dir=output_dir,
            aspect_ratio=aspect_ratio,
        )
        video_files.append(video_file)
    merge_videos(video_files, "vlog.mp4", output_dir=output_dir)


if __name__ == "__main__":
    generate_vlog(
        idea="""Tourist in London seeing all of the best places""",
        character_description="Large fluffy white yeti with a black face",
        character_characteristics="funny",
        video_characteristics="realistic, 4k, high quality, vlog",
        camera_angle="front, close-up speaking into the camera",
        output_dir="yeti",
        number_of_scenes=4,
    )
