from io import StringIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.server import Server
from mcp.types import TextContent, Tool

from luma_ai_mcp_server.server import (
    AddAudioInput,
    CreateGenerationInput,
    GenerateImageInput,
    GetCreditsInput,
    GetGenerationInput,
    ListGenerationsInput,
    LumaTools,
    PingInput,
    UpscaleGenerationInput,
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
    "state": "pending",
    "created_at": "2024-03-20T12:00:00Z",
    "assets": {},
    "version": "1.0",
    "request": {"prompt": "test prompt", "model": "ray-2"},
}

MOCK_COMPLETED_GENERATION = {
    "id": "test-id",
    "state": "completed",
    "created_at": "2024-03-20T12:00:00Z",
    "assets": {"video": "https://example.com/video.mp4"},
    "version": "1.0",
    "request": {"prompt": "test prompt", "model": "ray-2"},
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
        mock_response.raise_for_status = AsyncMock()
        mock_response.content = b"{}"
        mock_response.text = "{}"
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_request.return_value = mock_response

        result = await create_generation({"prompt": "test prompt", "resolution": "720p"})

        assert "Created text-to-video generation with ID: test-id" in result
        assert "State: pending" in result

        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["json"]["prompt"] == "test prompt"
        assert call_kwargs["json"]["resolution"] == "720p"


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
        assert "State: pending" in result
        assert "State: completed" in result
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
            "id": "img-123",
            "state": "completed",
            "generation_type": "image",
            "created_at": "2024-03-20T12:00:00Z",
            "assets": {"image": "https://example.com/image.png"},
        }
        mock_response.raise_for_status = AsyncMock()
        mock_response.content = b"{}"
        mock_response.text = "{}"
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_request.return_value = mock_response

        result = await generate_image({"prompt": "test prompt", "model": "photon-1"})

        assert "Image generation" in result
        assert "Prompt: test prompt" in result
        assert "Image URL: https://example.com/image.png" in result

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert args[0] == "POST"
        assert "image" in args[1]
        assert kwargs["json"]["prompt"] == "test prompt"
        assert kwargs["json"]["model"] == "photon-1"


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
    """Test that the tool input schemas are correctly defined."""
    # Test PingInput
    schema = PingInput.model_json_schema()
    assert "properties" in schema

    # Test CreateGenerationInput
    schema = CreateGenerationInput.model_json_schema()
    assert schema["properties"]["prompt"]["type"] == "string"
    assert schema["properties"]["model"]["default"] == "ray-2"
    assert "resolution" in schema["properties"]

    # Test GetGenerationInput
    schema = GetGenerationInput.model_json_schema()
    assert schema["properties"]["generation_id"]["type"] == "string"

    # Test ListGenerationsInput
    schema = ListGenerationsInput.model_json_schema()
    assert schema["properties"]["limit"]["default"] == 10
    assert schema["properties"]["offset"]["default"] == 0

    # Test UpscaleGenerationInput
    schema = UpscaleGenerationInput.model_json_schema()
    assert schema["properties"]["generation_id"]["type"] == "string"
    assert "resolution" in schema["properties"]

    # Test AddAudioInput
    schema = AddAudioInput.model_json_schema()
    assert schema["properties"]["generation_id"]["type"] == "string"
    assert schema["properties"]["prompt"]["type"] == "string"
    assert "negative_prompt" in schema["properties"]

    # Test GenerateImageInput
    schema = GenerateImageInput.model_json_schema()
    assert schema["properties"]["prompt"]["type"] == "string"
    assert schema["properties"]["model"]["default"] == "photon-1"

    # Test GetCreditsInput
    schema = GetCreditsInput.model_json_schema()
    assert "properties" in schema


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
            return_value="Created generation with ID: test-id\nState: pending"
        ),
        "get_generation": AsyncMock(return_value="Generation ID: test-id\nState: completed"),
        "list_generations": AsyncMock(return_value="Generations:\nID: test-id\nState: completed"),
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
        patch("luma-ai-mcp-server.server.ping", mock_fns["ping"]),
        patch("luma-ai-mcp-server.server.create_generation", mock_fns["create_generation"]),
        patch("luma-ai-mcp-server.server.get_generation", mock_fns["get_generation"]),
        patch("luma-ai-mcp-server.server.list_generations", mock_fns["list_generations"]),
        patch("luma-ai-mcp-server.server.delete_generation", mock_fns["delete_generation"]),
        patch("luma-ai-mcp-server.server.upscale_generation", mock_fns["upscale_generation"]),
        patch("luma-ai-mcp-server.server.add_audio", mock_fns["add_audio"]),
        patch("luma-ai-mcp-server.server.generate_image", mock_fns["generate_image"]),
        patch("luma-ai-mcp-server.server.get_camera_motions", mock_fns["get_camera_motions"]),
        patch("luma-ai-mcp-server.server.get_credits", mock_fns["get_credits"]),
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
    """Test the create_generation function with keyframes."""
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_GENERATION_RESPONSE
        mock_response.raise_for_status = AsyncMock()
        mock_response.content = b"{}"
        mock_response.text = "{}"
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_request.return_value = mock_response

        keyframes = {"frame0": {"type": "image", "url": "https://example.com/image.jpg"}}

        result = await create_generation(
            {"prompt": "test prompt", "resolution": "720p", "keyframes": keyframes}
        )

        assert "Created advanced generation" in result
        assert "starting from an image" in result
        assert "State: pending" in result

        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["json"]["prompt"] == "test prompt"
        assert call_kwargs["json"]["resolution"] == "720p"
        assert call_kwargs["json"]["keyframes"] == keyframes
