import os
import asyncio
import openai

API_KEY = os.environ.get("OPENAI_KEY")
openai.api_key = API_KEY

async def test_openai():
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Привет, проверь работу OpenAI!"}]
        )
        print("Ответ OpenAI:", response.choices[0].message.content)
    except Exception as e:
        print("Ошибка при запросе к OpenAI:", e)

if __name__ == "__main__":
    asyncio.run(test_openai())
