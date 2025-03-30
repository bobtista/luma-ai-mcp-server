import asyncio
import logging
import os
from enum import Enum
from typing import Any, Literal, Optional

import httpx
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from pydantic import BaseModel

load_dotenv()
logger = logging.getLogger(__name__)


class Resolution(str, Enum):
    P540 = "540p"
    P720 = "720p"
    P1080 = "1080p"
    P4K = "4k"


class Duration(str, Enum):
    """
    Duration options for Luma API video generations.
    As of the current API version, only "5s" and "9s" are supported.
    """

    SHORT = "5s"
    LONG = "9s"


class ImageModel(str, Enum):
    """
    Image generation models supported by the Luma API.
    """

    PHOTON_1 = "photon-1"
    PHOTON_FLASH_1 = "photon-flash-1"


class KeyframeType(str, Enum):
    IMAGE = "image"
    GENERATION = "generation"


class LumaTools(str, Enum):
    PING = "ping"
    CREATE_GENERATION = "create_generation"
    GET_GENERATION = "get_generation"
    LIST_GENERATIONS = "list_generations"
    DELETE_GENERATION = "delete_generation"
    UPSCALE_GENERATION = "upscale_generation"
    ADD_AUDIO = "add_audio"
    GENERATE_IMAGE = "generate_image"
    GET_CREDITS = "get_credits"
    GET_CAMERA_MOTIONS = "get_camera_motions"


class ImageKeyframe(BaseModel):
    type: Literal[KeyframeType.IMAGE] = KeyframeType.IMAGE
    url: str


class GenerationKeyframe(BaseModel):
    type: Literal[KeyframeType.GENERATION] = KeyframeType.GENERATION
    id: str


class PingInput(BaseModel):
    pass


class CreateGenerationInput(BaseModel):
    prompt: str
    model: str = "ray-2"
    resolution: Optional[Resolution] = None
    duration: Optional[Duration] = None
    aspect_ratio: Optional[str] = None
    loop: Optional[bool] = None
    keyframes: Optional[dict] = None
    callback_url: Optional[str] = None


class GetGenerationInput(BaseModel):
    generation_id: str


class ListGenerationsInput(BaseModel):
    limit: int = 10
    offset: int = 0


class DeleteGenerationInput(BaseModel):
    generation_id: str


class UpscaleGenerationInput(BaseModel):
    generation_id: str
    resolution: Resolution


class AddAudioInput(BaseModel):
    generation_id: str
    prompt: str
    negative_prompt: Optional[str] = None
    callback_url: Optional[str] = None


class GenerateImageInput(BaseModel):
    prompt: str
    model: ImageModel = ImageModel.PHOTON_1


class GetCreditsInput(BaseModel):
    pass


class GetCameraMotionsInput(BaseModel):
    pass


async def _make_luma_request(method: str, endpoint: str, api_key: str = None, **kwargs) -> Any:
    """Make a request to the Luma API."""
    api_key = api_key or os.getenv("LUMA_API_KEY")
    if not api_key:
        raise ValueError("LUMA_API_KEY environment variable or --api-key option is required")

    base_url = "https://api.lumalabs.ai/dream-machine/v1"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    client = None
    try:
        client = httpx.AsyncClient(timeout=30.0)
        response = await client.request(method, f"{base_url}/{endpoint}", headers=headers, **kwargs)
        status_code = response.status_code

        if not response.content:
            return {}

        json_data = {}
        try:
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                json_data = response.json()
            else:
                text_content = response.text
                if text_content and (text_content.startswith("{") or text_content.startswith("[")):
                    json_data = response.json()
                else:
                    json_data = {"raw_response": text_content}
        except Exception as json_error:
            logging.warning(f"Failed to parse JSON response: {json_error}")
            json_data = {"raw_response": response.text}

        if status_code >= 400:
            error_msg = f"HTTP error {status_code}"
            if json_data:
                error_msg += f": {json_data}"
            raise ValueError(error_msg)

        return json_data
    except httpx.RequestError as e:
        logging.error(f"Request error: {e}", exc_info=True)
        raise ValueError(f"Network error: {str(e)}") from e
    except Exception as e:
        logging.error(f"Unexpected error in _make_luma_request: {e}", exc_info=True)
        raise
    finally:
        if client:
            try:
                await client.aclose()
            except Exception as e:
                logging.warning(f"Error closing httpx client: {e}")


