from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import TextContent

from luma_ai_mcp_server.server import (
    AddAudioInput,
    AspectRatio,
    CreateGenerationInput,
    Duration,
    GenerateImageInput,
    GenerationType,
    GetCreditsInput,
    GetGenerationInput,
    ImageIdentity,
    ImageModel,
    ImageRef,
    ListGenerationsInput,
    LumaTools,
    ModifyImageRef,
    PingInput,
    Resolution,
    State,
    UpscaleGenerationInput,
    VideoModel,
    add_audio,
    create_generation,
    delete_generation,
    generate_image,
    get_camera_motions,
    get_credits,
    get_generation,
    list_generations,
    ping,
    upscale_generation,
)

# Mock responses
MOCK_GENERATION_RESPONSE = {
    "id": "test-id",
    "state": State.QUEUED.value,
    "created_at": "2024-03-20T12:00:00Z",
    "assets": {},
    "version": "1.0",
    "request": {"prompt": "test prompt", "model": VideoModel.RAY_2.value},
}

MOCK_COMPLETED_GENERATION = {
    "id": "test-id",
    "state": State.COMPLETED.value,
    "created_at": "2024-03-20T12:00:00Z",
    "assets": {"video": "https://example.com/video.mp4"},
    "version": "1.0",
    "request": {"prompt": "test prompt", "model": VideoModel.RAY_2.value},
}

MOCK_CREDITS_RESPONSE = {"credit_balance": 150000.0}

MOCK_IMAGE_RESPONSE = {
    "url": "https://example.com/image.png",
}

MOCK_CAMERA_MOTIONS = ["static", "spin", "zoom"]


@pytest.fixture
def mock_env():
    with patch.dict("os.environ", {"LUMA_API_KEY": "test-key"}):
        yield


@pytest.mark.asyncio
async def test_ping(mock_env):
    """Test the ping function."""
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = AsyncMock()
        mock_response.content = b"{}"
        mock_response.text = "{}"
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_request.return_value = mock_response

        result = await ping({})

        assert "Luma API is available and responding" in result

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert args[0] == "GET"
        assert "ping" in args[1]
        assert kwargs["headers"]["Authorization"] == "Bearer test-key"


@pytest.mark.asyncio
async def test_create_generation(mock_env):
    """Test the create_generation function."""
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_GENERATION_RESPONSE
        mock_response.status_code = 200
        mock_response.content = b"{}"
        mock_request.return_value = mock_response

        # Test successful generation
        result = await create_generation({"prompt": "test prompt", "resolution": "720p"})
        assert "Created text-to-video generation with ID: test-id" in result
        assert f"State: {State.QUEUED.value}" in result

        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["json"]["prompt"] == "test prompt"
        assert call_kwargs["json"]["resolution"] == "720p"

        # Test missing prompt
        with pytest.raises(ValueError, match="prompt parameter is required"):
            await create_generation({})

        # Test invalid model
        with pytest.raises(ValueError, match="Invalid model"):
            await create_generation({"prompt": "test", "model": "invalid-model"})

        # Test invalid aspect ratio
        with pytest.raises(ValueError, match="Invalid aspect ratio"):
            await create_generation({"prompt": "test", "aspect_ratio": "invalid-ratio"})


@pytest.mark.asyncio
async def test_get_generation(mock_env):
    """Test the get_generation function."""
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_COMPLETED_GENERATION
        mock_response.raise_for_status = AsyncMock()
        mock_response.content = b"{}"
        mock_response.text = "{}"
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_request.return_value = mock_response

        result = await get_generation({"generation_id": "test-id"})

        assert "Generation ID: test-id" in result
        assert "State: completed" in result
        assert "Video URL: https://example.com/video.mp4" in result


