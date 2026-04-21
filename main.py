from keys.projects_api_keys import open_ai_api_key
from prompts.system_prompts import main_system_prompt
from openai import OpenAI
import json
import time
import tools
import os
import sys
import llm_vpn_execution
from logger.logger_file import (log_user_request, log_gpt_request, log_gpt_response, log_tool_call_start,
    log_tool_call_result, log_final_response, log_error, log_session_summary)

main_client = OpenAI(api_key=open_ai_api_key)

def main():
    print("Running LLM Execution...")
    user_message = "Your task is watch the movies from different places on the world, provided in targets folder and write a detailed review for each of them. Please use the following tools to access the movies and gather information. Provide your response in JSON format.\n"
    log_user_request(user_message)
    messages = [
        {"role": "system", "content": main_system_prompt},
        {"role": "user", "content": user_message}
    ]
    model_name = "gpt-4o-mini"
    gpt_response = main_client.chat.completions.create(
        model=model_name,
        messages=messages,
        response_format={"type": "json_object"}
    )
    response_message = gpt_response.choices[0].message.content
    finish_reason = gpt_response.choices[0].finish_reason ### ???
    messages.append(response_message)

    if yt_links_MAYBE_AGNET:
        pass # TO DO
    elif vpn_access_agent:
        llm_vpn_execution.run()
        pass # TO DO
    elif other_tools:
        pass # TO DO
    elif user_asking_for_info:
        pass # TO DO
    else:
        pass # TO DO

    #+ ITERATE UNTIL TASK IS DONE OR MAX ITERATIONS REACHED
    #+ LOG ALL ACTIONS, TOOL CALLS, RESPONSES, ERRORS,
    #+ PROVIDE FINAL RESPONSE IN JSON FORMAT

if __name__ == "__main__":
    main()