async def ping(parameters: dict, api_key: Optional[str] = None) -> str:
    """Check if the Luma API is running."""
    try:
        result = await _make_luma_request("GET", "ping", api_key=api_key)

        result_details = ""
        if result:
            result_details = f": {result}"

        return f"Luma API is available and responding{result_details}"
    except Exception as e:
        logging.error(f"Error in ping: {str(e)}", exc_info=True)
        return f"Error pinging Luma API: {str(e)}"


async def create_generation(parameters: dict, api_key: Optional[str] = None) -> str:
    """Create a new video generation.

    Parameters:
        prompt: Required. The text prompt for the generation.
        model: Optional. Model to use (default: "ray-2").
        resolution: Optional. One of "540p", "720p", "1080p", or "4k".
        duration: Optional. ONLY "5s" or "9s" are supported by the API.
        aspect_ratio: Optional. The aspect ratio for the video.
        loop: Optional. Whether the video should loop.
        keyframes: Optional. Dictionary containing frame0/frame1 with type and url/id.
        callback_url: Optional. URL to notify when generation is complete.
    """
    try:
        prompt = parameters.get("prompt")
        if not prompt:
            raise ValueError("prompt parameter is required")

        data = {
            "prompt": prompt,
            "model": parameters.get("model", "ray-2"),
        }

        optional_params = [
            "resolution",
            "duration",
            "aspect_ratio",
            "loop",
            "callback_url",
        ]

        for param in optional_params:
            if param in parameters and parameters[param] is not None:
                data[param] = parameters[param]

        if "duration" in parameters and parameters["duration"] is not None:
            duration = parameters["duration"]
            if duration not in ["5s", "9s"]:
                logging.warning(
                    f"Unsupported duration value: {duration}. Only '5s' or '9s' are supported."
                )

        if "keyframes" in parameters and parameters["keyframes"]:
            keyframes = parameters["keyframes"]

            if not isinstance(keyframes, dict):
                raise ValueError("keyframes must be an object")

            if not any(key in keyframes for key in ["frame0", "frame1"]):
                raise ValueError("keyframes must contain frame0 or frame1")

            data["keyframes"] = keyframes

            keyframe_info = []
            if "frame0" in keyframes:
                frame_type = keyframes["frame0"].get("type")
                if frame_type == "image":
                    keyframe_info.append("starting from image")
                elif frame_type == "generation":
                    keyframe_info.append("extending existing video")

            if "frame1" in keyframes:
                frame_type = keyframes["frame1"].get("type")
                if frame_type == "image":
                    keyframe_info.append("ending with image")
                elif frame_type == "generation":
                    if "frame0" in keyframes:
                        keyframe_info.append("interpolating between videos")
                    else:
                        keyframe_info.append("reverse extending to existing video")

            logging.info(f"Creating generation with keyframes: {', '.join(keyframe_info)}")

        result = await _make_luma_request("POST", "generations", api_key=api_key, json=data)

        if not isinstance(result, dict):
            logging.error(f"Unexpected response format from Luma API: {result}")
            return (
                f"Error: Unexpected response format from Luma API. "
                f"Got {type(result).__name__} instead of dict."
            )

        generation_id = result.get("id", "Unknown")
        state = result.get("state", "Processing")
        generation_type = result.get("generation_type", "video")
        created_at = result.get("created_at", "Unknown")
        model = result.get("model", parameters.get("model", "ray-2"))

        assets = result.get("assets", {})
        if isinstance(assets, dict):
            asset_info = []
            if "video" in assets:
                asset_info.append(f"Video URL: {assets['video']}")
            if "image" in assets:
                asset_info.append(f"Image URL: {assets['image']}")
            if "progress_video" in assets:
                asset_info.append(f"Progress Video: {assets['progress_video']}")
        else:
            asset_info = []

        has_keyframes = "keyframes" in data and data["keyframes"]

        if generation_type == "image":
            return (
                f"Created image generation with ID: {generation_id}\n"
                f"State: {state}\n"
                f"Created at: {created_at}\n"
                f"Model: {model}\n"
                f"Prompt: {prompt}"
            )
        elif has_keyframes:
            keyframe_info = []
            if "frame0" in data.get("keyframes", {}):
                frame0 = data["keyframes"]["frame0"]
                if frame0.get("type") == "image":
                    keyframe_info.append("starting from an image")
                elif frame0.get("type") == "generation":
                    keyframe_info.append("extending an existing video")

            if "frame1" in data.get("keyframes", {}):
                frame1 = data["keyframes"]["frame1"]
                if frame1.get("type") == "image":
                    keyframe_info.append("ending with an image")
                elif frame1.get("type") == "generation":
                    if "frame0" in data.get("keyframes", {}):
                        keyframe_info.append("interpolating between videos")
                    else:
                        keyframe_info.append("reverse extending to an existing video")

            keyframe_description = ", ".join(keyframe_info)
            return (
                f"Created advanced generation ({keyframe_description}) with ID: {generation_id}\n"
                f"State: {state}\n"
                f"Created at: {created_at}\n"
                f"Model: {model}\n"
                f"Prompt: {prompt}"
            )
        else:
            return (
                f"Created text-to-video generation with ID: {generation_id}\n"
                f"State: {state}\n"
                f"Created at: {created_at}\n"
                f"Model: {model}\n"
                f"Prompt: {prompt}"
            )
    except Exception as e:
        logging.error(f"Error in create_generation: {str(e)}", exc_info=True)
        return f"Error creating generation: {str(e)}"