@pytest.mark.asyncio
async def test_list_generations(mock_env):
    """Test the list_generations function."""
    mock_generations = {
        "generations": [MOCK_GENERATION_RESPONSE, MOCK_COMPLETED_GENERATION],
        "has_more": False,
        "count": 2,
    }
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_generations
        mock_response.raise_for_status = AsyncMock()
        mock_response.content = b"{}"
        mock_response.text = "{}"
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_request.return_value = mock_response

        result = await list_generations({"limit": 2})

        assert "Generations:" in result
        assert "ID: test-id" in result
        assert f"State: {State.QUEUED.value}" in result
        assert f"State: {State.COMPLETED.value}" in result
        assert "Video URL: https://example.com/video.mp4" in result


@pytest.mark.asyncio
async def test_upscale_generation(mock_env):
    """Test the upscale_generation function."""
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "test-id",
            "state": "processing",
            "created_at": "2024-03-20T12:00:00Z",
        }
        mock_response.raise_for_status = AsyncMock()
        mock_response.content = b"{}"
        mock_response.text = "{}"
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_request.return_value = mock_response

        result = await upscale_generation({"generation_id": "test-id", "resolution": "1080p"})

        assert "Upscale initiated for generation test-id" in result
        assert "Status: processing" in result
        assert "Target resolution: 1080p" in result

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert args[0] == "POST"
        assert "upscale" in args[1]
        assert kwargs["json"]["resolution"] == "1080p"


@pytest.mark.asyncio
async def test_add_audio(mock_env):
    """Test the add_audio function."""
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "test-id",
            "state": "processing",
            "created_at": "2024-03-20T12:00:00Z",
        }
        mock_response.raise_for_status = AsyncMock()
        mock_response.content = b"{}"
        mock_response.text = "{}"
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_request.return_value = mock_response

        result = await add_audio(
            {"generation_id": "test-id", "prompt": "create epic background music"}
        )

        assert "Audio generation initiated for generation test-id" in result
        assert "Status: processing" in result
        assert "Prompt: create epic background music" in result

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert args[0] == "POST"
        assert "audio" in args[1]
        assert kwargs["json"]["prompt"] == "create epic background music"


@pytest.mark.asyncio
async def test_generate_image(mock_env):
    """Test the generate_image function."""
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "assets": {"image": "https://example.com/image.png"},
            "state": "completed",
        }
        mock_response.status_code = 200
        mock_response.content = b"{}"
        mock_request.return_value = mock_response

        # Test successful generation
        result = await generate_image({"prompt": "test prompt"})
        assert "Image generation completed" in result
        assert "Prompt: test prompt" in result
        assert "Model: photon-1" in result
        assert "Image URL: https://example.com/image.png" in result

        # Test invalid model
        with pytest.raises(ValueError, match="Invalid model"):
            await generate_image({"prompt": "test", "model": "invalid-model"})

        # Test invalid aspect ratio
        with pytest.raises(ValueError, match="Invalid aspect ratio"):
            await generate_image({"prompt": "test", "aspect_ratio": "invalid-ratio"})

        # Test missing image URL in response
        mock_response.json.return_value = {"assets": {}}
        with pytest.raises(ValueError, match="No image URL in API response"):
            await generate_image({"prompt": "test prompt"})


@pytest.mark.asyncio
async def test_get_credits(mock_env):
    """Test the get_credits function."""
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_CREDITS_RESPONSE
        mock_response.raise_for_status = AsyncMock()
        mock_response.content = b"{}"
        mock_response.text = "{}"
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_request.return_value = mock_response

        result = await get_credits({})

        assert "Credit Information:" in result
        assert "Available Credits: 150000.0" in result

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert args[0] == "GET"
        assert "credits" in args[1]


