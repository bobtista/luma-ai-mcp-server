# Luma AI MCP Server 🎥

A Model Context Protocol server for Luma AI's video generation capabilities.

## Overview

This MCP server integrates with Luma AI's API to provide tools for generating, managing, and manipulating AI-generated videos and images via Large Language Models. It implements the Model Context Protocol (MCP) to enable seamless interaction between AI assistants and Luma's creative tools.

## Features ✨

- Text-to-video generation
- Advanced video generation with keyframes
- Image-to-video conversion
- Video extension and interpolation
- Image generation
- Audio addition to videos
- Video upscaling
- Credit management
- Generation tracking and status checking

## Tools 🛠️

1. `ping`

   - Check if the Luma API is running
   - No parameters required

2. `create_generation`

   - Creates a new video generation
   - Input:
     - `prompt` (string, required): Text description of the video to generate
     - `model` (string, optional): Model to use (default: "ray-2")
     - `resolution` (string, optional): Video resolution (choices: "540p", "720p", "1080p", "4k")
     - `duration` (string, optional): Video duration (only "5s" and "9s" are currently supported by the API)
     - `aspect_ratio` (string, optional): Video aspect ratio (e.g., "16:9")
     - `loop` (boolean, optional): Whether to make the video loop
     - `keyframes` (object, optional): Start and end frames for advanced video generation:
       - `frame0` and/or `frame1` with either:
         - `{"type": "image", "url": "image_url"}` for image keyframes
         - `{"type": "generation", "id": "generation_id"}` for video keyframes

3. `get_generation`

   - Gets the status of a generation
   - Input:
     - `generation_id` (string, required): ID of the generation to check

4. `list_generations`

   - Lists all generations
   - Input:
     - `limit` (number, optional): Maximum number of generations to return (default: 10)
     - `offset` (number, optional): Number of generations to skip

5. `delete_generation`

   - Deletes a generation
   - Input:
     - `generation_id` (string, required): ID of the generation to delete

6. `upscale_generation`

   - Upscales a video generation to higher resolution
   - Input:
     - `generation_id` (string, required): ID of the generation to upscale
     - `resolution` (string, required): Target resolution for the upscaled video (one of "540p", "720p", "1080p", or "4k")
   - Note:
     - The generation must be in a completed state to be upscaled
     - The target resolution must be higher than the original generation's resolution
     - Each generation can only be upscaled once

7. `add_audio`

   - Adds AI-generated audio to a video generation
   - Input:
     - `generation_id` (required): The ID of the generation to add audio to
     - `prompt` (required): The prompt for the audio generation
     - `negative_prompt` (optional): The negative prompt for the audio generation
     - `callback_url` (optional): URL to notify when the audio processing is complete
   - Output:
     Information about the generation with audio being added

8. `generate_image`

   - Generates an image from a text prompt
   - Input:
     - `prompt` (string, required): Text description of the image to generate
     - `model` (string, optional): Model to use for image generation (default: "photon-1")
       - Note: Only "photon-1" and "photon-flash-1" are supported for image generation

9. `get_credits`

   - Gets credit information for the current user
   - No parameters required

10. `get_camera_motions`
    - Gets all supported camera motions
    - No parameters required
    - Returns: List of available camera motion strings

## Installation

### Using uv (recommended)

When using uv no specific installation is needed. We will use uvx to directly run _luma-ai-mcp-server_.

Alternatively, you can install the package with uv:

```bash
uv pip install luma-ai-mcp-server
```

### Using PIP

Alternatively you can install `luma-ai-mcp-server` via pip:

```bash
pip install luma-ai-mcp-server
```

After installation, you can run it as a script using:

```bash
python -m luma-ai-mcp-server
```

## Configuration

### Usage with Claude Desktop

Add this to your `claude_desktop_config.json`:

#### Using uvx

```json
"mcpServers": {
  "luma": {
    "command": "uvx",
    "args": ["luma-ai-mcp-server"]
  }
}
```

#### Using Local Development with Virtual Environment

For the most reliable setup with Claude Desktop, you can use a virtual environment with direct API key configuration:

1. Clone the repository:

   ```bash
   git clone https://github.com/bobtista/luma-ai-mcp-server.git
   cd luma-ai-mcp-server
   ```

2. Create a virtual environment and install dependencies:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e .
   ```

3. Add this to your Claude Desktop configuration (usually at `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

   ```json
   "mcpServers": {
     "luma": {
       "command": "/absolute/path/to/luma-ai-mcp-server/venv/bin/python",
       "args": ["-m", "luma_ai_mcp_server"],
       "env": {
         "LUMA_API_KEY": "your-luma-api-key-here"
       }
     }
   }
   ```

   Make sure to replace `/absolute/path/to/luma-ai-mcp-server` with the actual path to your repository and `your-luma-api-key-here` with your actual Luma API key.

4. Restart Claude Desktop to apply the changes.

#### Using Local Development

If you're developing locally and haven't published the package yet:

1. Clone the repository:

   ```bash
   git clone https://github.com/bobtista/luma-ai-mcp-server.git
   cd luma-ai-mcp-server
   ```

