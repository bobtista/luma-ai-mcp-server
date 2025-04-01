import logging
import os
from enum import Enum
from typing import Literal, Optional

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


class AspectRatio(str, Enum):
    """
    Supported aspect ratios for video and image generations.
    """

    SQUARE = "1:1"
    LANDSCAPE = "16:9"
    PORTRAIT = "9:16"
    STANDARD = "4:3"
    STANDARD_PORTRAIT = "3:4"
    ULTRAWIDE = "21:9"
    ULTRAWIDE_PORTRAIT = "9:21"


class VideoModel(str, Enum):
    """
    Video generation models supported by the Luma API.
    """

    RAY_1_6 = "ray-1-6"
    RAY_2 = "ray-2"
    RAY_FLASH_2 = "ray-flash-2"


class ImageModel(str, Enum):
    """
    Image generation models supported by the Luma API.
    """

    PHOTON_1 = "photon-1"
    PHOTON_FLASH_1 = "photon-flash-1"


class State(str, Enum):
    """
    Possible states for a generation.
    """

    QUEUED = "queued"
    DREAMING = "dreaming"
    COMPLETED = "completed"
    FAILED = "failed"


class GenerationType(str, Enum):
    """
    Types of generations supported by the API.
    """

    VIDEO = "video"
    IMAGE = "image"
    UPSCALE_VIDEO = "upscale_video"
    ADD_AUDIO = "add_audio"


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
    """
    Input parameters for video generation.
    """

    prompt: str
    model: VideoModel = VideoModel.RAY_2
    resolution: Optional[Resolution] = None
    duration: Optional[Duration] = None
    aspect_ratio: Optional[AspectRatio] = None
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


class ImageRef(BaseModel):
    """
    Reference to an image with optional weight.
    """

    url: str
    weight: Optional[float] = None


class ImageIdentity(BaseModel):
    """
    Collection of images representing an identity.
    """

    images: list[str]


class ModifyImageRef(BaseModel):
    """
    Reference to an image to modify with optional weight.
    """

    url: str
    weight: Optional[float] = None


class GenerateImageInput(BaseModel):
    """
    Input parameters for image generation.
    """

    prompt: str
    model: ImageModel = ImageModel.PHOTON_1
    aspect_ratio: Optional[AspectRatio] = None
    callback_url: Optional[str] = None
    image_ref: Optional[list[ImageRef]] = None
    style_ref: Optional[list[ImageRef]] = None
    character_ref: Optional[dict[str, ImageIdentity]] = None
    modify_image_ref: Optional[ModifyImageRef] = None


class GetCreditsInput(BaseModel):
    pass


class GetCameraMotionsInput(BaseModel):
    pass


async def _make_luma_request(method: str, endpoint: str, data: Optional[dict] = None) -> dict:
    """Make a request to the Luma API."""
    api_key = os.getenv("LUMA_API_KEY")
    if not api_key:
        raise ValueError("LUMA_API_KEY environment variable is not set")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.request(
                method,
                f"https://api.lumalabs.ai/dream-machine/v1{endpoint}",
                headers=headers,
                json=data if data else None,
            )

            if response.status_code >= 400:
                error_msg = f"API request failed with status {response.status_code}"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg = f"{error_msg}: {error_data['error']}"
                except Exception:
                    pass
                raise ValueError(error_msg)

            return response.json()
        except httpx.NetworkError as e:
            logger.error(f"Network error occurred: {str(e)}")
            raise


async def ping(parameters: dict) -> str:
    """Check if the Luma API is running."""
    try:
        await _make_luma_request("GET", "/ping")
        return "Luma API is available and responding"
    except Exception as e:
        logger.error(f"Error in ping: {str(e)}", exc_info=True)
        return f"Error pinging Luma API: {str(e)}"


