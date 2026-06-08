# coding=utf-8
from __future__ import annotations

import json
from datetime import datetime
import os
import openai
import flet as ft
import shutil
from flet import (
    ElevatedButton,
    FilePicker,
    FilePickerResultEvent,
    Page,
    Row,
    Text,
)
from api_key_store import read_api_key, write_api_key
from chat_store import (
    create_chat_json,
    get_combined_data,
    get_one_role_and_content,
    renew_now_chat,
    save_now_chat,
)
from paths import (
    ASSETS_DIR,
    CACHE_DIR,
    CHATLOG_DIR,
    CUSTOM_FONT_PATH,
    SETTINGS_FILE,
)
from prompt_engineering import (
    composition_stepped_reply,
    decode_chr,
    prompt_composition_analysis,
)
import codecs



# 优先从 OPENAI_API_KEY 读取；APIKEY.txt 仅保留给旧版本读取兼容。
openai.api_key = read_api_key()

'''
每一行对话的类
在调用的同时，会将数据存入聊天记录文件
'''


class chat_row(ft.Row):
    def __init__(self, role, content):
        super().__init__()
        self.role = role
        self.content = content
        chat_log_path = ensure_chat_json_path()
        self.hash = save_now_chat(
            chat_json_path=chat_log_path,
            role=self.role,
            content=self.content)

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
            label="Message",
            value=self.content,
            filled=True,
            expand=True,
            multiline=True,
            on_change=self.content_change
        )

        self.generalize_btn = ft.ElevatedButton(
            'Summarize',
            on_click=self.sum_change
        )
        self.sum_field = ft.TextField (
            visible=False,
            label="Summary",
            value='Summarizing',
            filled=True,
            expand=True,
            multiline=True,
            # on_change=self.content_change
        )

        self.controls = [
            self.role_dropdown,
            self.content_textfield,
            self.generalize_btn,
            self.sum_field,
        ]

    def sum_change(self,e):
        self.generalize_btn.disabled = True
        self.update()
        self.summary = chatGPT_sum(self.content)
        renew_now_chat (
            chat_json_path=ensure_chat_json_path(),
            hash_val=self.hash,
            summary=self.summary )
        self.sum_field.visible = True
        self.sum_field.value = self.summary
        self.generalize_btn.disabled = False
        self.update ()

    def role_change(self, e):
        self.role = self.role_dropdown.value
        renew_now_chat(
            chat_json_path=ensure_chat_json_path(),
            hash_val=self.hash,
            role=self.role)

    def content_change(self, e):
        self.content = self.content_textfield.value
        renew_now_chat(
            chat_json_path=ensure_chat_json_path(),
            hash_val=self.hash,
            content=self.content)


'''
调用chatGPT获取关键词和概括的函数
'''
# 文本切块成
def split_text(text, divide_length):
    return [text[i:i+divide_length] for i in range(0, len(text), divide_length)]

# 获取概括文本
def chatGPT_sum_old(content):
    divided_content = split_text(content,divide_length=1000)
    chain_summary = []
    for single_content in divided_content:
        composition_analysis_message = [{"role" : "user",
                    "content" : f'''为以下文本创建概括:


            {single_content}


            概括内容:'''}]
        chatGPT_raw_response = openai.ChatCompletion.create (
            model="gpt-3.5-turbo",
            messages=composition_analysis_message
        )
        summary = decode_chr ( chatGPT_raw_response.choices[0].message['content'].strip () )
        chain_summary.append(summary)

    chain_summary_long = '\n'.join ( chain_summary )
    return chain_summary_long



def chatGPT_sum(content, chain_type='map_reduce'):
    return chatGPT_sum_old(content)



# 获取关键词（还是用jieba吧）
def chatGPT_getkeyword(content):
    chatGPT_raw_response = openai.Completion.create (
        model="text-ada-001",
        prompt=f"你要总结这一文本的关键词，并以python列表的形式返回数个关键词字符串:{content}。",
        temperature=0
    )
    keyword = decode_chr ( chatGPT_raw_response.choices[0]['text'].strip () )
    return keyword


# 获取关键词（还是用jieba吧）
def chatGPT_getsummary(content):
    chatGPT_raw_response = openai.Completion.create (
        model="text-ada-001",
        prompt=f"你要在10字以内概括这段文本:{content}。",
        temperature=0
    )
    keyword = decode_chr ( chatGPT_raw_response.choices[0]['text'].strip () )
    return keyword


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


