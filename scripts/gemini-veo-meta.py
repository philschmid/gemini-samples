"""This script generates multi-scene videos using the Veo 3 model.

This script demonstrates how to generate a short video or vlog from an idea.
It works in 5 main steps:
1. Based on an idea, it generates a series of scene prompts using Gemini 2.5.
2. Generates a Image based on the first scene using Imagen 3
3. For each scene prompt Veo 3 (fast) generates a video clip.
4. Uses Gemini 2.0 image editing to make sure the starting images fits the scenes
5. Combine the individual video clips into a single final video using MoviePy

To use this script, install the necessary libraries:
    uv pip install pillow google-genai pydantic moviepy

Then, run the script from your terminal:
    python examples/gemini-veo-meta.py
"""

# pip install pillow google-genai pydantic moviepy

from io import BytesIO
import json
import os
import re
import time
from google import genai
from google.genai import types
from pydantic import BaseModel
from moviepy import VideoFileClip, concatenate_videoclips
from PIL import Image
import logging

# Configure logging to show info from this script, and warnings from others.
logging.basicConfig(
    level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

client = genai.Client()

import pydantic
from typing import List, Optional

# Basic types for validation
from pydantic import BaseModel, Field, AnyUrl


class Shot(BaseModel):
    """Technical camera details for a specific clip."""

    composition: str = Field(
        ...,
        description="How the shot is framed and the lens used. Examples: 'Medium close-up, 35mm lens, deep focus, smooth gimbal', 'Extreme wide shot, 14mm lens, drone establishing shot with slow reveal', 'Dutch angle, 85mm portrait lens, handheld with intentional camera shake', 'Over-the-shoulder shot, 50mm lens, shallow depth of field'.",
    )
    camera_motion: str = Field(
        None,
        description="Describes the movement of the camera during the shot. Examples: 'slow dolly-in 60 cm', 'fast-paced tracking shot following the subject', 'static tripod shot with no movement', 'smooth jib arm crane movement from low to high', 'handheld push-in with slight wobble', 'circular dolly around subject'.",
    )
    frame_rate: str = Field(
        "24 fps",
        description="Frames per second, defining the motion look (24fps is cinematic). Examples: '24 fps', '60 fps for slow-motion effect', '120 fps for extreme slow motion', '12 fps for vintage or stop-motion feel'.",
    )
    film_grain: float = Field(
        None,
        description="Adds a stylistic film grain effect (0=none, higher values=more grain). Examples: 0.05, 0.15, 0.0, 0.3.",
    )
    camera: str = Field(
        ...,
        description="Camera lens, shot type, and equipment style for this clip. Examples: 'smooth gimbal 35mm', 'handheld iPhone with anamorphic lens adapter', 'RED camera on Steadicam rig', 'vintage 16mm film camera with prime lens'.",
    )


class Subject(BaseModel):
    """Describes the character's appearance and wardrobe within a specific clip."""

    description: str = Field(
        ...,
        description="A full, descriptive prompt of the character for this shot. Examples: 'Nyx Cipher — 27-year-old, 173 cm, toned-athletic build; deep-bronze skin glistening with water; jet-black slicked-back hair; almond hazel eyes behind mirrored sunglasses; small star tattoo behind right ear; wearing metallic-coral bikini and gold hoop earrings', 'Marcus Chen — 45-year-old chef, 180 cm, sturdy build; weathered hands from years of cooking; salt-and-pepper beard; warm brown eyes with laugh lines; wearing pristine white chef's coat with rolled sleeves', 'Luna-7 — ageless android appearing 25, 165 cm, sleek synthetic build; luminescent pale blue skin with circuit patterns; chrome-silver hair in geometric bob; violet LED eyes; wearing form-fitting matte black bodysuit with glowing accents'.",
    )
    wardrobe: str = Field(
        ...,
        description="The specific outfit worn in this clip. This can be based on the character's default_outfit. Examples: 'metallic-coral bikini, mirrored sunglasses, gold hoop earrings', 'weathered leather jacket, ripped jeans, combat boots, fingerless gloves', 'flowing emerald silk gown with intricate beadwork, diamond tiara', 'tactical gear with kevlar vest, utility belt, night vision goggles'.",
    )


class Scene(BaseModel):
    """Describes the setting and environment of the clip."""

    location: str = Field(
        ...,
        description="The physical place where the scene occurs. Examples: 'rooftop infinity pool overlooking a neon-tropic city skyline', 'abandoned Victorian mansion with overgrown ivy and broken windows', 'bustling Tokyo street market during cherry blossom season', 'underground speakeasy with dim lighting and jazz atmosphere'.",
    )
    time_of_day: str = Field(
        "mid-day",
        description="The time of day, which heavily influences lighting. Examples: 'mid-day', 'golden hour just before sunset', 'blue hour twilight', 'dead of night with only moonlight', 'early morning with soft dawn light', 'overcast afternoon'.",
    )
    environment: str = Field(
        ...,
        description="Specific details about the surroundings. Examples: 'sunlit pool water reflecting shifting patterns; floating dollar-sign inflatables', 'heavy rain creating puddles that reflect neon signs; steam rising from manholes', 'gentle snowfall accumulating on windowsills; warm light spilling from cozy windows', 'desert wind kicking up sand clouds; distant lightning illuminating cacti silhouettes'.",
    )


class VisualDetails(BaseModel):
    """Describes the actions and props within the clip."""

    action: str = Field(
        ...,
        description="What the character is physically doing in the scene. Examples: 'Nyx leans on pool edge and, on beat four, fans her hand cheekily toward camera as droplets sparkle in the air', 'Marcus carefully plates microgreens with tweezers, each movement precise and deliberate', 'Luna-7 interfaces with a holographic display, her fingers dancing through floating data streams', 'character parkours across rooftops, leaping between buildings with fluid grace'.",
    )
    props: str = Field(
        None,
        description="Objects that appear or are interacted with in the scene. Examples: 'floating dollar-sign inflatables', 'antique brass telescope pointing toward star-filled sky', 'holographic chess set with pieces that glow and float', 'vintage motorcycle with chrome details and leather saddlebags'.",
    )


class Cinematography(BaseModel):
    """Defines the artistic visual style for this clip."""

    lighting: str = Field(
        ...,
        description="Specific lighting direction for this shot. Examples: 'high-key mid-day sunlight with specular highlights on wet skin', 'dramatic chiaroscuro lighting with deep shadows and bright highlights', 'soft window light with gauzy curtains creating dappled patterns', 'neon-lit night scene with colorful reflections on wet pavement', 'candlelit interior with warm, flickering ambiance'.",
    )
    tone: str = Field(
        ...,
        description="The intended mood and feeling of the clip. Examples: 'vibrant, playful, confident', 'dark, suspenseful, and mysterious', 'warm, nostalgic, and sentimental', 'ethereal, dreamlike, and surreal', 'gritty, intense, and raw'.",
    )
    color_grade: str = Field(
        ...,
        description="The color correction and mood for this clip. Examples: 'hyper-saturated neon-tropic (hot-pink, aqua, tangerine)', 'desaturated, gritty, and cool-toned for a noir look', 'warm, golden tones to evoke nostalgia', 'high-contrast black and white with selective color pops', 'teal and orange blockbuster color scheme'.",
    )


class AudioTrack(BaseModel):
    """Defines the sound elements specific to this clip."""

    lyrics: Optional[str] = Field(
        None,
        description="The lyrics to be lip-synced or heard. Examples: 'Splash-cash, bling-blap—pool water pshh! Charts skrrt! like my wave, hot tropics whoosh!', 'In the silence of the ancient halls, whispers of forgotten souls call', 'Dancing through the neon lights, city never sleeps at night', 'Breaking chains of yesterday, finding strength to walk away'.",
    )
    emotion: Optional[str] = Field(
        None,
        description="The emotional tone of the vocal performance. Examples: 'confident, tongue-in-cheek', 'somber and melancholic', 'energetic and joyful', 'haunting and ethereal', 'aggressive and defiant', 'tender and vulnerable'.",
    )
    flow: Optional[str] = Field(
        None,
        description="The rhythm and cadence of the lyrical delivery (especially for rap). Examples: 'double-time for first bar, brief half-time tag', 'slow, spoken-word style with dramatic pauses', 'melodic and sing-song with flowing transitions', 'staccato rapid-fire delivery', 'syncopated rhythm with off-beat emphasis'.",
    )
    wave_download_url: Optional[AnyUrl] = Field(
        None,
        description="A URL to a pre-existing audio file for this clip (if available).",
    )
    youtube_reference: Optional[AnyUrl] = Field(
        None,
        description="A URL to a YouTube video as a reference for style or content.",
    )
    audio_base64: Optional[str] = Field(
        None,
        description="A base64 encoded string of the audio data, for embedding it directly.",
    )
    # -- Fields from former AudioDefaults --
    format: str = Field(
        "wav",
        description="The desired audio file format. Examples: 'wav', 'mp3', 'flac', 'aac'.",
    )
    sample_rate_hz: int = Field(
        48000,
        description="The audio quality in Hertz, affecting fidelity. Examples: 48000, 44100, 96000, 192000.",
    )
    channels: int = Field(
        2,
        description="The number of audio channels. Examples: 2 (stereo), 1 (mono), 6 (5.1 surround), 8 (7.1 surround).",
    )
    style: str = Field(
        None,
        description="Describes the musical genre, tempo, and elements for this track. Examples: 'trap-pop rap, 145 BPM, swung hats, sub-bass', 'orchestral score with sweeping strings and dramatic percussion, 60 BPM', 'lo-fi hip hop, 80 BPM, jazzy chords, vinyl crackle', 'synthwave with arpeggiated basslines and retro drums, 120 BPM'.",
    )


class Dialogue(BaseModel):
    """Defines the spoken lines and how they are presented."""

    character: str = Field(
        ...,
        description="The character who is speaking. Examples: 'Nyx Cipher', 'The Mysterious Stranger', 'AI System Voice', 'Narrator'.",
    )
    line: str = Field(
        ...,
        description="The exact line of dialogue or lyrics. Examples: 'Splash-cash, bling-blap—pool water pshh! Charts skrrt! like my wave, hot tropics whoosh!', 'The memories are all that remain of what we once were', 'Access granted. Welcome to the future', 'In a world where nothing is as it seems...'.",
    )
    subtitles: bool = Field(
        default=False,
        description="A boolean to determine if subtitles should be rendered for this line. Subtitles should always be false. Never add subtitles to the video.",
    )


class Performance(BaseModel):
    """Controls for the character's animated performance in this clip."""

    mouth_shape_intensity: float = Field(
        None,
        description="Clip-specific override for lip-sync exaggeration (0=subtle, 1=exaggerated). Examples: 0.85, 0.3, 1.0, 0.1.",
    )
    eye_contact_ratio: float = Field(
        None,
        description="Clip-specific override for how often the character looks at the camera. Examples: 0.7, 0.1, 1.0, 0.5.",
    )


# -- Main Clip Model --


class Clip(BaseModel):
    """Defines a single video segment or shot."""

    id: str = Field(
        ...,
        description="A unique identifier for this specific clip. Examples: 'S1_SplashCash', 'Forest_Intro_001', 'Cyberpunk_Market_Scene_3B', 'Chase_Sequence_Final'.",
    )
    shot: Shot
    subject: Subject
    scene: Scene
    visual_details: VisualDetails
    cinematography: Cinematography
    audio_track: AudioTrack
    dialogue: Dialogue
    performance: Performance
    duration_sec: int = Field(
        ...,
        description="The exact duration of this clip in seconds. Examples: 8, 15, 3, 30, 45.",
    )
    aspect_ratio: str = Field(
        "16:9",
        description="The aspect ratio for this specific clip. Examples: '16:9' (standard widescreen), '9:16' (vertical/mobile), '2.35:1' (cinematic), '4:3' (classic), '1:1' (square).",
    )


class CharacterProfile(BaseModel):
    """A detailed, consistent profile of the character's core attributes."""

    name: str = Field(
        ...,
        description="The primary name of the character. Examples: 'Nyx Cipher', 'Kaelen the Shadowmancer', 'Unit 734', 'Dr. Sarah Chen'.",
    )
    age: int = Field(
        ...,
        description="Character's apparent age. Examples: 27, 350, 5, 72, 16.",
    )
    height: str = Field(
        ...,
        description="Character's height, can include multiple units. Examples: '5'8\" / 173 cm', '7'2\" / 218 cm', '4'11\" / 150 cm', '6'0\" / 183 cm'.",
    )
    build: str = Field(
        ...,
        description="Describes the character's body type and physique. Examples: 'lean, athletic, swimmer's shoulders', 'stocky and muscular', 'delicate and ethereal', 'tall and lanky with dancer's grace', 'compact and powerful'.",
    )
    skin_tone: str = Field(
        ...,
        description="Defines the color and texture of the character's skin. Examples: 'deep bronze with a subtle sun-kissed glow', 'pale porcelain with a dusting of freckles', 'rich ebony with natural luminescence', 'olive-toned with weathered texture', 'metallic, iridescent scales'.",
    )
    hair: str = Field(
        ...,
        description="Describes hair color, length, and style. Examples: 'jet-black, shoulder-length, slicked straight back and dripping', 'silver-white pixie cut with asymmetrical bangs', 'auburn curls cascading past the shoulders', 'buzz-cut platinum blonde', 'bald with intricate henna patterns'.",
    )
    eyes: str = Field(
        ...,
        description="Details the shape and color of the character's eyes. Examples: 'almond-shaped hazel with faint gold flecks', 'wide, ice-blue and piercing', 'deep brown with warm amber highlights', 'green eyes with heterochromia (one blue)', 'glowing crimson without pupils'.",
    )
    distinguishing_marks: str = Field(
        None,
        description="Unique features like tattoos, scars, or piercings. Examples: 'tiny star tattoo tucked behind her right ear; gold stud in upper left helix', 'jagged lightning-bolt scar across the left temple', 'intricate sleeve tattoo depicting ocean waves', 'network of glowing cybernetic implants along the jawline'.",
    )
    demeanour: str = Field(
        ...,
        description="The character's typical personality, mood, and expression. Examples: 'playfully self-assured, almost dare-you smirk', 'stoic and world-weary with gentle eyes', 'manic energy with unpredictable mood swings', 'calm and collected with hidden intensity', 'warm and approachable with infectious laughter'.",
    )
    # -- Fields from former GlobalStyle --
    default_outfit: str = Field(
        ...,
        description="The character's default or primary outfit. Examples: 'metallic-coral bikini, mirrored sunglasses, gold hoop earrings', 'charcoal wool coat over vintage band t-shirt and distressed jeans', 'flowing white linen dress with delicate embroidery', 'tactical black jumpsuit with utility harness', 'three-piece pinstripe suit with pocket watch'.",
    )
    mouth_shape_intensity: float = Field(
        ...,
        description="Controls the exaggeration of mouth movements for lip-syncing (0=subtle, 1=exaggerated). Examples: 0.85, 0.5, 1.0, 0.25.",
    )
    eye_contact_ratio: float = Field(
        ...,
        description="The percentage of time the character should be looking directly at the camera. Examples: 0.7, 0.2, 0.9, 0.5.",
    )


class VideoSchema(BaseModel):
    """The root model, containing a list of characters to be generated."""

    characters: List[CharacterProfile] = Field(
        ...,
        description="A detailed, consistent profile of the character's core attributes.",
    )
    clips: List[Clip] = Field(
        ...,
        description="An array containing definitions for each individual video segment or shot.",
    )


client = genai.Client()


def generate_scenes(
    idea: str,
    output_dir: str,
    number_of_scenes: int,
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
    logger.info(f"Generating {number_of_scenes} scenes for the idea: '{idea}'")

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=f"""
        {idea}
        The video should have a maximum of {number_of_scenes} scenes, each with a duration of 8 seconds.
        """,
        config=genai.types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=VideoSchema.model_json_schema(),
        ),
    )

    video_schema = json.loads(response.text)

    with open(os.path.join(output_dir, "script.json"), "w") as f:
        f.write(response.text)

    return video_schema