async def create_generation(params: dict) -> str:
    """Create a new generation."""
    if "prompt" not in params:
        raise ValueError("prompt parameter is required")

    if "model" in params:
        model = params["model"]
        if isinstance(model, str):
            if model not in [m.value for m in VideoModel]:
                raise ValueError(f"Invalid model: {model}")
        elif isinstance(model, VideoModel):
            params["model"] = model.value

    if "aspect_ratio" in params:
        aspect_ratio = params["aspect_ratio"]
        if isinstance(aspect_ratio, str):
            if aspect_ratio not in [a.value for a in AspectRatio]:
                raise ValueError(f"Invalid aspect ratio: {aspect_ratio}")
        elif isinstance(aspect_ratio, AspectRatio):
            params["aspect_ratio"] = aspect_ratio.value

    if "keyframes" in params:
        keyframes = params["keyframes"]
        if not isinstance(keyframes, dict):
            raise ValueError("keyframes must be an object")
        if not any(key in keyframes for key in ["frame0", "frame1"]):
            raise ValueError("keyframes must contain frame0 or frame1")

    input_data = CreateGenerationInput(**params)
    request_data = input_data.model_dump(exclude_none=True)
    response = await _make_luma_request("POST", "/generations", request_data)

    if input_data.keyframes:
        output = [
            f"Created advanced generation with ID: {response['id']}",
            f"State: {response['state']}",
        ]
        if "frame0" in input_data.keyframes:
            output.append("starting from an image")
        if "frame1" in input_data.keyframes:
            output.append("ending with an image")
    else:
        output = [
            f"Created text-to-video generation with ID: {response['id']}",
            f"State: {response['state']}",
        ]

    return "\n".join(output)


async def get_generation(parameters: dict) -> str:
    """Get the status of a generation."""
    try:
        generation_id = parameters.get("generation_id")
        if not generation_id:
            raise ValueError("generation_id parameter is required")

        result = await _make_luma_request("GET", f"/generations/{generation_id}")

        if not isinstance(result, dict):
            raise ValueError("Invalid response from API")

        output = [f"Generation ID: {result['id']}", f"State: {result['state']}"]

        if result.get("failure_reason"):
            output.append(f"Reason: {result['failure_reason']}")

        if result.get("assets", {}).get("video"):
            output.append(f"Video URL: {result['assets']['video']}")

        return "\n".join(output)
    except Exception as e:
        logger.error(f"Error in get_generation: {str(e)}", exc_info=True)
        return f"Error getting generation {generation_id}: {str(e)}"


async def list_generations(parameters: dict) -> str:
    """List all generations."""
    try:
        limit = parameters.get("limit", 10)
        offset = parameters.get("offset", 0)

        result = await _make_luma_request("GET", "/generations", {"limit": limit, "offset": offset})

        if not isinstance(result, dict) or "generations" not in result:
            raise ValueError("Invalid response from API")

        output = ["Generations:"]
        for gen in result["generations"]:
            output.extend(
                [
                    f"ID: {gen['id']}",
                    f"State: {gen['state']}",
                ]
            )
            if gen.get("assets", {}).get("video"):
                output.append(f"Video URL: {gen['assets']['video']}")
            output.append("")

        return "\n".join(output)
    except Exception as e:
        logger.error(f"Error in list_generations: {str(e)}", exc_info=True)
        return f"Error listing generations: {str(e)}"


async def delete_generation(parameters: dict) -> str:
    """Delete a generation."""
    try:
        generation_id = parameters.get("generation_id")
        if not generation_id:
            raise ValueError("generation_id parameter is required")

        await _make_luma_request("DELETE", f"/generations/{generation_id}")
        return f"Generation {generation_id} deleted successfully"
    except Exception as e:
        logger.error(f"Error in delete_generation: {str(e)}", exc_info=True)
        return f"Error deleting generation {generation_id}: {str(e)}"


async def upscale_generation(parameters: dict) -> str:
    """Upscale a video generation."""
    try:
        generation_id = parameters.get("generation_id")
        if not generation_id:
            raise ValueError("generation_id parameter is required")

        resolution = parameters.get("resolution")
        if not resolution:
            raise ValueError("resolution parameter is required")

        request_data = {"generation_type": "upscale_video", "resolution": resolution}
        result = await _make_luma_request(
            "POST", f"/generations/{generation_id}/upscale", request_data
        )

        return (
            f"Upscale initiated for generation {generation_id}\n"
            f"Status: {result['state']}\n"
            f"Target resolution: {resolution}"
        )
    except Exception as e:
        logger.error(f"Error in upscale_generation: {str(e)}", exc_info=True)
        return f"Error upscaling generation {generation_id}: {str(e)}"


