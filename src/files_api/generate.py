import os
from typing import (
    Literal,
    Optional,
    Tuple,
    Union,
)

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

SYSTEM_PROMPT = "You are an autocompletion tool that produces text files given constraints."
# prompt = "toml file representing a setuptools python package"


def get_openai_client() -> AsyncOpenAI:
    # point to a local mock of OpenAI
    # if os.getenv("OPENAI_API_KEY") is None:
    #     client = AsyncOpenAI(base_url="http://localhost:1080", api_key="mocked_key")
    #     return client

    base_url = os.getenv("OPENAI_BASE_URL")
    api_key = os.getenv("OPENAI_API_KEY")

    client = AsyncOpenAI(base_url=base_url, api_key=api_key)
    return client


async def get_text_chat_completion(prompt: str, openai_client: Optional[AsyncOpenAI] = None) -> str:
    """Generate a text chat completion from a given prompt."""
    # get the OpenAI client
    client = openai_client or get_openai_client()

    # get the completion
    response: ChatCompletion = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=100,  # avoid burning your credits
        n=1,  # number of responses
    )

    return response.choices[0].message.content or ""


async def generate_image(prompt: str, openai_client: Optional[AsyncOpenAI] = None) -> Union[str, None]:
    """Generate an image from a given prompt."""
    # get the OpenAI client
    client = openai_client or get_openai_client()

    # get image response from OpenAI
    image_response = await client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )

    return image_response.data[0].url or None


async def generate_text_to_speech(
    prompt: str,
    openai_client: Optional[AsyncOpenAI] = None,
    response_format: Literal["mp3", "opus", "aac", "flac", "wav", "pcm"] = "mp3",
) -> Tuple[bytes, str]:
    """
    Generate text-to-speech audio from a given prompt.

    Returns the audio content as bytes and the MIME type as a string.
    """
    # get the OpenAI client
    client = openai_client or get_openai_client()

    # get audio response from OpenAI
    audio_response = await client.audio.speech.with_raw_response.create(
        model="tts-1",
        voice="echo",
        input=prompt,
        response_format=response_format,
    )

    # Get the audio content as bytes
    file_content_bytes: bytes = audio_response.content
    file_mime_type: str = audio_response.headers.get("Content-Type")

    return file_content_bytes, file_mime_type


# import io
# import tempfile
# import aiofiles

# async def generate_text_to_speech_with_memory(prompt: str, openai_client: Optional[AsyncOpenAI] = None) -> bytes:
#     # get the OpenAI client
#     client = openai_client or get_openai_client()

#     # Create a in-memory audio buffer
#     audio_buffer = io.BytesIO()

#     # Get audio response from OpenAI and write directly to the in-memory buffer
#     async with client.audio.speech.with_streaming_response.create(
#         model="tts-1", voice="echo", input=prompt
#     ) as response:
#         async for chunk in response.iter_bytes():
#             audio_buffer.write(chunk)

#     # Get the audio content as bytes
#     file_content_bytes = audio_buffer.getvalue()

#     return file_content_bytes


# async def generate_text_to_speech_with_tempfile(prompt: str, openai_client: Optional[AsyncOpenAI] = None) -> bytes:
#     # get the OpenAI client
#     client = openai_client or get_openai_client()

#     # Create a temporary file to store the audio
#     with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3", dir="/tmp") as temp_file:
#         temp_audio_file = temp_file.name

#     # get audio response from OpenAI
#     async with client.audio.speech.with_streaming_response.create(
#         model="tts-1", voice="echo", input=prompt
#     ) as response:
#         async with aiofiles.open(temp_audio_file, "wb") as f:
#             async for chunk in response.iter_bytes():
#                 await f.write(chunk)

#     # Read the file content and return as bytes
#     async with aiofiles.open(temp_audio_file, "rb") as f:
#         file_content_bytes = await f.read()

#     # Delete the temporary file
#     os.unlink(temp_audio_file)

#     return file_content_bytes