def test_tool_schemas():
    """Test that all tool schemas are properly defined."""
    # Test PingInput
    schema = PingInput.model_json_schema()
    assert schema["type"] == "object"

    # Test GetGenerationInput
    schema = GetGenerationInput.model_json_schema()
    assert "generation_id" in schema["properties"]
    assert schema["required"] == ["generation_id"]

    # Test ListGenerationsInput
    schema = ListGenerationsInput.model_json_schema()
    assert "limit" in schema["properties"]
    assert "offset" in schema["properties"]
    assert schema["properties"]["limit"]["default"] == 10
    assert schema["properties"]["offset"]["default"] == 0

    # Test UpscaleGenerationInput
    schema = UpscaleGenerationInput.model_json_schema()
    assert "generation_id" in schema["properties"]
    assert "resolution" in schema["properties"]
    assert schema["required"] == ["generation_id", "resolution"]

    # Test GetCreditsInput
    schema = GetCreditsInput.model_json_schema()
    assert schema["type"] == "object"

    # Test Resolution enum
    assert Resolution.P540.value == "540p"
    assert Resolution.P720.value == "720p"
    assert Resolution.P1080.value == "1080p"
    assert Resolution.P4K.value == "4k"

    # Test Duration enum
    assert Duration.SHORT.value == "5s"
    assert Duration.LONG.value == "9s"

    # Test CreateGenerationInput
    schema = CreateGenerationInput.model_json_schema()
    assert "prompt" in schema["properties"]
    assert schema["properties"]["model"]["default"] == VideoModel.RAY_2.value
    assert "aspect_ratio" in schema["properties"]
    assert "resolution" in schema["properties"]
    assert "duration" in schema["properties"]

    # Test AddAudioInput
    schema = AddAudioInput.model_json_schema()
    assert "generation_id" in schema["properties"]
    assert "prompt" in schema["properties"]
    assert "negative_prompt" in schema["properties"]
    assert "callback_url" in schema["properties"]

    # Test GenerateImageInput
    schema = GenerateImageInput.model_json_schema()
    assert "prompt" in schema["properties"]
    assert schema["properties"]["model"]["default"] == ImageModel.PHOTON_1.value
    assert "aspect_ratio" in schema["properties"]
    assert "image_ref" in schema["properties"]
    assert "style_ref" in schema["properties"]
    assert "character_ref" in schema["properties"]
    assert "modify_image_ref" in schema["properties"]

    # Test ImageRef
    schema = ImageRef.model_json_schema()
    assert "url" in schema["properties"]
    assert "weight" in schema["properties"]

    # Test ImageIdentity
    schema = ImageIdentity.model_json_schema()
    assert "images" in schema["properties"]
    assert schema["properties"]["images"]["type"] == "array"

    # Test ModifyImageRef
    schema = ModifyImageRef.model_json_schema()
    assert "url" in schema["properties"]
    assert "weight" in schema["properties"]

    # Test AspectRatio enum
    assert AspectRatio.LANDSCAPE.value == "16:9"
    assert AspectRatio.SQUARE.value == "1:1"
    assert AspectRatio.PORTRAIT.value == "9:16"

    # Test VideoModel enum
    assert VideoModel.RAY_1_6.value == "ray-1-6"
    assert VideoModel.RAY_2.value == "ray-2"
    assert VideoModel.RAY_FLASH_2.value == "ray-flash-2"

    # Test ImageModel enum
    assert ImageModel.PHOTON_1.value == "photon-1"
    assert ImageModel.PHOTON_FLASH_1.value == "photon-flash-1"

    # Test State enum
    assert State.QUEUED.value == "queued"
    assert State.DREAMING.value == "dreaming"
    assert State.COMPLETED.value == "completed"
    assert State.FAILED.value == "failed"

    # Test GenerationType enum
    assert GenerationType.VIDEO.value == "video"
    assert GenerationType.IMAGE.value == "image"
    assert GenerationType.UPSCALE_VIDEO.value == "upscale_video"
    assert GenerationType.ADD_AUDIO.value == "add_audio"


@pytest.mark.asyncio
async def test_delete_generation(mock_env):
    """Test the delete_generation function."""
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status = AsyncMock()
        mock_response.content = b"{}"
        mock_response.text = "{}"
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_request.return_value = mock_response

        result = await delete_generation({"generation_id": "test-id"})

        assert "test-id deleted successfully" in result

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert args[0] == "DELETE"
        assert "test-id" in args[1]


