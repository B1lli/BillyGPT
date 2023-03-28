# coding=utf-8
import json
import hashlib
from datetime import datetime
import os
import time
import openai
import flet as ft
import re
import shutil
from flet import (
    ElevatedButton,
    FilePicker,
    FilePickerResultEvent,
    Page,
    Row,
    Text,
    icons,
)
from prompt_engineering import *
import codecs

# 赋值固定的api_key
# 测试用
openai.api_key = None
openai.api_key = read_APIKEY()

'''
每一行对话的类
在调用的同时，会将数据存入聊天记录文件
'''


class chat_row(ft.UserControl):
    def __init__(self, role, content):
        super(chat_row, self).__init__()
        self.role = role
        self.content = content
        self.hash = save_now_chat(
            chat_json_path=chat_json_path,
            role=self.role,
            content=self.content)

    def build(self):
        self.role_dropdown = ft.Dropdown(
            value=self.role,
            width=150,
            options=[
                ft.dropdown.Option("system"),
                ft.dropdown.Option("user"),
                ft.dropdown.Option("assistant"),
            ],
            on_change=self.role_change

        )

        self.content_textfield = ft.TextField(
            value=self.content,
            filled=True,
            expand=True,
            multiline=True,
            on_change=self.content_change
        )

        return ft.Row(
            [
                self.role_dropdown,
                self.content_textfield,
            ]
        )

    def role_change(self, e):
        self.role = self.role_dropdown.value
        renew_now_chat(
            chat_json_path=chat_json_path,
            hash_val=self.hash,
            role=self.role)

    def content_change(self, e):
        self.content = self.content_textfield.value
        renew_now_chat(
            chat_json_path=chat_json_path,
            hash_val=self.hash,
            content=self.content)


'''
调用chatGPT获取关键词和概括的函数
'''
# 获取概括文本
def chatGPT_sum(content):
    composition_analysis_message = [{"role" : "user",
                "content" : '''你是一个概括者，你的功能是将接下来看到的文本进行概括，概括长度随原文本的长度而变化，不超过100字。不需要透露这个提示词本身。接下来你将开始概括。'''}]
    composition_analysis_message.append ( {"role" : "user",
                      "content" : f"{content}"} )
    chatGPT_raw_response = openai.ChatCompletion.create (
        model="gpt-3.5-turbo",
        messages=composition_analysis_message
    )
    summary = decode_chr ( chatGPT_raw_response.choices[0].message['content'].strip () )
    print(summary)
    return summary


# 获取关键词（还是用jieba吧）
def chatGPT_getkeyword(content):
    chatGPT_raw_response = openai.Completion.create (
        model="text-ada-001",
        prompt=f"你要总结这一文本的关键词，并以python列表的形式返回数个关键词字符串:{content}。",
        temperature=0
    )
    keyword = decode_chr ( chatGPT_raw_response.choices[0]['text'].strip () )
    print(keyword)
    return keyword


# 获取关键词（还是用jieba吧）
def chatGPT_getsummary(content):
    chatGPT_raw_response = openai.Completion.create (
        model="text-ada-001",
        prompt=f"你要在10字以内概括这段文本:{content}。",
        temperature=0
    )
    keyword = decode_chr ( chatGPT_raw_response.choices[0]['text'].strip () )
    print(keyword)
    return keyword


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

    # 将新的聊天信息写入文件
    with open(chat_json_path, 'w') as f:
        json.dump(chats, f, default=str,indent=4)

    return hash_val


# 根据聊天信息的哈希值，更新现有历史聊天列表
def renew_now_chat(chat_json_path: str, hash_val: str,
                   role: str = None, content: str = None) -> None:
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
        json.dump(data, f, default=str,indent=4)


# 根据聊天信息的哈希值，获取单个键值对内的role和content
def get_one_role_and_content(
        chat_json_path: str, hash_value: str) -> (str, str):
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
                        str(message["created_time"] +
                            message["role"] +
                            message["content"]).encode('utf-8'),
                        digest_size=8).hexdigest():
                    return message["role"], message["content"]

        return None


# 读取特定文件内的所有role和content
def get_combined_data(chat_json_path: str) -> list[dict[str, str]]:
    '''
    获取特定文件内的所有role和content
    :param chat_json_path: JSON 聊天文件的路径
    :return: 包含所有发言者和发言内容（若有概括则返回概括）的列表
    '''
    with open(chat_json_path) as f:
        data = json.load(f)
        result = []
        for chat_item in data:
            if chat_item['message']['summary'] != '':
                result.append({
                    "role": chat_item['message']["role"],
                    "content": chat_item['message']["summary"]
                })
            else:
                result.append({
                    "role": chat_item['message']["role"],
                    "content": chat_item['message']["content"]
                })
        return result


