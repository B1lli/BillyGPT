# coding=utf-8
"""
@author B1lli
@date 2023年03月09日 17:11:42
@File:main.py
"""
import json
import hashlib
from datetime import datetime
import os
import time
import openai
import flet as ft
import re

# 赋值固定的api_key
# 测试用
openai.api_key = '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'


# 创建对话行的类
class chat_row(ft.UserControl) :
    def __init__(self, role, content):
        super(chat_row, self).__init__()
        self.role = role
        self.content = content
        self.hash = save_now_chat(chat_json_path=chat_json_path,role=self.role,content=self.content)


    def build(self) :
        self.role_dropdown =ft.Dropdown (
                    value=self.role,
                    width=150,
                    options=[
                        ft.dropdown.Option ( "system" ),
                        ft.dropdown.Option ( "user" ),
                        ft.dropdown.Option ( "assistant" ),
                    ],
            on_change=self.role_change

                )

        self.content_textfield = ft.TextField (
                    value=self.content,
                    filled=True,
                    expand=True,
                    multiline=True,
            on_change=self.content_change
                )

        return ft.Row (
            [
                self.role_dropdown,
                self.content_textfield,
            ]
        )

    def role_change(self,e):
        self.role = self.role_dropdown.value
        renew_now_chat(chat_json_path=chat_json_path,hash_val=self.hash,role=self.role)


    def content_change(self,e):
        self.content = self.content_textfield.value
        renew_now_chat(chat_json_path=chat_json_path,hash_val=self.hash,content=self.content)








# 设置全局继承文本的列表
global success_lst
success_lst = []


'''
读写chatlog的相关函数
'''
# 储存现有的每一句聊天信息
def save_now_chat(chat_json_path:str,role: str, content: str) -> str :
    '''
    将每一段聊天信息储存到一个 JSON 文件中。以哈希值作为唯一标识符
    :param chat_json_path: 聊天文件的路径
    :param role: 发言者
    :param content: 发言内容
    :return hash_val: 哈希值
    '''
    # 生成哈希值
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    str_to_hash = now + role + content
    hash_obj = hashlib.blake2b(str_to_hash.encode('utf-8'), digest_size=8)
    hash_val = hash_obj.hexdigest()

    # 读取之前的内容
    try:
        with open(chat_json_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}

    # 更新数据并写入文件
    data[hash_val] = [{"role": role}, {"content": content}]
    with open(chat_json_path, 'w') as f:
        json.dump(data, f)
    return hash_val


# 根据聊天信息的哈希值，更新现有历史聊天列表
def renew_now_chat(chat_json_path:str, hash_val:str, role:str=None, content:str=None) -> None:
    '''
    根据聊天信息的哈希值，更新现有历史聊天列表
    :param chat_json_path: 聊天文件的路径
    :param hash_val: 聊天信息的哈希值
    :param role: 更新后的发言者（可选）
    :param content: 更新后的发言内容（可选）
    :return: None
    '''
    # 读取chat_renew_data.json文件
    with open(chat_json_path, 'r') as f:
        data = json.load(f)
    # 找出哈希值相同的键值对，并更新它们的role和content
    if hash_val in data:
        if role:data[hash_val][0]['role'] = role
        if content:data[hash_val][1]['content'] = content

        # 将更新后的数据写回文件
        with open(chat_json_path, 'w') as f:
            json.dump(data, f)

# 根据聊天信息的哈希值，获取单个键值对内的role和content
def get_one_role_and_content(chat_json_path:str, hash_value:str) -> (str,str):
    '''
    根据聊天信息的哈希值，获取单个键值对内的role和content
    :param chat_json_path: 聊天文件的路径
    :param hash_value: 聊天信息的哈希值
    :return: (发言者, 发言内容)
    '''
    with open(chat_json_path) as f:
        data = json.load(f)
        if hash_value in data:
            values = data[hash_value]
            role = values[0]['role']
            content = values[1]['content']
            return role, content
        else:
            return None

# 获取特定文件内的所有role和content
def get_combined_data(chat_json_path:str) -> list[dict[str, str]]:
    '''
    获取特定文件内的所有role和content
    :param chat_json_path: JSON 聊天文件的路径
    :return: 包含所有发言者和发言内容的列表
    '''
    with open( chat_json_path ) as f:
        data = json.load(f)
        combined_data = []
        for key, value in data.items():
            role = value[0]['role']
            content = value[1]['content']
            combined_data.append({"role": role, "content": content})
        return combined_data