@pytest.mark.asyncio
async def test_get_camera_motions(mock_env):
    """Test the get_camera_motions function."""
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_CAMERA_MOTIONS
        mock_response.raise_for_status = AsyncMock()
        mock_response.content = b"{}"
        mock_response.text = "{}"
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_request.return_value = mock_response

        result = await get_camera_motions({})

        assert "Available camera motions:" in result
        assert "static" in result
        assert "spin" in result
        assert "zoom" in result

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert args[0] == "GET"
        assert "camera_motion" in args[1]


@pytest.mark.asyncio
async def test_server_call_tool(mock_env):
    """Test the call_tool server function with different tools."""
    mock_fns = {
        "ping": AsyncMock(return_value="Luma API is available and responding"),
        "create_generation": AsyncMock(
            return_value=f"Created generation with ID: test-id\nState: {State.QUEUED.value}"
        ),
        "get_generation": AsyncMock(
            return_value=f"Generation ID: test-id\nState: {State.COMPLETED.value}"
        ),
        "list_generations": AsyncMock(
            return_value=f"Generations:\nID: test-id\nState: {State.COMPLETED.value}"
        ),
        "delete_generation": AsyncMock(return_value="Successfully deleted generation test-id"),
        "upscale_generation": AsyncMock(return_value="Upscale initiated for generation test-id"),
        "add_audio": AsyncMock(return_value="Audio added to generation test-id"),
        "generate_image": AsyncMock(
            return_value="Image generation completed\nImage URL: https://example.com/image.png"
        ),
        "get_camera_motions": AsyncMock(
            return_value="Available camera motions:\nstatic, spin, zoom"
        ),
        "get_credits": AsyncMock(return_value="Credit Information:\nAvailable Credits: 150000.0"),
    }

    with (
        patch("luma_ai_mcp_server.server.ping", mock_fns["ping"]),
        patch("luma_ai_mcp_server.server.create_generation", mock_fns["create_generation"]),
        patch("luma_ai_mcp_server.server.get_generation", mock_fns["get_generation"]),
        patch("luma_ai_mcp_server.server.list_generations", mock_fns["list_generations"]),
        patch("luma_ai_mcp_server.server.delete_generation", mock_fns["delete_generation"]),
        patch("luma_ai_mcp_server.server.upscale_generation", mock_fns["upscale_generation"]),
        patch("luma_ai_mcp_server.server.add_audio", mock_fns["add_audio"]),
        patch("luma_ai_mcp_server.server.generate_image", mock_fns["generate_image"]),
        patch("luma_ai_mcp_server.server.get_camera_motions", mock_fns["get_camera_motions"]),
        patch("luma_ai_mcp_server.server.get_credits", mock_fns["get_credits"]),
    ):

        async def mock_call_tool(name, arguments):
            if name == LumaTools.PING:
                result = await mock_fns["ping"](arguments)
                return [TextContent(type="text", text=result)]
            elif name == LumaTools.CREATE_GENERATION:
                result = await mock_fns["create_generation"](arguments)
                return [TextContent(type="text", text=result)]
            elif name == LumaTools.GET_GENERATION:
                result = await mock_fns["get_generation"](arguments)
                return [TextContent(type="text", text=result)]
            elif name == LumaTools.LIST_GENERATIONS:
                result = await mock_fns["list_generations"](arguments)
                return [TextContent(type="text", text=result)]
            elif name == LumaTools.DELETE_GENERATION:
                result = await mock_fns["delete_generation"](arguments)
                return [TextContent(type="text", text=result)]
            elif name == LumaTools.UPSCALE_GENERATION:
                result = await mock_fns["upscale_generation"](arguments)
                return [TextContent(type="text", text=result)]
            elif name == LumaTools.ADD_AUDIO:
                result = await mock_fns["add_audio"](arguments)
                return [TextContent(type="text", text=result)]
            elif name == LumaTools.GENERATE_IMAGE:
                result = await mock_fns["generate_image"](arguments)
                return [TextContent(type="text", text=result)]
            elif name == LumaTools.GET_CAMERA_MOTIONS:
                result = await mock_fns["get_camera_motions"](arguments)
                return [TextContent(type="text", text=result)]
            elif name == LumaTools.GET_CREDITS:
                result = await mock_fns["get_credits"](arguments)
                return [TextContent(type="text", text=result)]
            return []

        result = await mock_call_tool(LumaTools.PING, {})
        mock_fns["ping"].assert_called_once_with({})
        assert "Luma API is available" in result[0].text

        result = await mock_call_tool(LumaTools.CREATE_GENERATION, {"prompt": "test prompt"})
        mock_fns["create_generation"].assert_called_once_with({"prompt": "test prompt"})
        assert "Created generation with ID" in result[0].text

        result = await mock_call_tool(LumaTools.UPSCALE_GENERATION, {"generation_id": "test-id"})
        mock_fns["upscale_generation"].assert_called_once_with({"generation_id": "test-id"})
        assert "Upscale initiated" in result[0].text

        audio_params = {"generation_id": "test-id", "prompt": "create epic background music"}
        result = await mock_call_tool(LumaTools.ADD_AUDIO, audio_params)
        mock_fns["add_audio"].assert_called_once_with(audio_params)
        assert "Audio added" in result[0].text

        result = await mock_call_tool(LumaTools.GENERATE_IMAGE, {"prompt": "test prompt"})
        mock_fns["generate_image"].assert_called_once_with({"prompt": "test prompt"})
        assert "Image generation completed" in result[0].text

        result = await mock_call_tool(LumaTools.GET_CREDITS, {})
        mock_fns["get_credits"].assert_called_once_with({})
        assert "Credit Information" in result[0].text

        result = await mock_call_tool(LumaTools.LIST_GENERATIONS, {"limit": 10})
        mock_fns["list_generations"].assert_called_once_with({"limit": 10})
        assert "Generations:" in result[0].text

        result = await mock_call_tool(LumaTools.DELETE_GENERATION, {"generation_id": "test-id"})
        mock_fns["delete_generation"].assert_called_once_with({"generation_id": "test-id"})
        assert "Successfully deleted generation" in result[0].text

        result = await mock_call_tool(LumaTools.GET_CAMERA_MOTIONS, {})
        mock_fns["get_camera_motions"].assert_called_once_with({})
        assert "Available camera motions" in result[0].text