async def get_generation(parameters: dict, api_key: Optional[str] = None) -> str:
    """Get the status of a generation."""
    try:
        generation_id = parameters.get("generation_id")
        if not generation_id:
            raise ValueError("generation_id parameter is required")

        result = await _make_luma_request("GET", f"generations/{generation_id}", api_key=api_key)

        if not isinstance(result, dict):
            logging.error(f"Unexpected response format from Luma API: {result}")
            return (
                f"Error: Unexpected response format from Luma API. "
                f"Got {type(result).__name__} instead of dict."
            )

        result_id = result.get("id", generation_id)
        state = result.get("state", "Unknown")
        created_at = result.get("created_at", "Unknown")
        generation_type = result.get("generation_type", "video")
        model = result.get("model", "Unknown")
        failure_reason = result.get("failure_reason", "")

        state_info = f"State: {state}"
        if state == "failed" and failure_reason:
            state_info += f" (Reason: {failure_reason})"

        request_data = result.get("request", {})
        if not isinstance(request_data, dict):
            request_data = {}

        prompt = request_data.get("prompt", "Unknown")

        has_keyframes = False
        if isinstance(request_data, dict):
            keyframes = request_data.get("keyframes")
            has_keyframes = isinstance(keyframes, dict) and bool(keyframes)

        if generation_type == "image":
            type_display = "Image"
        else:
            type_display = "Advanced" if has_keyframes else "Text-to-video"

        assets = result.get("assets", {})
        if not isinstance(assets, dict):
            assets = {}

        asset_lines = []
        if generation_type == "image":
            if "image" in assets:
                asset_lines.append(f"Image URL: {assets['image']}")
        else:
            if "video" in assets:
                asset_lines.append(f"Video URL: {assets['video']}")
            if "progress_video" in assets:
                asset_lines.append(f"Progress video: {assets['progress_video']}")
            if "image" in assets:
                asset_lines.append(f"Thumbnail: {assets['image']}")

        assets_info = "\n".join(asset_lines) if asset_lines else "No assets available yet"

        output = [
            f"Generation ID: {result_id}",
            f"Type: {type_display}",
            state_info,
            f"Created at: {created_at}",
            f"Model: {model}",
            f"Prompt: {prompt}",
            assets_info,
        ]

        return "\n".join(output)
    except Exception as e:
        logging.error(f"Error in get_generation: {str(e)}", exc_info=True)
        return f"Error getting generation {generation_id}: {str(e)}"