async def add_audio(parameters: dict) -> str:
    """Add audio to a video generation."""
    try:
        generation_id = parameters.get("generation_id")
        if not generation_id:
            raise ValueError("generation_id parameter is required")

        prompt = parameters.get("prompt")
        if not prompt:
            raise ValueError("prompt parameter is required")

        request_data = {"generation_type": "add_audio", "prompt": prompt}
        if "negative_prompt" in parameters:
            request_data["negative_prompt"] = parameters["negative_prompt"]

        result = await _make_luma_request(
            "POST", f"/generations/{generation_id}/audio", request_data
        )

        return (
            f"Audio generation initiated for generation {generation_id}\n"
            f"Status: {result['state']}\n"
            f"Prompt: {prompt}"
        )
    except Exception as e:
        logger.error(f"Error in add_audio: {str(e)}", exc_info=True)
        return f"Error adding audio to generation {generation_id}: {str(e)}"


async def generate_image(params: dict) -> str:
    """Generate an image using the Luma API."""
    try:
        input_data = GenerateImageInput(**params)
    except Exception as e:
        error_msg = str(e)
        if "model" in error_msg:
            raise ValueError(f"Invalid model: {params.get('model')}") from e
        elif "aspect_ratio" in error_msg:
            raise ValueError(f"Invalid aspect ratio: {params.get('aspect_ratio')}") from e
        raise

    model_value = input_data.model.value
    aspect_ratio_value = input_data.aspect_ratio.value if input_data.aspect_ratio else None

    request_data = input_data.model_dump(exclude_none=True)
    response = await _make_luma_request("POST", "/generations/image", request_data)

    if "assets" not in response or "image" not in response["assets"]:
        raise ValueError("No image URL in API response")

    output = ["Image generation completed"]
    output.append(f"Prompt: {input_data.prompt}")
    output.append(f"Model: {model_value}")
    if aspect_ratio_value:
        output.append(f"Aspect ratio: {aspect_ratio_value}")
    output.append(f"Image URL: {response['assets']['image']}")

    return "\n".join(output)


async def get_credits(parameters: dict) -> str:
    """Get the credit information for the current user."""
    try:
        result = await _make_luma_request("GET", "/credits")

        if not isinstance(result, dict):
            raise ValueError("Invalid response from API")

        return f"Credit Information:\nAvailable Credits: {result.get('credit_balance', 0)}"
    except Exception as e:
        logger.error(f"Error in get_credits: {str(e)}", exc_info=True)
        return f"Error retrieving credit information: {str(e)}"


async def get_camera_motions(parameters: dict) -> str:
    """Get all supported camera motions."""
    try:
        result = await _make_luma_request("GET", "/generations/camera_motion/list")

        if not result:
            return "No camera motions available"

        return "Available camera motions:\n" + ", ".join(result)
    except Exception as e:
        logger.error(f"Error in get_camera_motions: {str(e)}", exc_info=True)
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
                result = await ping(arguments)
                return [TextContent(type="text", text=result)]

            case LumaTools.CREATE_GENERATION:
                result = await create_generation(arguments)
                return [TextContent(type="text", text=result)]

            case LumaTools.GET_GENERATION:
                result = await get_generation(arguments)
                return [TextContent(type="text", text=result)]

            case LumaTools.LIST_GENERATIONS:
                result = await list_generations(arguments)
                return [TextContent(type="text", text=result)]

            case LumaTools.DELETE_GENERATION:
                result = await delete_generation(arguments)
                return [TextContent(type="text", text=result)]

            case LumaTools.UPSCALE_GENERATION:
                result = await upscale_generation(arguments)
                return [TextContent(type="text", text=result)]

            case LumaTools.ADD_AUDIO:
                result = await add_audio(arguments)
                return [TextContent(type="text", text=result)]

            case LumaTools.GENERATE_IMAGE:
                result = await generate_image(arguments)
                return [TextContent(type="text", text=result)]

            case LumaTools.GET_CREDITS:
                result = await get_credits(arguments)
                return [TextContent(type="text", text=result)]

            case LumaTools.GET_CAMERA_MOTIONS:
                result = await get_camera_motions(arguments)
                return [TextContent(type="text", text=result)]

            case _:
                raise ValueError(f"Unknown tool: {name}")

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)
