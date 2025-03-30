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

## Setup for Claude Desktop 🖥️

1. Get your Luma API key from [Luma AI](https://lumalabs.ai) (sign up or log in to get your API key)

2. Add this to your Claude Desktop configuration file:

   - On macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - On Windows: `%APPDATA%\Claude\claude_desktop_config.json`

   ```json
   {
     "mcpServers": {
       "luma": {
         "command": "uv",
         "args": [
           "run",
           "--project",
           "/path/to/your/luma-ai-mcp-server",
           "-m",
           "luma_ai_mcp_server"
         ],
         "env": {
           "LUMA_API_KEY": "your-luma-api-key-here"
         }
       }
     }
   }
   ```

   Replace:

   - `/path/to/your/luma-ai-mcp-server` with the actual path to your server directory
   - `your-luma-api-key-here` with your actual Luma API key

3. Restart Claude Desktop

4. That's it! You can now use Luma AI tools directly in Claude Desktop conversations.

## Quick Troubleshooting 🛠️

If you're having issues:

1. Check your API key is correct
2. Make sure the path to the server is correct
3. View logs with: `tail -n 20 -f ~/Library/Logs/Claude/mcp*.log`

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

## License 📄

MIT