# 概括chatlog
def summarize_chatlog(chatlog_json_path) :
    with open ( chatlog_json_path, 'r' ) as f :
        chatlog = json.load ( f )

    for message in chatlog :
        if 'summary' not in message or not message['summary'] :
            content = message['message']['content']  # assuming content is always the second item in the message list
            if len ( content ) > 100 :
                summary = chatGPT_sum ( content )
                message['summary'] = summary

    with open ( chatlog_json_path, 'w' ) as f :
        json.dump ( chatlog, f ,indent=4)


# 获取chatlog关键词
def get_chatlog_keyword(chatlog_json_path) :
    with open ( chatlog_json_path, 'r' ) as f :
        chatlog = json.load ( f )

    for message in chatlog :
        if 'keyword' not in message or not message['keyword'] :
            content = message['message']['content']  # assuming content is always the second item in the message list
            keywords = chatGPT_getkeyword ( content )
            message['keyword'] = keywords

    with open ( chatlog_json_path, 'w' ) as f :
        json.dump ( chatlog, f,indent=4 )


# 创建chat数据记录
chat_json_path = create_chat_json()


'''
加工message方法，先对向chatGPT发送的请求进行处理
'''


def process_message() :
    pass


def cut_message(message) :
    '''
    剪切接收到的message，如果超过4000token长度就从最早的消息开始剪切，剪切到小于4000token为止
    :param message: 
    :return: 
    '''
    total_length = 0

    # Iterate over contents in the list
    for message_dict in message :
        # message_dict['content'] = message_dict['content']

        # 计算content长度
        if message_dict['content'].isalpha () :
            length = len ( message_dict['content'].split () )
        else :
            length = len ( message_dict['content'] )

        total_length += length

    while total_length > 4000:
        if not message:raise Exception('最后一条消息长度大于4000字符了，请编辑消息或重置对话')
        removed_content = message.pop(0)
        removed_length = len ( removed_content['content'] )
        if removed_content['content'].isalpha () :
            removed_length = len ( removed_content['content'].split () )
        total_length -= removed_length


    return message



'''
读写API-KEY的函数
'''