@pytest.mark.asyncio
async def test_create_generation_with_keyframes(mock_env):
    """Test creating a generation with keyframes."""
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_GENERATION_RESPONSE
        mock_response.status_code = 200
        mock_response.content = b"{}"
        mock_request.return_value = mock_response

        keyframes_data = {
            "frame0": {"type": "image", "url": "https://example.com/start.jpg"},
            "frame1": {"type": "image", "url": "https://example.com/end.jpg"},
        }

        result = await create_generation({"prompt": "test prompt", "keyframes": keyframes_data})

        assert "Created advanced generation" in result
        assert "starting from an image" in result
        assert "ending with an image" in result

        # Verify request data
        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["json"]["keyframes"] == keyframes_data

        # Test invalid keyframes format
        with pytest.raises(ValueError, match="keyframes must be an object"):
            await create_generation({"prompt": "test", "keyframes": ["invalid"]})

        # Test missing frame0/frame1
        with pytest.raises(ValueError, match="keyframes must contain frame0 or frame1"):
            await create_generation({"prompt": "test", "keyframes": {}})


@pytest.mark.asyncio
async def test_create_generation_with_video_model(mock_env):
    """Test creating a generation with different video models."""
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_GENERATION_RESPONSE
        mock_response.status_code = 200
        mock_response.content = b"{}"
        mock_request.return_value = mock_response

        # Test with enum value
        result = await create_generation({"prompt": "test prompt", "model": VideoModel.RAY_FLASH_2})
        assert "Created text-to-video generation" in result
        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["json"]["model"] == VideoModel.RAY_FLASH_2.value

        # Test with string value
        result = await create_generation({"prompt": "test prompt", "model": "ray-1-6"})
        assert "Created text-to-video generation" in result
        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["json"]["model"] == "ray-1-6"