async def list_generations(parameters: dict, api_key: Optional[str] = None) -> str:
    """List all generations."""
    try:
        limit = parameters.get("limit", 10)
        offset = parameters.get("offset", 0)

        result = await _make_luma_request(
            "GET", "generations", api_key=api_key, params={"limit": limit, "offset": offset}
        )

        if not result:
            return "No generations found"

        generations_list = []

        if isinstance(result, dict):
            if "generations" in result and isinstance(result["generations"], list):
                generations_list = result["generations"]
                has_more = result.get("has_more", False)
                count = result.get("count", len(generations_list))

                pagination_info = f"Showing {len(generations_list)} of {count} generations"
                if has_more:
                    pagination_info += " (more available)"
            else:
                if "id" in result and "state" in result:
                    generations_list = [result]
                else:
                    for field in ["data", "results", "items"]:
                        if field in result and isinstance(result[field], list):
                            generations_list = result[field]
                            break

                    if not generations_list:
                        logging.warning(f"Unexpected response structure: {result.keys()}")
                        return (
                            f"Response format from Luma API doesn't contain generations: {result}"
                        )
        elif isinstance(result, list):
            generations_list = result
        else:
            logging.error(f"Unexpected response format from Luma API: {result}")
            return (
                f"Error: Unexpected response format from Luma API. "
                f"Got {type(result).__name__} instead of object with generations."
            )

        if not generations_list:
            return "No generations found"

        output = ["Generations:"]
        if "pagination_info" in locals():
            output.append(pagination_info)

        for gen in generations_list:
            if not isinstance(gen, dict):
                logging.warning(f"Skipping non-dict generation: {gen}")
                continue

            generation_id = gen.get("id", "Unknown ID")
            state = gen.get("state", "Unknown state")
            created_at = gen.get("created_at", "Unknown date")
            generation_type = gen.get("generation_type", "video")

            request_data = gen.get("request", {})
            if not isinstance(request_data, dict):
                request_data = {}

            has_keyframes = False
            if isinstance(request_data, dict):
                keyframes = request_data.get("keyframes")
                has_keyframes = isinstance(keyframes, dict) and bool(keyframes)

            if generation_type == "image":
                type_display = "Image"
            else:
                type_display = "Advanced" if has_keyframes else "Text-to-video"

            prompt = request_data.get("prompt", "Unknown prompt")

            assets = gen.get("assets", {})
            if not isinstance(assets, dict):
                assets = {}

            if generation_type == "image":
                url = assets.get("image", "Not available yet")
                url_label = "Image URL"
            else:
                url = assets.get("video", "Not available yet")
                url_label = "Video URL"

            output.append(
                f"ID: {generation_id}\n"
                f"  Type: {type_display}\n"
                f"  State: {state}\n"
                f"  Created at: {created_at}\n"
                f"  Prompt: {prompt}\n"
                f"  {url_label}: {url}\n"
            )

        return "\n".join(output)
    except Exception as e:
        logging.error(f"Error in list_generations: {str(e)}", exc_info=True)
        return f"Error listing generations: {str(e)}"


async def delete_generation(parameters: dict, api_key: Optional[str] = None) -> str:
    """Delete a generation."""
    try:
        generation_id = parameters.get("generation_id")
        if not generation_id:
            raise ValueError("generation_id parameter is required")

        await _make_luma_request("DELETE", f"generations/{generation_id}", api_key=api_key)
        return f"Generation {generation_id} deleted successfully"
    except Exception as e:
        logging.error(f"Error in delete_generation: {str(e)}", exc_info=True)
        return f"Error deleting generation {parameters.get('generation_id')}: {str(e)}"


