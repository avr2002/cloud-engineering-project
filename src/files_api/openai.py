from typing import Union

import aiofiles

# from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

SYSTEM_PROMPT = "You are an autocompletion tool that produces text files given constraints."
# prompt = "toml file representing a setuptools python package"


def get_openai_client() -> AsyncOpenAI:
    # point to a local mock of OpenAI
    client = AsyncOpenAI(base_url="http://localhost:1080", api_key="mocked_key")
    return client


async def get_text_chat_completion(prompt: str) -> str:
    # get the OpenAI client
    client = get_openai_client()

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


async def generate_image(prompt: str) -> Union[str, None]:
    # get the OpenAI client
    client = get_openai_client()

    # get image response from OpenAI
    image_response = await client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )

    return image_response.data[0].url or None


async def generate_text_to_speech(prompt: str, output_file: str):
    # get the OpenAI client
    client = get_openai_client()

    # get audio response from OpenAI
    async with client.audio.speech.with_streaming_response.create(
        model="tts-1", voice="echo", input=prompt
    ) as response:
        async with aiofiles.open(output_file, "wb") as f:
            async for chunk in response.iter_bytes():
                await f.write(chunk)