2. Create a virtual environment and install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e .
   ```

   Or if you're using uv:

   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -e .
   ```

3. If you need to clean and reinstall the package with uv:

   ```bash
   # Remove the current installation
   uv pip uninstall luma-ai-mcp-server

   # Clean build artifacts
   rm -rf build/ dist/ *.egg-info/

   # Reinstall in development mode
   uv pip install -e .
   ```

4. Create a `.env` file with your Luma API key:

   ```bash
   echo "LUMA_API_KEY=your_luma_api_key_here" > .env
   ```

5. Configure Claude Desktop:
   ```json
   "mcpServers": {
     "luma": {
       "command": "python",
       "args": ["-m", "luma-ai-mcp-server"],
       "cwd": "/path/to/your/luma-ai-mcp-server"
     }
   }
   ```

Make sure to replace `/path/to/your/luma-ai-mcp-server` with the actual path to your local repository and `your_luma_api_key_here` with your actual Luma API key.

#### Using docker

```json
"mcpServers": {
  "luma": {
    "command": "docker",
    "args": ["run", "--rm", "-i", "--env-file", ".env", "mcp/luma"]
  }
}
```

### Usage with Zed

Add to your Zed settings.json:

#### Using uvx

```json
"context_servers": [
  "luma-ai-mcp-server": {
    "command": {
      "path": "uvx",
      "args": ["luma-ai-mcp-server"]
    }
  }
],
```

#### Using Local Development

If you're developing locally and haven't published the package yet:

```json
"context_servers": {
  "luma-ai-mcp-server": {
    "command": {
      "path": "python",
      "args": ["-m", "luma-ai-mcp-server"],
      "cwd": "/path/to/your/luma-ai-mcp-server"
    }
  }
},
```

Make sure to replace `/path/to/your/luma-ai-mcp-server` with the actual path to your local repository.

#### Using pip installation

```json
"context_servers": {
  "luma-ai-mcp-server": {
    "command": {
      "path": "python",
      "args": ["-m", "luma-ai-mcp-server"]
    }
  }
},
```

## Advanced Video Generation Types 🎬

The Luma API supports various types of advanced video generation through keyframes:

1. **Starting from an image**: Provide `frame0` with `type: "image"` and an image URL
2. **Ending with an image**: Provide `frame1` with `type: "image"` and an image URL
3. **Extending a video**: Provide `frame0` with `type: "generation"` and a generation ID
4. **Reverse extending a video**: Provide `frame1` with `type: "generation"` and a generation ID
5. **Interpolating between videos**: Provide both `frame0` and `frame1` with `type: "generation"` and generation IDs

## API Limitations and Notes 📝

- **Duration**: Currently, the Luma API only supports durations of "5s" or "9s"
- **Resolution**: Valid values are "540p", "720p", "1080p", and "4k"
- **Models**:
  - Video generation: "ray-2" (default)
  - Image generation: "photon-1" (default) or "photon-flash-1"
- **Generation types**: Video, image, and advanced (with keyframes)
- **Upscaling**:
  - Video generations can only be upscaled when they're in a "complete" state
  - Target resolution must be higher than the original generation's resolution
  - Each generation can only be upscaled once
- **API Key**: Required in environment variables or passed as an argument

## Debugging

You can use the MCP inspector to debug the server. For uvx installations:

```bash
npx @modelcontextprotocol/inspector uvx luma-ai-mcp-server
```

Or if you've installed the package in a specific directory or are developing on it:

```bash
cd path/to/luma-ai-mcp-server
npx @modelcontextprotocol/inspector uv run luma-ai-mcp-server
```

For direct local development, you can run the module directly with uv:

```bash
cd path/to/luma-ai-mcp-server
uv run -m luma-ai-mcp-server
```

Running `tail -n 20 -f ~/Library/Logs/Claude/mcp*.log` will show the logs from the server and may help you debug any issues.

## Development

If you are doing local development, there are two ways to test your changes:

1. Run the MCP inspector to test your changes. See Debugging for run instructions.
2. Test using the Claude desktop app. Add the following to your `claude_desktop_config.json`:

#### Using Docker

```json
{
  "mcpServers": {
    "luma": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "--env-file", ".env", "mcp/luma"]
    }
  }
}
```

#### Using UVX

```json
{
  "mcpServers": {
    "luma": {
      "command": "uv",
      "args": [
        "--directory",
        "/<path to repo>/luma-ai-mcp-server",
        "run",
        "luma-ai-mcp-server"
      ]
    }
  }
}
```

## Build

Docker build:

```bash
cd luma-ai-mcp-server
docker build -t mcp/luma .
```

## Environment Variables 🔐

- `LUMA_API_KEY`: Your Luma AI API key (required)

Create a `.env` file in your project directory with the following content:

```
LUMA_API_KEY=your_luma_api_key_here
```

You can obtain a Luma API key from the [Luma AI website](https://lumalabs.ai). Sign up or log in, then navigate to your account settings to find or generate your API key.

## License 📄

MIT