async def upscale_generation(parameters: dict, api_key: Optional[str] = None) -> str:
    """Upscale a video generation to higher resolution.

    Parameters:
        generation_id: Required. The ID of the generation to upscale.
        resolution: Required. The target resolution (540p, 720p, 1080p, 4k).
                   Must be higher than the original generation's resolution.
    """
    try:
        generation_id = parameters.get("generation_id")
        if not generation_id:
            raise ValueError("generation_id parameter is required")

        resolution = parameters.get("resolution")
        if not resolution:
            raise ValueError("resolution parameter is required for upscaling")

        valid_resolutions = ["540p", "720p", "1080p", "4k"]
        if resolution not in valid_resolutions:
            raise ValueError(
                f"Invalid resolution: {resolution}. Must be one of {', '.join(valid_resolutions)}"
            )

        request_data = {"resolution": resolution}

        max_retries = 2
        retry_count = 0

        while True:
            try:
                result = await _make_luma_request(
                    "POST",
                    f"generations/{generation_id}/upscale",
                    api_key=api_key,
                    json=request_data,
                )
                break
            except ValueError as e:
                error_msg = str(e)
                if "same resolution as the original" in error_msg:
                    raise ValueError(
                        f"Cannot upscale to {resolution} because the original generation is already at this resolution. "
                        f"Please choose a higher resolution."
                    ) from e
                elif "HTTP error 500" in error_msg and retry_count < max_retries:
                    retry_count += 1
                    logging.warning(
                        f"Server error during upscale, retrying ({retry_count}/{max_retries})..."
                    )
                    await asyncio.sleep(2)
                else:
                    raise

        if not isinstance(result, dict):
            logging.warning(f"Unexpected response format from upscale: {result}")
            return f"Upscale initiated for generation {generation_id}. Response: {result}"

        result_id = result.get("id", generation_id)
        state = result.get("state", "Processing")
        created_at = result.get("created_at", "Unknown")
        model = result.get("model", "Unknown")
        upscale_resolution = result.get("resolution", resolution or "Unknown")

        failure_reason = result.get("failure_reason", "")
        state_info = state
        if state == "failed" and failure_reason:
            state_info += f" (Reason: {failure_reason})"

        assets = result.get("assets", {})
        asset_lines = []
        if isinstance(assets, dict):
            if "video" in assets:
                asset_lines.append(f"Video URL: {assets['video']}")
            if "progress_video" in assets:
                asset_lines.append(f"Progress video: {assets['progress_video']}")
            if "image" in assets:
                asset_lines.append(f"Thumbnail: {assets['image']}")

        output = [
            f"Upscale initiated for generation {result_id}",
            f"Target resolution: {upscale_resolution}",
            f"Status: {state_info}",
            f"Created at: {created_at}",
            f"Model: {model}",
        ]

        if asset_lines:
            output.append("")
            output.append("Assets:")
            output.extend(asset_lines)

        return "\n".join(output)
    except Exception as e:
        error_msg = str(e)

        if "same resolution as the original" in error_msg:
            logging.error(f"Resolution error in upscale_generation: {error_msg}", exc_info=True)
            return (
                f"Error upscaling generation {parameters.get('generation_id')}: "
                f"The requested resolution ({parameters.get('resolution')}) is the same as the original. "
                f"Please choose a higher resolution."
            )
        elif "HTTP error 400" in error_msg:
            logging.error(f"Bad request in upscale_generation: {error_msg}", exc_info=True)
            import re

            detail_match = re.search(r"'detail': '([^']*)'", error_msg)
            detail = detail_match.group(1) if detail_match else "Invalid request"

            return (
                f"Error upscaling generation {parameters.get('generation_id')}: {detail}. "
                f"Common issues include:\n"
                f"- The generation is not in a completed state\n"
                f"- The requested resolution is not higher than the original\n"
                f"- The generation was already upscaled"
            )
        elif "HTTP error 500" in error_msg:
            logging.error(f"Server error in upscale_generation: {error_msg}", exc_info=True)
            return (
                f"Error upscaling generation {parameters.get('generation_id')}: Server Error. "
                f"This could be due to:\n"
                f"- The generation not being in a completed state\n"
                f"- The generation already being upscaled\n"
                f"- The Luma API experiencing temporary issues\n\n"
                f"Please check the generation status and try again later."
            )
        else:
            logging.error(f"Error in upscale_generation: {error_msg}", exc_info=True)
            return f"Error upscaling generation {parameters.get('generation_id')}: {error_msg}"