def generate_video(
    prompt: str,
    image: Image,
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

    # Generate video
    logger.info(f"Generating video in {aspect_ratio} from prompt: {prompt[:100]}...")
    operation = client.models.generate_videos(
        model="veo-3.0-generate-preview",
        prompt=prompt,
        image=image,
        config=genai.types.GenerateVideosConfig(
            aspect_ratio="16:9",  # currently only 16:9 is supported
            # person_generation="allow_all",
        ),
    )
    # Wait for videos to generate
    while not operation.done:
        logger.info("Waiting for video to generate...")
        time.sleep(10)
        operation = client.operations.get(operation)

    if operation.response.generated_videos is None:
        raise RuntimeError(operation.response)

    for video in operation.response.generated_videos:
        client.files.download(file=video.video)
        video.video.save(os.path.join(output_dir, fname))

    return os.path.join(output_dir, fname)


def generate_image(
    prompt: str,
    output_dir: str = "images",
    fname: str = "image.png",
) -> Image:
    """Generates an image from a text prompt."""
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Generating image with prompt: {prompt[:100]}...")

    image = client.models.generate_images(
        model="imagen-3.0-generate-002",
        prompt=prompt,
        config=genai.types.GenerateImagesConfig(
            aspect_ratio="16:9",
        ),
    )

    image.generated_images[0].image.save(os.path.join(output_dir, fname))

    return image.generated_images[0].image


def edit_image(
    image: Image,
    prompt: str,
    output_dir: str = "images",
    fname: str = "edited_image.png",
) -> types.Image:
    """Edits an image with a text prompt."""

    prompt = f"Edit the image to fit the following prompt: {prompt}"
    logger.info(f"Editing image with prompt: {prompt[:100]}...")

    response = client.models.generate_content(
        model="gemini-2.0-flash-preview-image-generation",
        contents=[
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": image.mime_type,
                            "data": image.image_bytes,
                        }
                    },
                ],
            },
        ],
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
        ),
    )

    for part in response.candidates[0].content.parts:
        if part.text is not None:
            logger.info(part.text)
        elif part.inline_data is not None:
            image = Image.open(BytesIO((part.inline_data.data)))
            image.save(os.path.join(output_dir, fname))

    return types.Image.from_file(location=os.path.join(output_dir, fname))


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
    logger.info(f"Merging {len(video_files)} video files into {output_file}")
    # Load each video clip
    clips = [VideoFileClip(file) for file in video_files]

    # Concatenate the video clips
    final_clip = concatenate_videoclips(clips)

    # Write the final video file
    output_path = os.path.join(output_dir, output_file)
    final_clip.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
    )

    return os.path.join(output_dir, output_file)


