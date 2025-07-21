# ProtoReel Worker Service

This service processes video generation tasks for ProtoReel. It receives tasks via HTTP API, generates videos using MoviePy and other tools, and notifies the backend API of task status via secure webhooks.

---

## Table of Contents
- [Setup](#setup)
- [Environment Variables](#environment-variables)
- [API Endpoints](#api-endpoints)
- [Webhook Details](#webhook-details)
- [Logging](#logging)
- [Development & Testing](#development--testing)

---

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Set environment variables:**
   - Copy `.env.example` to `.env` and fill in the required values.
3. **Run the worker:**
   ```bash
   uvicorn main_worker:app --host 0.0.0.0 --port 8081
   ```

---

## Environment Variables

| Variable             | Description                                      | Example                        |
|----------------------|--------------------------------------------------|--------------------------------|
| BACKEND_API_URL      | URL of the backend API to notify via webhooks    | https://api.protoreel.com      |
| WORKER_API_KEY       | API key for authenticating with backend webhooks | changeme-worker-key            |
| OPENAI_API_KEY       | API key for image generation (if used)           | sk-...                         |
| R2_BUCKET_NAME       | Cloudflare R2 bucket for video uploads           | my-bucket                      |
| R2_PUBLIC_BASE_URL   | Public base URL for R2 videos                    | https://r2.example.com         |
| ...                  | See `.env.example` for more                      |                                |

---

## API Endpoints

### `POST /process-task`
- **Description:** Receives a video generation task.
- **Request Body:**
  ```json
  {
    "task_id": "string",           // Unique task identifier
    "request_dict": { ... }         // Video generation parameters (scenes, output filename, etc.)
  }
  ```
- **Response:**
  - On success:
    ```json
    { "status": "finished", "result": { "r2_url": "https://..." } }
    ```
  - On failure:
    ```json
    { "status": "failed", "error": "..." }
    ```

### `GET /health`
- **Description:** Health check endpoint (recommended to add for orchestration).
- **Response:**
  ```json
  { "status": "ok" }
  ```

---

## Webhook Details

The worker notifies the backend API of task status changes via secure webhooks. All webhook requests include an `Authorization: Bearer <WORKER_API_KEY>` header.

### 1. `POST /worker/task-started`
- **Description:** Notify backend that a task has started processing.
- **Payload:**
  ```json
  { "task_id": "string" }
  ```

### 2. `POST /worker/task-finished`
- **Description:** Notify backend that a task has finished and provide the video URL.
- **Payload:**
  ```json
  { "task_id": "string", "video_url": "https://..." }
  ```

### 3. `POST /worker/task-failed`
- **Description:** Notify backend that a task has failed.
- **Payload:**
  ```json
  { "task_id": "string", "error": "..." }
  ```

---

## Logging
- All logs are structured as JSON for Google Cloud Logging.
- Each log entry includes a `task_id` field for easy filtering.
- Errors include stack traces for debugging.

---

## Development & Testing
- Run tests in the `tests/` directory with `pytest` or directly with Python.
- Example:
  ```bash
  pytest tests/
  ```
- For local development, you can use the default `.env.example` and override as needed.

---

## Starting a Task: API Payload Details

To start a video generation task, make a `POST` request to `/process-task` with the following payload:

```json
{
  "task_id": "string",         // Unique identifier for this task (required)
  "request_dict": {
    "output_filename": "string",   // Name for the output video file (required)
    "scenes": [                    // List of scenes to generate (required)
      {
        "type": "image",               // Scene type: currently only 'image' is supported (required)
        "image": "string",             // (Optional) URL or path to an image file to use for this scene
        "promptImage": "string",       // (Optional) Text prompt to generate an image (requires OPENAI_API_KEY)
        "video": "string",             // (Optional, not yet implemented) URL/path to a video file for this scene
        "narration": "string",         // (Optional) URL or path to an audio file for narration
        "narration_text": "string",    // (Optional) Text to generate narration audio for this scene
        "music": "string",             // (Optional) URL or path to a music file for background music
        "duration": 10,                // (Required) Duration of the scene in seconds
        "text": {                      // (Optional) Overlay text on the scene
          "content": "string",         // Text content to display
          "position": "center",        // Position of the text (e.g., 'center', 'top', 'bottom')
          "fontsize": 36,              // Font size for the text
          "color": "white"             // Text color
        },
        "subtitle": true               // (Optional) Whether to generate subtitles for narration
      }
    ],
    "narration_text": "string"     // (Optional) If provided, generates a single narration for the whole video and splits duration across scenes
  }
}
```

### Parameter Explanations

#### Top-level
- **task_id**:  
  *Type*: string  
  *Required*: Yes  
  *Description*: Unique identifier for the task. Used for tracking and logging.

- **request_dict**:  
  *Type*: object  
  *Required*: Yes  
  *Description*: Contains all video generation parameters.

#### Inside `request_dict`
- **output_filename**:  
  *Type*: string  
  *Required*: Yes  
  *Description*: The name of the output video file (e.g., `"myvideo.mp4"`).

- **scenes**:  
  *Type*: array of objects  
  *Required*: Yes  
  *Description*: List of scenes to generate. Each scene is an object with the following fields:

##### Scene Object Fields
- **type**:  
  *Type*: string  
  *Required*: Yes  
  *Description*: The type of scene. Currently, only `"image"` is supported.
- **image**:  
  *Type*: string  
  *Required*: No  
  *Description*: URL or path to an image file to use for this scene.
- **promptImage**:  
  *Type*: string  
  *Required*: No  
  *Description*: Text prompt to generate an image using an AI model (requires `OPENAI_API_KEY`).
- **video**:  
  *Type*: string  
  *Required*: No  
  *Description*: URL or path to a video file for this scene. *(Not yet implemented)*
- **narration**:  
  *Type*: string  
  *Required*: No  
  *Description*: URL or path to an audio file for narration.
- **narration_text**:  
  *Type*: string  
  *Required*: No  
  *Description*: Text to generate narration audio for this scene.
- **music**:  
  *Type*: string  
  *Required*: No  
  *Description*: URL or path to a music file for background music.
- **duration**:  
  *Type*: integer  
  *Required*: Yes  
  *Description*: Duration of the scene in seconds.
- **text**:  
  *Type*: object  
  *Required*: No  
  *Description*: Overlay text on the scene.  
    - **content**: string — The text to display  
    - **position**: string — Where to place the text (e.g., `"center"`)  
    - **fontsize**: integer — Font size  
    - **color**: string — Text color
- **subtitle**:  
  *Type*: boolean  
  *Required*: No  
  *Description*: Whether to generate subtitles for narration.

- **narration_text** (in `request_dict`):  
  *Type*: string  
  *Required*: No  
  *Description*: If provided at the top level, generates a single narration for the whole video and splits the duration across all scenes.

### Example Minimal Payload

```json
{
  "task_id": "abc123",
  "request_dict": {
    "output_filename": "myvideo.mp4",
    "scenes": [
      {
        "type": "image",
        "image": "https://example.com/image1.jpg",
        "duration": 10
      }
    ]
  }
}
```

#### Notes
- At least one of `image` or `promptImage` must be provided for each scene.
- If both `narration` and `narration_text` are provided, `narration` (the file) takes precedence.
- If `narration_text` is provided at the top level, it will be used for the whole video and split across scenes.
- All fields not marked as required are optional.

---

## Contact
For support, contact the ProtoReel team. 