import os
from typing import (
    Literal,
    Optional,
    Tuple,
    Union,
)

from aws_lambda_powertools.metrics import MetricUnit
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from files_api.utils import metrics, logger

SYSTEM_PROMPT = "You are an autocompletion tool that produces text files given constraints."


def get_openai_client() -> AsyncOpenAI:
    # point to a local mock of OpenAI, se these env vars in your .env file while testing
    # base_url="http://localhost:1080", api_key="mocked_key"
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
    
    metrics.add_metric(name="OpenAITokensUsage", unit=MetricUnit.Count, value=response.usage.total_tokens)
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
