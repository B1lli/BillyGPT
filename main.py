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

# 创建对话窗口的类（没做好，还在学怎么做）
class chat_window(ft.UserControl):
    def __init__(self):
        super(chat_window, self).__init__()

    def build(self):
        self.chat_list = ft.ListView ( expand=True, spacing=10, auto_scroll=True, padding=20 )
        self.page.add(self.chat_list)
        self.chat_text = ft.TextField ( hint_text="想和chatGPT说些什么？",filled=True,expand=True,multiline=True )


        return ft.Column(
            controls=[
                self.chat_list,
                ft.Row(
                    controls=[
                        self.chat_text,
                        ft.ElevatedButton ( "对话", on_click=add_msg )
                    ]
                ),
            ],
        )

    def add_msg(self,e) :
        self.chat_list.controls.append ( chat_row ( 'user', self.chat_text.value ) )
        self.chat_text.value = ""
        self.page.update ()
        self.chat_list.controls.append ( chat_row ( 'assistant', self.chat ( chat_text.value ) ) )
        self.page.update ()

    def chat(self,msg = None) :
        try:
            message = get_combined_data(chat_json_path)
            completion = openai.ChatCompletion.create (
                model="gpt-3.5-turbo",
                messages=message
            )
            gpt_msg = completion.choices[0].message['content']
            d_msg = decode_chr ( gpt_msg )
            return d_msg
        except openai.error.RateLimitError as e:
            print(e)
            print( "频率过高，请过一分钟再试，或更换API-KEY" )
            pass
        except Exception as e:
            print( f"出现如下报错：\n{e}，如果无法重新发起对话，请尝试重启程序，或者检查自己的网络环境能否连接到openai的服务器" )
        finally:
            print( d_msg )


'''
读写chatlog的相关函数
'''
# 创建chat数据记录的方法，将聊天数据结构基于 JSON 文件进行存储
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
            json.dump([], f, default=str)
    return chat_json_path


# 储存现有的每一句聊天信息
def save_now_chat(chat_json_path: str, role: str, content: str) -> str:
    '''
    将每一段聊天信息储存到一个 JSON 文件中。以哈希值作为唯一标识符
    :param chat_json_path: 聊天文件的路径
    :param role: 发言者
    :param content: 发言内容
    :return hash_val: 哈希值
    '''
    now = datetime.now().timestamp()
    str_to_hash = str(now) + role + content
    hash_obj = hashlib.blake2b(str_to_hash.encode('utf-8'), digest_size=8)
    hash_val = hash_obj.hexdigest()

    # 读取之前的内容
    try:
        with open(chat_json_path, 'r') as f:
            chats = json.load(f)
    except FileNotFoundError:
        chats = []

    # 添加新的聊天信息
    message = {
        'role': role,
        'content': content,
        'keyword': [],
        'summary': ''
    }
    chats.append({
        'chat_seq': len(chats) + 1,
        'hash': hash_val,
        'created_time': now,
        'altered_time': None,
        'message': message
    })

    # # 更新聊天信息中的关键字和摘要
    # for chat in chats:
    #     keywords = []
    #     for msg in chat['message']:
    #         for word in re.findall(r'\w+', msg['content']):
    #             if len(word) > 1 and word not in keywords:
    #                 keywords.append(word)
    #         msg['keyword'] = keywords
    #         msg['summary'] = '，'.join(keywords[:3]) + '...' if keywords else ''

    # 将新的聊天信息写入文件
    with open(chat_json_path, 'w') as f:
        json.dump(chats, f, default=str)

    return hash_val


# 根据聊天信息的哈希值，更新现有历史聊天列表
def renew_now_chat(chat_json_path: str, hash_val: str, role: str = None, content: str = None) -> None:
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
    for chat_item in data:
        if hash_val == chat_item['hash']:
            if role:
                chat_item['message']['role'] = role
            if content:
                chat_item['message']['content'] = content
            chat_item["altered_time"] = datetime.now().timestamp()
            break

    # 将更新后的数据写回文件
    with open(chat_json_path, 'w') as f:
        json.dump(data, f, default=str)


# 根据聊天信息的哈希值，获取单个键值对内的role和content
def get_one_role_and_content(chat_json_path: str, hash_value: str) -> (str, str):
    '''
    根据聊天信息的哈希值，获取单个键值对内的role和content
    :param chat_json_path: 聊天文件的路径
    :param hash_value: 聊天信息的哈希值
    :return: (发言者, 发言内容)
    '''
    with open(chat_json_path) as f:
        data = json.load(f)

        for chat_item in data:
            for message in chat_item['message']:
                if hash_value == hashlib.blake2b(
                        str(message["created_time"] + message["role"] + message["content"]).encode('utf-8'),
                        digest_size=8).hexdigest():
                    return message["role"], message["content"]

        return None


# 读取特定文件内的所有role和content
def get_combined_data(chat_json_path: str) -> list[dict[str, str]]:
    '''
    获取特定文件内的所有role和content
    :param chat_json_path: JSON 聊天文件的路径
    :return: 包含所有发言者和发言内容的列表
    '''
    with open(chat_json_path) as f:
        data = json.load(f)
        result = []
        for chat_item in data:
            result.append({
                "role": chat_item['message']["role"],
                "content": chat_item['message']["content"]
            })
        return result


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

    # 调用
    def add_msg(e):
        gpt_text.controls.append ( chat_row('user',chat_text.value) )
        chat_text.value = ""
        page.update()
        gpt_text.controls.append(chat_row('assistant',chat(chat_text.value)))
        page.update()

    # 设置布局
    chat_text = ft.TextField ( hint_text="想和chatGPT说些什么？",filled=True,expand=True,multiline=True )
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



    def chat(msg = None) :
        message = get_combined_data(chat_json_path)
        completion = openai.ChatCompletion.create (
            model="gpt-3.5-turbo",
            messages=message
        )
        gpt_msg = completion.choices[0].message['content']
        d_msg = decode_chr ( gpt_msg )
        return d_msg



    # 版本信息
    ver_text = ft.Text('BillyGPT V3.0.0  By B1lli',size=10)
    page.add(ver_text)


if __name__ == '__main__':
    ft.app ( target=ft_interface, assets_dir='assets' )
    # print ( time.time () )