async def add_audio(parameters: dict, api_key: Optional[str] = None) -> str:
    """Add audio to a video generation.

    Parameters:
        generation_id: Required. The ID of the generation to add audio to.
        prompt: Required. The prompt for the audio generation.
        negative_prompt: Optional. The negative prompt for the audio generation.
        callback_url: Optional. URL to notify when the audio processing is complete.
    """
    try:
        generation_id = parameters.get("generation_id")
        if not generation_id:
            raise ValueError("generation_id parameter is required")

        prompt = parameters.get("prompt")
        if not prompt:
            raise ValueError("prompt parameter is required for audio generation")

        request_data = {"prompt": prompt}

        if "negative_prompt" in parameters and parameters["negative_prompt"]:
            request_data["negative_prompt"] = parameters["negative_prompt"]

        if "callback_url" in parameters and parameters["callback_url"]:
            request_data["callback_url"] = parameters["callback_url"]

        result = await _make_luma_request(
            "POST",
            f"generations/{generation_id}/audio",
            api_key=api_key,
            json=request_data,
        )

        if not isinstance(result, dict):
            logging.warning(f"Unexpected response format from add_audio: {result}")
            return f"Audio generation initiated for generation {generation_id}. Response: {result}"

        result_id = result.get("id", generation_id)
        state = result.get("state", "Processing")
        created_at = result.get("created_at", "Unknown")
        model = result.get("model", "Unknown")

        failure_reason = result.get("failure_reason", "")
        state_info = state
        if state == "failed" and failure_reason:
            state_info += f" (Reason: {failure_reason})"

        assets = result.get("assets", {})
        asset_lines = []
        if isinstance(assets, dict):
            if "video" in assets:
                asset_lines.append(f"Video URL: {assets['video']}")
            if "progress_video" in assets:
                asset_lines.append(f"Progress video: {assets['progress_video']}")
            if "image" in assets:
                asset_lines.append(f"Thumbnail: {assets['image']}")
            if "audio" in assets:
                asset_lines.append(f"Audio URL: {assets['audio']}")

        output = [
            f"Audio generation initiated for generation {result_id}",
            f"Status: {state_info}",
            f"Created at: {created_at}",
            f"Model: {model}",
            f"Prompt: {prompt}",
        ]

        if "negative_prompt" in request_data:
            output.append(f"Negative prompt: {request_data['negative_prompt']}")

        if asset_lines:
            output.append("")
            output.append("Assets:")
            output.extend(asset_lines)

        return "\n".join(output)
    except Exception as e:
        logging.error(f"Error in add_audio: {str(e)}", exc_info=True)
        return f"Error adding audio to generation {parameters.get('generation_id')}: {str(e)}"