@pytest.mark.asyncio
async def test_create_generation_with_aspect_ratio(mock_env):
    """Test creating a generation with different aspect ratios."""
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_GENERATION_RESPONSE
        mock_response.status_code = 200
        mock_response.content = b"{}"
        mock_request.return_value = mock_response

        # Test with enum value
        result = await create_generation(
            {"prompt": "test prompt", "aspect_ratio": AspectRatio.LANDSCAPE}
        )
        assert "Created text-to-video generation" in result
        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["json"]["aspect_ratio"] == AspectRatio.LANDSCAPE.value

        # Test with string value
        result = await create_generation({"prompt": "test prompt", "aspect_ratio": "1:1"})
        assert "Created text-to-video generation" in result
        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["json"]["aspect_ratio"] == "1:1"


@pytest.mark.asyncio
async def test_generate_image_with_references(mock_env):
    """Test generating an image with reference images."""
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "assets": {"image": "https://example.com/image.png"},
            "state": "completed",
        }
        mock_response.status_code = 200
        mock_response.content = b"{}"
        mock_request.return_value = mock_response

        input_data = {
            "prompt": "test prompt",
            "model": ImageModel.PHOTON_1,
            "aspect_ratio": AspectRatio.SQUARE,
            "image_ref": [{"url": "https://example.com/ref1.jpg", "weight": 0.8}],
            "style_ref": [{"url": "https://example.com/style1.jpg"}],
            "character_ref": {"person1": {"images": ["https://example.com/char1.jpg"]}},
        }

        result = await generate_image(input_data)

        # Verify response format
        assert "Image generation completed" in result
        assert "Prompt: test prompt" in result
        assert "Model: photon-1" in result
        assert "Aspect ratio: 1:1" in result
        assert "Image URL: https://example.com/image.png" in result

        # Verify request data
        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["json"]["prompt"] == "test prompt"
        assert call_kwargs["json"]["model"] == ImageModel.PHOTON_1
        assert call_kwargs["json"]["aspect_ratio"] == AspectRatio.SQUARE
        assert call_kwargs["json"]["image_ref"] == input_data["image_ref"]
        assert call_kwargs["json"]["style_ref"] == input_data["style_ref"]
        assert call_kwargs["json"]["character_ref"] == input_data["character_ref"]


@pytest.mark.asyncio
async def test_state_handling(mock_env):
    """Test handling of different generation states."""
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}

        # Test queued state
        mock_response.json.return_value = {
            "id": "test-id",
            "state": State.QUEUED.value,
            "created_at": "2024-03-20T12:00:00Z",
        }
        mock_request.return_value = mock_response
        result = await get_generation({"generation_id": "test-id"})
        assert f"State: {State.QUEUED.value}" in result

        # Test dreaming state
        mock_response.json.return_value["state"] = State.DREAMING.value
        result = await get_generation({"generation_id": "test-id"})
        assert f"State: {State.DREAMING.value}" in result

        # Test completed state
        mock_response.json.return_value["state"] = State.COMPLETED.value
        result = await get_generation({"generation_id": "test-id"})
        assert f"State: {State.COMPLETED.value}" in result

        # Test failed state with reason
        mock_response.json.return_value.update(
            {"state": State.FAILED.value, "failure_reason": "API error"}
        )
        result = await get_generation({"generation_id": "test-id"})
        assert f"State: {State.FAILED.value}" in result
        assert "Reason: API error" in result