# 聊天日志只在 UI 启动后创建，避免导入模块时产生文件副作用。
chat_json_path = None


def ensure_chat_json_path():
    global chat_json_path
    if chat_json_path is None:
        chat_json_path = create_chat_json()
    return chat_json_path


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
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if line:
                    key, value = line.split('=', maxsplit=1)
                    settings_dict[key.strip()] = value.strip()
    except FileNotFoundError:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as file:
            pass    # 如果文件不存在，则创建一个空白的txt文件，不需要做任何操作
    return settings_dict


# 将字典中的多个键值对写入/修改settings.txt文件的设置项值
def write_settings(settings):
    """
    将多个键值对写入/更新settings.txt文件
    如果文件不存在则创建一个空的文件
    :param settings: 包含键值对的字典
    """
    existing = read_settings()
    existing.update(settings)
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        for key, value in existing.items():
            f.write(f"{key} = {value}\n")


'''
读写字体文件的函数（适用于windows）
'''
def replace_font_file(path):
    if not path or path == "Cancelled!":
        return
    CUSTOM_FONT_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(path, CUSTOM_FONT_PATH)


'''
其他函数
'''


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
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)   # 创建cache文件夹
    json_path = CACHE_DIR / f"{os.path.basename(txt_path)[:-4]}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        f.write(json_data)

    return json_path

'''
程序主窗体
'''