async def generate_image(parameters: dict, api_key: Optional[str] = None) -> str:
    """Generate an image from a text prompt.

    Parameters:
        prompt: Required. The text prompt for the image generation.
        model: Optional. Model to use (default: "photon-1").
              Only "photon-1" and "photon-flash-1" are supported for image generation.
    """
    try:
        prompt = parameters.get("prompt")
        if not prompt:
            raise ValueError("prompt parameter is required")

        model = parameters.get("model", "photon-1")
        if model not in ["photon-1", "photon-flash-1"]:
            logging.warning(
                f"Unsupported image model: {model}. Using 'photon-1' instead. "
                f"Only 'photon-1' and 'photon-flash-1' are supported for image generation."
            )
            model = "photon-1"

        data = {
            "prompt": prompt,
            "model": model,
        }

        result = await _make_luma_request("POST", "generations/image", api_key=api_key, json=data)

        if not isinstance(result, dict):
            logging.warning(f"Unexpected response format from generate_image: {result}")
            return f"Image generation completed for prompt: {prompt}. Response: {result}"

        generation_id = result.get("id", "Unknown")
        state = result.get("state", "Processing")
        created_at = result.get("created_at", "Unknown")
        model = result.get("model", parameters.get("model", "ray-2"))

        failure_reason = result.get("failure_reason", "")
        state_info = state
        if state == "failed" and failure_reason:
            state_info += f" (Reason: {failure_reason})"

        assets = result.get("assets", {})
        image_url = "Image will be available when processing completes"

        if isinstance(assets, dict) and "image" in assets:
            image_url = assets["image"]

        output = [
            f"Image generation {state_info}",
            f"ID: {generation_id}",
            f"Created at: {created_at}",
            f"Model: {model}",
            f"Prompt: {prompt}",
            f"Image URL: {image_url}",
        ]

        return "\n".join(output)
    except Exception as e:
        logging.error(f"Error in generate_image: {str(e)}", exc_info=True)
        return f"Error generating image for prompt '{parameters.get('prompt')}': {str(e)}"


async def get_credits(parameters: dict, api_key: Optional[str] = None) -> str:
    """Get the credit information for the current user."""
    try:
        result = await _make_luma_request("GET", "credits", api_key=api_key)

        if not isinstance(result, dict):
            logging.warning(f"Unexpected response format from get_credits: {result}")
            return f"Credit Information: {result}"

        if "credit_balance" in result:
            credit_balance = result.get("credit_balance", "Unknown")
            return f"Credit Information:\nAvailable Credits: {credit_balance}"

        available = result.get("credits_available", "Unknown")
        used = result.get("credits_used", "Unknown")
        total = result.get("credits_total", "Unknown")

        return (
            f"Credit Information:\n"
            f"Available Credits: {available}\n"
            f"Used Credits: {used}\n"
            f"Total Credits: {total}"
        )
    except Exception as e:
        logging.error(f"Error in get_credits: {str(e)}", exc_info=True)
        return f"Error retrieving credit information: {str(e)}"


async def get_camera_motions(parameters: dict, api_key: Optional[str] = None) -> str:
    """Get all supported camera motions."""
    try:
        result = await _make_luma_request("GET", "generations/camera_motion/list", api_key=api_key)

        if not result:
            return "No camera motions available"

        if isinstance(result, list):
            if not result:
                return "No camera motions available"

            output = ["Available camera motions:"]

            for motion in result:
                if isinstance(motion, str):
                    output.append(f"- {motion}")
                elif isinstance(motion, dict):
                    if "name" in motion:
                        output.append(f"- {motion['name']}")
                    elif "id" in motion:
                        output.append(f"- {motion['id']}")
                    else:
                        output.append(f"- {motion}")
                else:
                    output.append(f"- {motion}")

            return "\n".join(output)
        elif isinstance(result, dict):
            for field in ["motions", "camera_motions", "data", "items", "results"]:
                if field in result and isinstance(result[field], list):
                    motions = result[field]
                    output = ["Available camera motions:"]

                    for motion in motions:
                        if isinstance(motion, str):
                            output.append(f"- {motion}")
                        elif isinstance(motion, dict) and "name" in motion:
                            output.append(f"- {motion['name']}")
                        elif isinstance(motion, dict) and "id" in motion:
                            output.append(f"- {motion['id']}")
                        else:
                            output.append(f"- {motion}")

                    return "\n".join(output)

            return f"Unexpected response format. Response contained: {list(result.keys())}"
        else:
            return f"Unexpected response format: {result}"

    except Exception as e:
        logging.error(f"Error in get_camera_motions: {str(e)}", exc_info=True)
        return f"Error retrieving camera motions: {str(e)}"