# 创建chat数据记录的方法
def create_chat_json(save_path='./chatlog'):
    # 如果保存目录不存在，则创建目录
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    # 获取当前时间并格式化为文件名格式
    now = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    chat_json_name = f"chat_{now}.json"

    # 如果文件不存在，则创建文件
    chat_json_path = os.path.join(save_path, chat_json_name)
    if not os.path.exists(chat_json_path):
        with open(chat_json_path, 'w') as f:
            json.dump({}, f)

    return chat_json_path

# 创建chat数据记录
chat_json_path = create_chat_json ()



'''
读写API-KEY的函数
'''
# 定义 write_APIKEY 函数
def write_APIKEY(APIKEY):
# 以追加模式打开或创建 APIKEY.txt 文件
    with open("APIKEY.txt", "a") as f:
        # 写入字符串并换行
        f.write(APIKEY + "\n")

# 定义 read_APIKEY 函数
def read_APIKEY():
# 以读取模式打开 APIKEY.txt 文件
    with open("APIKEY.txt", "r") as f:
        # 读取所有行并存入列表
        lines = f.readlines()
        # 如果列表不为空，返回最后一行的值，去掉换行符
        if lines:
            return lines[-1].strip()



'''
其他函数
'''
# 字符转码
def decode_chr(s) :
    pattern = re.compile ( r'(\\u[0-9a-fA-F]{4}|\n)' )
    result = ''
    pos = 0
    while True :
        match = pattern.search ( s, pos )
        if match is None :
            break
        result += s[pos :match.start ()]
        if match.group () == '\n' :
            result += '\n'
        else :
            result += chr ( int ( match.group ()[2 :], 16 ) )
        pos = match.end ()
    result += s[pos :]
    return result

# markdown检测
def markdown_check(gpt_msg):
    pass





'''
程序主窗体
'''
def ft_interface(page: ft.Page) :
    # 设置字体与主题
    page.title = 'BillyGPT'
    page.fonts = {'A75方正像素12' : '../assets/font.ttf'}
    page.theme = ft.Theme ( font_family='A75方正像素12' )
    page.dark_theme = page.theme


    # 设置滚动列表
    gpt_text = ft.ListView ( expand=True, spacing=10, auto_scroll=True, padding=20 )
    page.add ( gpt_text )



    # # 构造聊天行
    # def chat_row(character,value):
    #     return ft.Row(
    #         [
    #             ft.Dropdown(
    #                 value=character,
    #                 width=150,
    #                 options=[
    #                     ft.dropdown.Option("system"),
    #                     ft.dropdown.Option("user"),
    #                     ft.dropdown.Option("assistant"),
    #                 ],
    #             ),
    #             ft.TextField(
    #                 value=value,
    #                 filled=True,
    #                 # bgcolor='#1c1c1c',
    #                 expand=True,
    #                 multiline=True
    #             ),
    #         ]
    #     )

    # 按下对话按钮

    # 调用
    def add_msg(e):
        gpt_text.controls.append ( chat_row('user',chat_text.value) )
        chat_text.value = ""
        page.update()
        gpt_text.controls.append(chat_row('assistant',chat2(chat_text.value)))
        page.update()

    # 设置布局
    chat_text = ft.TextField ( hint_text="想和chatGPT说些什么？",filled=True,expand=True )
    view = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    chat_text,
                    ft.ElevatedButton ( "对话", on_click=add_msg )
                ]
            ),
        ],
    )


    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.add(view)



    def chat2(msg = None) :
        global success_lst
        try:
            # msg = [{"role" : "user", "content" : f"{msg}"}]
            # message = [
            #     {"role" : "system",
            #      "content" : '''你是名为Billy的助手'''}
            # ]
            # if success_lst :
            #     success_lst.extend(msg)
            #     message.extend ( success_lst )
            # else:
            #     message.extend(msg)
            message = get_combined_data(chat_json_path)
            completion = openai.ChatCompletion.create (
                model="gpt-3.5-turbo",
                messages=message
            )
            gpt_msg = completion.choices[0].message['content']
            d_msg = decode_chr ( gpt_msg )
            # success_lst.append({"role" : "assistant", "content" : f"{d_msg}"})
            return d_msg

        except openai.error.RateLimitError:
            print( "频率过高，请过一分钟再试，或更换API-KEY" )
            pass
        except Exception as e:
            print( f"出现如下报错：\n{e}，如果无法重新发起对话，请尝试重启程序，或者检查自己的网络环境能否连接到openai的服务器" )
        finally:
            print( success_lst )


    # 版本信息
    ver_text = ft.Text('V2.0.0 有技术问题请咨询qq2508285107',size=10)
    page.add(ver_text)

if __name__ == '__main__':
    ft.app ( target=ft_interface, assets_dir='assets' )








