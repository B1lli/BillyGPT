# coding=utf-8
import openai
from api_key_store import read_api_key



openai.api_key = read_api_key()

# 字符转码
import re
def decode_chr(s):
    pattern = re.compile(r'(\\u[0-9a-fA-F]{4}|\n)')
    result = ''
    pos = 0
    while True:
        match = pattern.search(s, pos)
        if match is None:
            break
        result += s[pos:match.start()]
        if match.group() == '\n':
            result += '\n'
        else:
            result += chr(int(match.group()[2:], 16))
        pos = match.end()
    result += s[pos:]
    return result


def prompt_composition_analysis(initial_prompt=None) :
    composition_analysis_message = [{"role" : "user",
                "content" : '''你要伪装成一个提示词分析器，一步一步来。
                首先，你的功能是将接下来看到的提示进行归类:你要判断该提示词是否属于提问或者要求.
                然后，如果是提问或者要求：你只需分析该类型提问或要求一般由哪些部分组成，然后回答即可。
                从现在开始，对每个你看到的提示进行分析：'''}]
    composition_analysis_message.append ( {"role" : "user",
                      "content" : f"{initial_prompt}"} )
    chatGPT_raw_response = openai.ChatCompletion.create (
        model="gpt-3.5-turbo",
        messages=composition_analysis_message
    )
    composition_analysis_result = decode_chr ( chatGPT_raw_response.choices[0].message['content'].strip () )
    composition_analysis_success_message = []
    composition_analysis_success_message.append ( {"role" : "user",
                      "content" : f"{initial_prompt}"} )
    composition_analysis_success_message.append ( {"role" : "assistant",
               "content" : f"{composition_analysis_result}"} )
    return composition_analysis_success_message


def composition_stepped_reply(composition_analysis_message = None, user_prompt = None):
    if user_prompt:
        user_message = {"role" : "user","content" : f"{user_prompt}"}
        composition_analysis_message.append( user_message )
    stepped_reply_message = {"role" : "user","content" : "根据以上分析中提及的每一部分，一步一步来，给出尽可能详细的回答"}
    composition_analysis_message.append ( stepped_reply_message )
    stepped_reply_message = composition_analysis_message
    chatGPT_raw_response = openai.ChatCompletion.create (
        model="gpt-3.5-turbo",
        messages=stepped_reply_message
    )
    return chatGPT_raw_response