def ft_interface(page: ft.Page):
    global chat_json_path
    chat_json_path = ensure_chat_json_path()

    # 设置字体与主题
    page.title = 'BillyGPT'
    page.theme = ft.Theme(font_family='Arial')
    page.dark_theme = page.theme
    page.bgcolor = "#0b0f14"
    page.padding = ft.padding.symmetric(horizontal=24, vertical=18)

    # 设置主页面聊天区域的滚动列表
    chat_area = ft.ListView(
        expand=True,
        spacing=12,
        auto_scroll=True,
        padding=ft.padding.symmetric(horizontal=4, vertical=8))
    empty_state = ft.Container(
        content=ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Container(
                            content=ft.Icon(ft.Icons.CHAT_BUBBLE_OUTLINE, size=34, color="#d7e5ff"),
                            width=64,
                            height=64,
                            alignment=ft.alignment.center,
                            bgcolor="#192232",
                            border=ft.border.all(1, "#2d3a4d"),
                            border_radius=8,
                        ),
                        ft.Text(
                            "BillyGPT",
                            size=34,
                            weight=ft.FontWeight.BOLD,
                            color="#ecf3ff",
                        ),
                        ft.Text(
                            "Maintenance-mode ChatGPT desktop client",
                            size=15,
                            color="#9fb0c3",
                        ),
                    ],
                    spacing=10,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Container(height=14, width=220, bgcolor="#314158", border_radius=3),
                            ft.Container(height=14, width=300, bgcolor="#243246", border_radius=3),
                            ft.Container(height=14, width=250, bgcolor="#243246", border_radius=3),
                            ft.Container(
                                content=ft.Row(
                                    controls=[
                                        ft.Container(height=10, width=110, bgcolor="#1cc9a0", border_radius=3),
                                        ft.Container(height=10, width=72, bgcolor="#536176", border_radius=3),
                                    ],
                                    spacing=10,
                                ),
                                margin=ft.margin.only(top=10),
                            ),
                        ],
                        spacing=10,
                    ),
                    width=360,
                    padding=22,
                    bgcolor="#0d131b",
                    border=ft.border.all(1, "#243246"),
                    border_radius=8,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        alignment=ft.alignment.center_left,
        bgcolor="#101720",
        border=ft.border.all(1, "#243246"),
        border_radius=8,
        height=230,
        width=1040,
        padding=28,
    )

    def show_empty_state():
        chat_area.controls.clear()
        empty_state.visible = True

    def remove_empty_state():
        empty_state.visible = False

    show_empty_state()

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
                for chat_row_content in full_chatlog:
                    remove_empty_state()
                    role = chat_row_content['role']
                    content = chat_row_content['content']
                    chat_area.controls.append(chat_row(role, content))
                    page.update()
            elif selected_file[-4:] == '.txt':
                json_path = convert_content_to_unicode(selected_file)
                full_chatlog = get_combined_data(json_path)
                for chat_row_content in full_chatlog:
                    remove_empty_state()
                    role = decode_chr(chat_row_content['role'])
                    content = decode_chr(chat_row_content['content'])
                    chat_area.controls.append(chat_row(role, content))
                    page.update()
        except Exception as e:
            chat_area.controls.append(
                Text(f'Import failed:\n{e}\nPlease check the chat log file.'))
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

    # 隐藏所有
    page.overlay.extend([import_chatlog_dialog, save_file_dialog])

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
        write_api_key(apikey_field.value)
        openai.api_key = read_api_key()
        page.update()

    def cancel_settings(e):
        settings_dlg.open = False
        page.update()


    change_font_dialog = FilePicker(on_result=change_font_clicked)
    page.overlay.extend([change_font_dialog])

    apikey_field = ft.TextField(hint_text='OpenAI API key')
    legacy_notice = ft.Text('BillyGPT is a maintenance-mode legacy project.', size=15)
    github_page_btn = ft.ElevatedButton(
        'Open GitHub',
        tooltip='Repository, history, and safety notes',
        on_click=lambda _:page.launch_url('https://github.com/B1lli/BillyGPT')
    )
    change_font_btn = ft.ElevatedButton(
        'Select custom font',
        on_click=lambda _:change_font_dialog.pick_files(
            allowed_extensions=['ttf'],
            allow_multiple=False,
            dialog_title='Select font file',
        )
    )
    settings_dlg = ft.AlertDialog(
        title=ft.Text("Settings"),
        content=ft.Column(
            [apikey_field,legacy_notice,github_page_btn,change_font_btn],
            height=200,

        ),
        actions=[
            ft.TextButton("Save", on_click=save_settings),
            ft.TextButton("Cancel", on_click=cancel_settings)
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        shape=ft.RoundedRectangleBorder(radius=10)
    )

    def open_dlg_modal(e):
        page.dialog = settings_dlg
        settings_dlg.open = True
        page.update()

    settings_btn = ft.IconButton(
        icon=ft.Icons.SETTINGS_OUTLINED,
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
        write_api_key(apikey_field_open.value)
        openai.api_key = read_api_key()
        open_setting_apikey_dlg.open = False
        page.update()

    get_apikey_btn = ft.ElevatedButton(
        'Get an OpenAI API key',
        on_click=lambda _:page.launch_url('https://platform.openai.com/account/api-keys')
    )
    openai.api_key = read_api_key()
    if not openai.api_key:
        apikey_field_open = ft.TextField(label="OpenAI API key")
        open_setting_apikey_dlg = ft.AlertDialog(
            open=True,
            modal=True,
            title=ft.Text("Welcome to BillyGPT"),
            content=ft.Column(
                [apikey_field_open,get_apikey_btn],
                tight=True),
            actions=[
                ft.ElevatedButton(
                    text="Start",
                    on_click=save_settings_open)],
            actions_alignment="end",
        )
        page.dialog = open_setting_apikey_dlg
        openai.api_key = read_api_key()

    '''
    添加聊天行
    '''
    def add_msg(e):
        chatPO_btn.disabled = True
        remove_empty_state()
        chat_area.controls.append(chat_row('user', chat_text.value))
        chat_text.value = ""
        page.update()
        chat_area.controls.append(
            chat_row(
                'assistant', chatGPT()))
        page.update()

    def add_msg_composition(e):
        chatPO_btn.disabled = True
        remove_empty_state()
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


    chat_text = ft.TextField(
        hint_text="Message ChatGPT",
        filled=True,
        expand=True,
        multiline=True,
        min_lines=1,
        max_lines=4,
        border_radius=8)
    chat_btn = ft.ElevatedButton(
        "Send",
        icon=ft.Icons.SEND_OUTLINED,
        on_click=add_msg,
        tooltip='Send message'
    )
    chatPO_btn = ft.ElevatedButton(
        "Prompt mode",
        icon=ft.Icons.AUTO_FIX_HIGH_OUTLINED,
        on_click=add_msg_composition,
        tooltip='Structured prompt mode'
    )

    toolbar = ft.Container(
        content=Row(
            [
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.CHAT_BUBBLE_OUTLINE, color="#d7e5ff"),
                        ft.Text("BillyGPT", weight=ft.FontWeight.BOLD, color="#ecf3ff", size=18),
                    ],
                    spacing=8,
                ),
                ElevatedButton(
                    "New chat",
                    icon=ft.Icons.CLEANING_SERVICES,
                    on_click=lambda _ : clear_page(),
                ),
                ElevatedButton(
                    "Import",
                    icon=ft.Icons.FILE_DOWNLOAD_OUTLINED,
                    on_click=lambda _: import_chatlog_dialog.pick_files(
                        allowed_extensions=['json','txt'],
                        allow_multiple=False,
                        dialog_title='Select chat log',
                        initial_directory=str(CHATLOG_DIR)
                    ),
                ),
                ElevatedButton(
                    "Export",
                    icon=ft.Icons.FILE_UPLOAD_OUTLINED,
                    on_click=lambda _: save_file_dialog.save_file(
                        file_name=f"chat_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt",
                    ),
                    disabled=page.web,
                ),
                settings_btn
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            width=992,
        ),
        width=1040,
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        bgcolor="#101720",
        border=ft.border.all(1, "#243246"),
        border_radius=8,
    )
    composer = ft.Container(
        content=ft.Row(
            controls=[
                chat_text,
                chat_btn,
                chatPO_btn
            ],
            vertical_alignment=ft.CrossAxisAlignment.END,
        ),
        width=1040,
        padding=12,
        bgcolor="#101720",
        border=ft.border.all(1, "#243246"),
        border_radius=8,
    )
    app_layout = ft.Column(
        controls=[
            toolbar,
            empty_state,
            chat_area,
            composer,
        ],
        expand=True,
        spacing=10,
        width=1040,
    )

    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.add(app_layout)


    '''
    添加清空页面方法
    '''
    def clear_page():
        global chat_json_path
        show_empty_state()
        page.update()
        chat_json_path = create_chat_json()
        chatPO_btn.disabled = False

    '''
    聊天方法，向api发送请求
    '''
    def chatGPT(message=None):
        try:
            # global role_template
            if not message: message = get_combined_data(chat_json_path)
            # message = get_combined_data ( chat_json_path )
            chatGPT_raw_response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=message
            )
            # if role_template:pass
            chatGPT_response = decode_chr(
                chatGPT_raw_response.choices[0].message['content'])
            return chatGPT_response.strip()
        except openai.error.AuthenticationError as error:
            error_message = f'Error:\n{str(error)}\nPlease update the API key in settings.'
            chat_area.controls.append(ft.Text(error_message))
            page.update()
            return error_message
        except openai.error.InvalidRequestError as error:
            error_message = f'Error:\n{str(error)}\nThe chat context is too long. Summarize or shorten it and retry.'
            chat_area.controls.append(ft.Text(error_message))
            page.update()
            return error_message
        except Exception as error:
            error_message = f'Error:\n{str(error)}\nPlease check the API key and dependency versions.'
            chat_area.controls.append(ft.Text(error_message))
            page.update()
            return error_message


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
                ft.Text('Analyzing prompt structure...', color='#1cc9a0'))
            page.update()
            composition_analysis_message = prompt_composition_analysis(
                initial_prompt)
            chat_area.controls.append(
                ft.Text('Generating a structured response...', color='#1cc9a0'))
            page.update()
            chatGPT_raw_response = composition_stepped_reply(
                composition_analysis_message)
            chatGPT_response = decode_chr(
                chatGPT_raw_response.choices[0].message['content'])
            return chatGPT_response.strip()
        except openai.error.AuthenticationError as error:
            error_message = f'Error:\n{str(error)}\nPlease update the API key in settings.'
            chat_area.controls.append(ft.Text(error_message))
            page.update()
            return error_message
        except Exception as error:
            error_message = f'Error:\n{str(error)}\nPlease check the API key and dependency versions.'
            chat_area.controls.append(ft.Text(error_message))
            page.update()
            return error_message

    '''
    版本信息
    '''
    ver_text = ft.Text('BillyGPT V5.3.1', size=10, color="#768397")
    app_layout.controls.append(ver_text)
    page.update()


if __name__ == '__main__':
    # 在客户端运行
    ft.app(target=ft_interface, assets_dir=str(ASSETS_DIR))

    # 在内网运行
    # ft.app ( port=8550, target=ft_interface, view=ft.WEB_BROWSER ,assets_dir='assets')
