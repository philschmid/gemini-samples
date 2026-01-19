# Generate Transparent Stickers with Nano Banana Pro and Gemini Interactions API

Generating images is easy. Generating images you can actually use with clean edges or transparent backgrounds is harder than it should be.

This guide shows how to generate ready to print stickers with Nano Banana Pro using the Gemini Interactions API. The trick: generate on a chromakey green background, then strip it with HSV color-space detection.

![Generated sticker with transparent background](../cat.png)

## The Stack

- **SDK:** `google-genai`
- **Model:** `gemini-3-pro-image-preview`
- **Dependencies:** `pillow`, `scipy`, `numpy`

```bash
pip install google-genai pillow scipy numpy
```

## Why This Works

Most "remove background" approaches use ML models. That's overkill when you control the generation.

Instead, we:
1. Prompt for a specific background color (#00FF00 chromakey green)
2. Detect that color in HSV space (catches all green shades, not just the exact pixel value)
3. Apply morphological cleanup (removes edge artifacts)

This is faster, deterministic, and doesn't require another model.

## The Prompt

```python
enhanced_prompt = f"""Create a sticker illustration of: {prompt}

CRITICAL CHROMAKEY REQUIREMENTS:
1. BACKGROUND: Solid, flat, uniform chromakey green color. Use EXACTLY hex color #00FF00. 
   The entire background must be this single pure green color with NO variation, NO gradients.

2. WHITE OUTLINE: The subject MUST have a clean white outline/border (2-3 pixels wide) 
   separating it from the green background.

3. NO GREEN ON SUBJECT: The subject itself should NOT contain any green colors.
   If the subject needs green (like leaves), use a distinctly different shade like teal.

4. SHARP EDGES: Crisp, well-defined edges - no soft or blurry boundaries.

5. CENTERED: Subject should be centered with padding around all sides.

This is for chromakey extraction - the green background will be removed programmatically."""
```

The white outline is the key insight here. It creates a buffer zone that prevents color bleeding between subject and background.

## The Generation

```python
from google import genai

client = genai.Client()

def generate_sticker(prompt: str, image_size: str = "2K") -> Image.Image:
    """Generate a sticker-style image with chromakey green background."""
    
    interaction = client.interactions.create(
        model="gemini-3-pro-image-preview",
        input=enhanced_prompt,  # The chromakey-optimized prompt from above
        generation_config={
            "image_config": {
                "aspect_ratio": "1:1",
                "image_size": image_size  # 2K gives cleaner edges than 4K
            }
        }
    )

    # Extract the generated image from the response
    for output in interaction.outputs:
        if output.type == "image":
            return decode_image(output.data)  # base64 -> PIL Image
    
    raise ValueError("No image was generated")
```

## The Green Screen Removal

GB makes detecting "all greens" difficult. Is `(50, 200, 50)` green? What about `(100, 180, 80)`?

HSV separates hue from saturation and brightness. Green sits around 120° on the hue wheel. Saturation and value handle light/dark variants.

```python
def remove_green_screen_hsv(
    image: Image.Image,
    hue_center: float = 120,    # Pure green = 120°
    hue_range: float = 50,      # Catch greens from ~70° to ~170°
    min_saturation: float = 15, # Include even faded greens
    min_value: float = 15       # Include even dark greens
) -> Image.Image:
    """Remove green screen using HSV color space."""
    
    data = np.array(image.convert('RGBA'))
    hsv = rgb_to_hsv_array(data[:, :, :3])
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]

    # Calculate hue distance (accounting for circular nature)
    hue_diff = np.abs(h - hue_center)
    hue_diff = np.minimum(hue_diff, 360 - hue_diff)

    # Pixel is green if: hue in range AND saturated AND not too dark
    green_mask = (
        (hue_diff < hue_range) &
        (s > min_saturation) &
        (v > min_value)
    )

    # Morphological cleanup: dilate to catch edge pixels, then erode
    from scipy import ndimage
    green_mask = ndimage.binary_dilation(green_mask, iterations=2)
    green_mask = ndimage.binary_erosion(green_mask, iterations=1)

    # Apply transparency
    alpha = data[:, :, 3].copy()
    alpha[green_mask] = 0
    data[:, :, 3] = alpha

    return Image.fromarray(data)
```

The `binary_dilation` → `binary_erosion` pattern is important. Dilation expands the mask to catch anti-aliased edge pixels. Erosion shrinks it back but keeps those expanded green areas.

## The Pipeline

One detection pass isn't enough. Some green-tinted pixels slip through.

The full pipeline runs three passes:

```python
def create_sticker(prompt: str, output_filename: str) -> Image.Image:
    """Complete workflow to create a transparent sticker."""
    
    # Step 1: Generate with chromakey prompt
    raw_image = generate_sticker(prompt)

    # Step 2: HSV-based removal (catches the color range)
    print("🔧 Pass 1: HSV-based green removal...")
    transparent = remove_green_screen_hsv(raw_image)

    # Step 3: Aggressive removal (catches remaining green tints)
    print("🔧 Pass 2: Aggressive green removal...")
    transparent = remove_green_screen_aggressive(
        transparent,
        green_threshold=1.1,  # Any pixel where G > R and G > B by 10%
        edge_pixels=2
    )

    # Step 4: Clean up semi-transparent edges
    print("✨ Cleaning up edges...")
    transparent = cleanup_edges(transparent, threshold=200)

    # Step 5: Save
    transparent.save(output_filename, 'PNG')
    return transparent
```

The aggressive removal pass catches pixels where green dominates but doesn't hit the HSV thresholds—like shadows with a green tint.

## Image-to-Sticker Mode

Got an existing image? Pass it as input and the model will convert it to sticker style:

```python
sticker = create_sticker(
    prompt="Convert this photo to a cute sticker style",
    output_filename="converted_sticker.png",
    input_images=["photo.jpg"]  # Your source image
)
```

The function builds a multimodal input:

```python
if input_images:
    input_content = []
    for img_path in input_images:
        input_content.append(load_image_as_content(img_path))  # base64 + mime_type
    input_content.append({"type": "text", "text": enhanced_prompt})
else:
    input_content = enhanced_prompt
```

## Usage

```python
sticker = create_sticker(
    prompt="a cute happy cat with big eyes",
    output_filename="cat.png",
    image_size="2K",
    save_raw=True  # Also save pre-processed version for debugging
)
```

Output:
```
🎨 Generating sticker: a cute happy cat with big eyes
   Resolution: 2K
✅ Image generated (mime_type: image/png)
🔧 Pass 1: HSV-based green removal...
🔧 Pass 2: Aggressive green removal...
✨ Cleaning up edges...
✅ Saved: cat.png
```

The PNG has a proper alpha channel. Works in Figma, Photoshop, chat apps, print-on-demand.

## What's Still Hard

- **Subjects with green in them.** A frog sticker will lose body parts. The prompt asks the model to avoid green, but it doesn't always comply. Workaround: use teal or forest green for those subjects.
- **Complex backgrounds.** The model sometimes adds shadows or gradients despite the prompt. Usually caught by the aggressive pass, but not always.

## Full Code

The complete implementation with all helper functions is available in [`interactions-generate-stickers.py`](../interactions-generate-stickers.py).