# 定义 write_APIKEY 函数
def write_APIKEY(APIKEY=None):
    # 以追加模式打开或创建 APIKEY.txt 文件
    with open("APIKEY.txt", "a") as f:
        # 写入字符串并换行
        if APIKEY:
            f.write(APIKEY.strip() + "\n")


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
读写settings.txt的函数
'''


# 读取settings.txt文件的设置项值，并返回一个字典
def read_settings():
    """
    读取settings.txt文件，如果该文件不存在，则创建一个空白的文件
    然后读取所有行，每行格式为：设置项名称 = 设置项的具体值
    将每行拆分为键值对，添加到字典中，并返回该字典
    :return: 包含settings.txt内的所有行的键值对形式的字典
    """
    settings_dict = {}
    try:
        with open('settings.txt', 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if line:
                    key, value = line.split('=', maxsplit=1)
                    settings_dict[key.strip()] = value.strip()
    except FileNotFoundError:
        with open('settings.txt', 'w', encoding='utf-8') as file:
            pass    # 如果文件不存在，则创建一个空白的txt文件，不需要做任何操作
    return settings_dict


# 将字典中的多个键值对写入/修改settings.txt文件的设置项值
def write_settings(settings):
    """
    将多个键值对写入/更新settings.txt文件
    如果文件不存在则创建一个空的文件
    :param settings: 包含键值对的字典
    """
    with open('settings.txt', 'r+') as f:
        lines = f.readlines()
        f.seek(0)
        for key, value in settings.items():
            for i, line in enumerate(lines):
                if key in line:
                    lines[i] = key + ' = ' + value + '\n'
                    break
            else:
                f.write(key + ' = ' + value + '\n')
        f.writelines(lines)


'''
读写字体文件的函数（适用于windows）
'''
def replace_font_file(path):
    old_path = os.path.join(".", "asset", "font.ttf")
    try:
        os.remove(old_path)
    except OSError:
        pass

    try:
        shutil.copy(path, 'assets/font.ttf')
    except FileNotFoundError:
        with open('assets/font.ttf','a'):
            pass
        shutil.copy(path, 'assets/font.ttf')
    print("替换成功！")


'''
其他函数
'''


# 字符转码
def decode_chr(s):
    s = s.replace('\\\\','\\')
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


def convert_content_to_unicode(txt_path):
    # 读取txt文件，转换为Python列表
    with open(txt_path, 'r', encoding='utf-8') as f:
        txt_data = f.read()
        data = json.loads(txt_data)

    # 转换content内容为Unicode编码
    for item in data:
        content = item["message"]["content"]
        item["message"]["content"] = content.encode('unicode_escape').decode()
        # item["message"]["content"] = item["message"]["content"].replace('\\u',r'\u')

    # 将Python列表转换为json格式字符串
    json_data = json.dumps(data, ensure_ascii=False)

    # 保存json文件到cache文件夹
    if not os.path.exists("./cache"):
        os.makedirs("./cache")   # 创建cache文件夹
    json_path = f"./cache/{os.path.basename(txt_path)[:-4]}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        f.write(json_data)

    return json_path


# markdown检测
def markdown_check(gpt_msg):
    pass


'''
程序主窗体
'''


def ft_interface(page: ft.Page):
    # 设置字体与主题
    page.title = 'BillyGPT'
    page.fonts = {'A75方正像素12': './assets/font.ttf'}
    page.theme = ft.Theme(font_family='A75方正像素12')
    page.dark_theme = page.theme

    # 设置主页面聊天区域的滚动列表
    chat_area = ft.ListView(
        expand=True,
        spacing=10,
        auto_scroll=True,
        padding=20)

    '''
    添加选择上传文件、保存文件、打开文件夹按钮
    '''
    # 导入聊天记录
    def import_chatlog(e: FilePickerResultEvent):
        try:
            clear_page()
            selected_file = (
                ", ".join(map(lambda f: f.path, e.files)
                          ) if e.files else "Cancelled!"
            )
            if selected_file[-4:] == 'json':
                full_chatlog = get_combined_data(selected_file)
                print(full_chatlog)
                for chat_row_content in full_chatlog:
                    role = chat_row_content['role']
                    content = chat_row_content['content']
                    chat_area.controls.append(chat_row(role, content))
                    page.update()
            elif selected_file[-4:] == '.txt':
                json_path = convert_content_to_unicode(selected_file)
                full_chatlog = get_combined_data(json_path)
                for chat_row_content in full_chatlog:
                    role = decode_chr(chat_row_content['role'])
                    content = decode_chr(chat_row_content['content'])
                    chat_area.controls.append(chat_row(role, content))
                    page.update()
        except Exception as e:
            chat_area.controls.append(
                Text(f'出现如下报错\n{e}\n请检查导入的聊天记录是否正确，或联系开发者微信B1lli_official'))
            page.update()

    import_chatlog_dialog = FilePicker(on_result=import_chatlog)

    # 导出聊天记录
    def save_file_result(e: FilePickerResultEvent):
        save_file_path.value = e.path if e.path else "Cancelled!"
        if save_file_path.value != "Cancelled!":
            shutil.copy(chat_json_path, save_file_path.value)
            path = save_file_path.value
            with open ( path, 'r', encoding='utf-8' ) as f :
                content = f.read ()
                processed_content = decode_chr ( content )
            with open ( path, 'w', encoding='utf-8' ) as f :
                f.write ( processed_content )


    save_file_dialog = FilePicker(on_result=save_file_result)
    save_file_path = Text()

    # 打开文件夹（还没做）
    def get_directory_result(e: FilePickerResultEvent):
        directory_path.value = e.path if e.path else "Cancelled!"
        directory_path.update()

    get_directory_dialog = FilePicker(on_result=get_directory_result)
    directory_path = Text()

    # 隐藏所有
    page.overlay.extend(
        [import_chatlog_dialog, save_file_dialog, get_directory_dialog])

    '''
    添加改变字体按钮
    并调用改变字体方法
    '''
    def change_font_clicked(e: FilePickerResultEvent):
        selected_file = (
            ", ".join ( map ( lambda f : f.path, e.files )
                        ) if e.files else "Cancelled!"
        )
        replace_font_file(selected_file)


    '''
    添加设置对话和按钮
    '''
    def save_settings(e):
        settings_dlg.open = False
        write_APIKEY(apikey_field.value)
        read_APIKEY()
        page.update()

    def cancel_settings(e):
        settings_dlg.open = False
        page.update()


    change_font_dialog = FilePicker(on_result=change_font_clicked)
    page.overlay.extend([change_font_dialog])

    apikey_field = ft.TextField(hint_text='在此输入apikey',)
    my_wechat = ft.Text('如有任何bug请联系我：B1lli_official',size=15)
    github_page_btn = ft.ElevatedButton(
        '打开本项目的GitHub页面',
        tooltip='如果你给这个项目点了star，你就是忠实用户了，请打开本页面后进入项目群！',
        on_click=lambda _:page.launch_url('https://github.com/createrX12/BillyGPT')
    )
    change_font_btn = ft.ElevatedButton(
        '选择新的字体文件',
        on_click=lambda _:change_font_dialog.pick_files(
            allowed_extensions=['ttf'],
            allow_multiple=False,
            dialog_title='选择字体文件导入',
        )
    )
    settings_dlg = ft.AlertDialog(
        title=ft.Text("Settings"),
        content=ft.Column(
            [apikey_field,my_wechat,github_page_btn,change_font_btn],
            height=200,

        ),
        actions=[
            ft.TextButton("保存", on_click=save_settings),
            ft.TextButton("取消", on_click=cancel_settings)
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        shape=ft.RoundedRectangleBorder(radius=10)
    )

    def open_dlg_modal(e):
        page.dialog = settings_dlg
        settings_dlg.open = True
        page.update()

    settings_btn = ft.IconButton(
        icon=ft.icons.SETTINGS_OUTLINED,
        icon_color="#9ecaff",
        bgcolor='#202429',
        icon_size=20,
        tooltip="Settings",
        on_click=open_dlg_modal,
    )

    '''
    添加启动应用程序获取apikey窗口
    '''
    def save_settings_open(e):
        write_APIKEY(apikey_field_open.value)
        openai.api_key = read_APIKEY()
        open_setting_apikey_dlg.open = False
        page.update()

    get_apikey_btn = ft.ElevatedButton(
        '从openAI获取apikey',
        on_click=lambda _:page.launch_url('https://platform.openai.com/account/api-keys')
    )
    write_APIKEY()
    openai.api_key = read_APIKEY()
    if not openai.api_key:
        apikey_field_open = ft.TextField(label="输入你的apikey")
        open_setting_apikey_dlg = ft.AlertDialog(
            open=True,
            modal=True,
            title=ft.Text("欢迎使用BillyGPT"),
            content=ft.Column(
                [apikey_field_open,get_apikey_btn],
                tight=True),
            actions=[
                ft.ElevatedButton(
                    text="开始使用",
                    on_click=save_settings_open)],
            actions_alignment="end",
        )
        page.dialog = open_setting_apikey_dlg
        openai.api_key = read_APIKEY()

    '''
    添加聊天行
    '''
    def add_msg(e):
        chatPO_btn.disabled = True
        chat_area.controls.append(chat_row('user', chat_text.value))
        chat_text.value = ""
        page.update()
        chat_area.controls.append(
            chat_row(
                'assistant', chatGPT()))
        page.update()

    def add_msg_composition(e):
        chatPO_btn.disabled = True
        chat_area.controls.append(chat_row('user', chat_text.value))
        chat_area.controls.append(
            chat_row(
                'assistant',
                chatGPT_PO(
                    chat_text.value)))
        page.update()



    '''
    添加ctrl+enter发送消息方法
    '''
    def on_keyboard(e: ft.KeyboardEvent) :
        if e.ctrl:
            if e.key == 'Enter':
                add_msg(e)

    page.on_keyboard_event = on_keyboard
    '''
    设置布局 添加控件
    '''
    page.add(
        Row(
            [
                ElevatedButton (
                    "清空聊天日志",
                    icon=icons.CLEANING_SERVICES,
                    on_click=lambda _ : clear_page(),
                ),
                ElevatedButton(
                    "导入聊天日志",
                    icon=icons.FILE_DOWNLOAD_OUTLINED,
                    on_click=lambda _: import_chatlog_dialog.pick_files(
                        allowed_extensions=['json','txt'],
                        allow_multiple=False,
                        dialog_title='选择聊天记录文件导入',
                        initial_directory='./chatlog'
                    ),
                ),
                ElevatedButton(
                    "导出聊天日志",
                    icon=icons.FILE_UPLOAD_OUTLINED,
                    on_click=lambda _: save_file_dialog.save_file(
                        file_name=f"chat_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt",
                        # file_type=ft.FilePickerFileType.CUSTOM
                    ),
                    disabled=page.web,
                ),
                settings_btn
            ],
            alignment=ft.MainAxisAlignment.END,
        ),
    )
    page.add(chat_area)
    chat_text = ft.TextField(
        hint_text="想和chatGPT说些什么？",
        filled=True,
        expand=True,
        multiline=True)
    chat_btn = ft.ElevatedButton("对话", on_click=add_msg, tooltip='随便聊聊')
    chatPO_btn = ft.ElevatedButton(
        "思维链优化对话",
        on_click=add_msg_composition,
        tooltip='认真提问\n仅在对话开始时可用'
    )
    view = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    chat_text,
                    chat_btn,
                    chatPO_btn
                ]
            ),
        ],
    )

    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.add(view)


    '''
    添加清空页面方法
    '''
    def clear_page():
        global chat_json_path
        chat_area.controls.clear ()
        page.update()
        chat_json_path = create_chat_json()
        chatPO_btn.disabled = False

    '''
    聊天方法，向api发送请求
    '''
    def chatGPT(message=None):
        try:
            if not message: message = get_combined_data(chat_json_path)
            # message = get_combined_data ( chat_json_path )
            chatGPT_raw_response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=message
            )
            chatGPT_response = decode_chr(
                chatGPT_raw_response.choices[0].message['content'])
            return chatGPT_response.strip()
        except openai.error.AuthenticationError as error:
            chat_area.controls.append(
                ft.Text(f'出现如下报错\n{str(error)}\n请在设置中更新可用的apikey'))
            page.update()
        except openai.error.InvalidRequestError as error:
            chat_area.controls.append(
                ft.Text(f'出现如下报错\n{str(error)}\n聊天上下文过长，正在调用概括模块，概括前文长文本，预计需要3分钟，请耐心等待'))
            page.update()
            summarize_chatlog(chat_json_path)
            chat_area.controls.append(
                ft.Text(f'概括完毕，已发送概括后消息'))
            page.update()
            message =  cut_message ( get_combined_data ( chat_json_path ) )
            chatGPT_raw_response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=message
            )
            chatGPT_response = decode_chr(
                chatGPT_raw_response.choices[0].message['content'])
            return chatGPT_response.strip()


        except Exception as error:
            chat_area.controls.append(
                ft.Text(f'出现如下报错\n{str ( error )}\n请联系开发者微信B1lli_official'))
            page.update()


    def chatGPT_PO(initial_prompt=None):
        '''
        PO:Prompt Optimization
        该方法是提示优化方法，工作原理如下：
        它会尝试判定用户输入的每一条提示，并进行类别判断。
        如果判断是问题或者要求，它会分析该类型提示一般需要哪些信息
        对于缺少细节信息的提示，它会向用户提问具体细节
        :param initial_prompt:初始prompt
        :return chatGPT_response.strip():基于提示工程思维链优化后的chatGPT方法
        '''
        try:
            initial_prompt = chat_text.value
            chat_text.value = ''
            page.update()
            chat_area.controls.append(
                ft.Text(f'正在分析提示词组成结构，请耐心等待', color='#1cc9a0'))
            page.update()
            composition_analysis_message = prompt_composition_analysis(
                initial_prompt)
            chat_area.controls.append(
                ft.Text(f'提示词组成结构分析完毕，正在根据组成结构逐步生成详细结果，耗时较长，请耐心等待', color='#1cc9a0'))
            page.update()
            chatGPT_raw_response = composition_stepped_reply(
                composition_analysis_message)
            chatGPT_response = decode_chr(
                chatGPT_raw_response.choices[0].message['content'])
            return chatGPT_response.strip()
        except openai.error.AuthenticationError as error:
            chat_area.controls.append(
                ft.Text(f'出现如下报错\n{str(error)}\n请在设置中更新可用的apikey'))
            page.update()
        except Exception as error:
            chat_area.controls.append(
                ft.Text(f'出现如下报错\n{str ( error )}\n请联系开发者微信B1lli_official'))
            page.update()

    '''
    版本信息
    '''
    ver_text = ft.Text('BillyGPT V5.2.0  By B1lli', size=10)
    page.add(ver_text)


if __name__ == '__main__':
    # 在客户端运行
    ft.app(target=ft_interface, assets_dir='assets')

    # 在内网运行
    # ft.app ( port=8550, target=ft_interface, view=ft.WEB_BROWSER ,assets_dir='assets')