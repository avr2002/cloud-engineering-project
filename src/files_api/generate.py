import io
import os
import tempfile
from typing import (
    Optional,
    Union,
)

import aiofiles
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


async def generate_text_to_speech(prompt: str, openai_client: Optional[AsyncOpenAI] = None) -> bytes:
    # get the OpenAI client
    client = openai_client or get_openai_client()

    # # Create a temporary file to store the audio
    # with tempfile.NamedTemporaryFile(delete_on_close=False, suffix=".mp3") as temp_file:
    #     temp_audio_file = temp_file.name

    # # get audio response from OpenAI
    # async with client.audio.speech.with_streaming_response.create(
    #     model="tts-1", voice="echo", input=prompt
    # ) as response:
    #     async with aiofiles.open(temp_audio_file, "wb") as f:
    #         async for chunk in response.iter_bytes():
    #             await f.write(chunk)

    # # Read the file content and return as bytes
    # async with aiofiles.open(temp_audio_file, 'rb') as f:
    #     file_content_bytes = await f.read()

    # Create a in-memory audio buffer
    audio_buffer = io.BytesIO()

    # Get audio response from OpenAI and write directly to the in-memory buffer
    async with client.audio.speech.with_streaming_response.create(
        model="tts-1", voice="echo", input=prompt
    ) as response:
        async for chunk in response.iter_bytes():
            audio_buffer.write(chunk)

    # Get the audio content as bytes
    file_content_bytes = audio_buffer.getvalue()

    return file_content_bytes