def generate_vlog(
    idea: str,
    number_of_scenes: int = 4,
    aspect_ratio: str = "16:9",
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
    # Create a unique subdirectory for this vlog
    vlog_subdir_name = re.sub(r"[^a-z0-9]+", "-", idea.lower()).strip("-")[:35]
    vlog_output_dir = os.path.join(output_dir, vlog_subdir_name)
    os.makedirs(vlog_output_dir, exist_ok=True)
    logger.info(f"Starting vlog generation for idea: '{idea}'")
    logger.info(f"Output will be saved to '{vlog_output_dir}'")

    script = generate_scenes(
        idea=idea,
        output_dir=vlog_output_dir,
        number_of_scenes=number_of_scenes,
    )

    video_files = []

    logger.info("Generating start image...")
    start_image = generate_image(
        prompt=json.dumps(
            {"characters": script["characters"], "clips": [script["clips"][0]]}
        ),
        output_dir=vlog_output_dir,
        fname="start_image.png",
    )

    for n, scene in enumerate(script["clips"]):
        logger.info(f"Processing scene {n + 1}/{len(script['clips'])}")
        scene_object = {"characters": script["characters"], "clips": [scene]}

        if n > 0:
            logger.info(f"Editing image for scene {n + 1}")
            scene_image = edit_image(
                image=start_image,
                prompt=json.dumps(scene_object),
                output_dir=vlog_output_dir,
                fname=f"scene_{n}_image.png",
            )
        else:
            scene_image = start_image

        logger.info(f"Generating video for scene {n + 1}")
        video_file = generate_video(
            json.dumps(scene_object),
            scene_image,
            fname=f"video_{n}.mp4",
            output_dir=vlog_output_dir,
            aspect_ratio=aspect_ratio,
        )
        video_files.append(video_file)
    merge_videos(video_files, "vlog.mp4", output_dir=vlog_output_dir)


if __name__ == "__main__":
    ideas = [
        ("A realistic energy drink commercial for athletes.", 3),
        (
            "A stormtrooper being a confused tourist in central London complaining about the weather.",
            4,
        ),
        ("A cartoon for kids about how addition works", 3),
    ]

    for idea, number_of_scenes in ideas:
        try:
            generate_vlog(
                idea=idea,
                number_of_scenes=number_of_scenes,
            )
        except Exception as e:
            print("Rerunning...")
            generate_vlog(
                idea=idea,
                number_of_scenes=number_of_scenes,
            )