async def serve(api_key: Optional[str] = None) -> None:
    """Serve MCP requests."""
    logger.info("Starting Luma MCP server")

    server = Server("mcp-luma")

    @server.list_tools()
    async def list_tools() -> list:
        return [
            Tool(
                name=LumaTools.PING,
                description="Check if the Luma API is running",
                inputSchema=PingInput.model_json_schema(),
            ),
            Tool(
                name=LumaTools.CREATE_GENERATION,
                description="Creates a new video generation from text, image, or existing video",
                inputSchema=CreateGenerationInput.model_json_schema(),
            ),
            Tool(
                name=LumaTools.GET_GENERATION,
                description="Gets the status of a generation",
                inputSchema=GetGenerationInput.model_json_schema(),
            ),
            Tool(
                name=LumaTools.LIST_GENERATIONS,
                description="Lists all generations",
                inputSchema=ListGenerationsInput.model_json_schema(),
            ),
            Tool(
                name=LumaTools.DELETE_GENERATION,
                description="Deletes a generation",
                inputSchema=DeleteGenerationInput.model_json_schema(),
            ),
            Tool(
                name=LumaTools.UPSCALE_GENERATION,
                description="Upscales a video generation to higher resolution",
                inputSchema=UpscaleGenerationInput.model_json_schema(),
            ),
            Tool(
                name=LumaTools.ADD_AUDIO,
                description="Adds audio to a video generation",
                inputSchema=AddAudioInput.model_json_schema(),
            ),
            Tool(
                name=LumaTools.GENERATE_IMAGE,
                description="Generates an image from a text prompt",
                inputSchema=GenerateImageInput.model_json_schema(),
            ),
            Tool(
                name=LumaTools.GET_CREDITS,
                description="Gets credit information for the current user",
                inputSchema=GetCreditsInput.model_json_schema(),
            ),
            Tool(
                name=LumaTools.GET_CAMERA_MOTIONS,
                description="Gets all supported camera motions",
                inputSchema=GetCameraMotionsInput.model_json_schema(),
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list:
        logger.debug(f"Tool call: {name} with arguments {arguments}")

        match name:
            case LumaTools.PING:
                result = await ping(arguments, api_key)
                return [TextContent(type="text", text=result)]

            case LumaTools.CREATE_GENERATION:
                result = await create_generation(arguments, api_key)
                return [TextContent(type="text", text=result)]

            case LumaTools.GET_GENERATION:
                result = await get_generation(arguments, api_key)
                return [TextContent(type="text", text=result)]

            case LumaTools.LIST_GENERATIONS:
                result = await list_generations(arguments, api_key)
                return [TextContent(type="text", text=result)]

            case LumaTools.DELETE_GENERATION:
                result = await delete_generation(arguments, api_key)
                return [TextContent(type="text", text=result)]

            case LumaTools.UPSCALE_GENERATION:
                result = await upscale_generation(arguments, api_key)
                return [TextContent(type="text", text=result)]

            case LumaTools.ADD_AUDIO:
                result = await add_audio(arguments, api_key)
                return [TextContent(type="text", text=result)]

            case LumaTools.GENERATE_IMAGE:
                result = await generate_image(arguments, api_key)
                return [TextContent(type="text", text=result)]

            case LumaTools.GET_CREDITS:
                result = await get_credits(arguments, api_key)
                return [TextContent(type="text", text=result)]

            case LumaTools.GET_CAMERA_MOTIONS:
                result = await get_camera_motions(arguments, api_key)
                return [TextContent(type="text", text=result)]

            case _:
                raise ValueError(f"Unknown tool: {name}")

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)
