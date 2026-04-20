from Keys.projects_api_keys import open_ai_api_key
from prompts.system_prompts import gpt_system_prompt
import openai   



def run():
    openai.api_key = open_ai_api_key

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": gpt_system_prompt},
            {"role": "user", "content": "Tell me something about MCP servers and their strategic importance."}
        ]
    )

    print(response['choices'][0]['message']['content'])