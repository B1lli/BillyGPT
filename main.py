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
            label="消息内容",
            value=self.content,
            filled=True,
            expand=True,
            multiline=True,
            on_change=self.content_change
        )

        self.generalize_btn = ft.ElevatedButton(
        '概括本消息',
        on_click=self.sum_change
    )
        self.sum_field = ft.TextField (
            visible=False,
            label="概括内容",
            value='概括中',
            filled=True,
            expand=True,
            multiline=True,
            # on_change=self.content_change
        )

        self.one_chat_row = ft.Row (
            [
                self.role_dropdown,
                self.content_textfield,
                self.generalize_btn,
                self.sum_field,
            ]
        )
        return self.one_chat_row

    def sum_change(self,e):
        self.generalize_btn.disabled = True
        self.update()
        self.one_chat_row.controls.append(self.sum_field)
        self.update()
        self.summary = chatGPT_sum(self.content)
        renew_now_chat (
            chat_json_path=chat_json_path,
            hash_val=self.hash,
            summary=self.summary )
        self.sum_field.visible = True
        self.sum_field.value = self.summary
        self.generalize_btn.disabled = False
        self.update ()
        return self.one_chat_row

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
        
        
            {content}
        
        
            概括内容:'''}]
        chatGPT_raw_response = openai.ChatCompletion.create (
            model="gpt-3.5-turbo",
            messages=composition_analysis_message
        )
        summary = decode_chr ( chatGPT_raw_response.choices[0].message['content'].strip () )
        chain_summary.append(summary)
        print(summary)

    chain_summary_long = '\n'.join ( chain_summary )
    return chain_summary_long



def chatGPT_sum(content,chain_type='map_reduce'):
    try:
        # 试图用langchain但无法打包
        import langchain
        from langchain.llms import OpenAI
        from langchain.chains.summarize import load_summarize_chain
        from langchain.chains import AnalyzeDocumentChain
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        from langchain.document_loaders import UnstructuredFileLoader
        from langchain.docstore.document import Document
        from langchain.prompts import PromptTemplate
        '''
        准备步骤
        '''
        # 创建文本分块器，每块长度为1000
        text_splitter = RecursiveCharacterTextSplitter ( chunk_size=1000, chunk_overlap=0 )
        # 创建大语言模型，将温度拉到最低以提高精确性
        llm = OpenAI ( temperature=0, openai_api_key=openai.api_key )

        '''
        加载需要概括的内容
        '''
        # 加载外部文件
        # loader = UnstructuredFileLoader ( 'game_log_conversation.txt' )
        # docs = loader.load ()
        # split_docs = text_splitter.split_documents(docs)

        # 加载函数输入的字符串
        split_content = text_splitter.split_text ( content )
        split_docs = [Document ( page_content=t ) for t in split_content]

        '''
        总结文本
        '''
        # 创建prompt模板
        prompt_template = """为以下文本创建概括:
    
    
        {text}
    
    
        概括内容:"""
        PROMPT = PromptTemplate ( template=prompt_template, input_variables=["text"] )
        # 创建总结链，模式为map_reduce
        # 第一种
        # 有模板的总结链
        summary_chain = load_summarize_chain ( llm, chain_type="map_reduce", return_intermediate_steps=True,
                                       map_prompt=PROMPT, combine_prompt=PROMPT ,verbose=True)
        # 带参数带模板总结
        chain_summary = summary_chain (
            {"input_documents" : split_docs},
            # return_only_outputs=True,
        )
        # 第二种
        # 无模板的总结链
        # summary_chain = load_summarize_chain ( llm, chain_type=chain_type, verbose=True )
        # 直接总结
        # chain_summary = summary_chain.run ( split_docs )

        chain_summary_long = '\n'.join(chain_summary['intermediate_steps'])
        return chain_summary_long
    except Exception as error:
        print(error)
        return chatGPT_sum_old(content)



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
                   role: str = None, content: str = None , summary=None) -> None:
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
            if summary :
                chat_item['message']['summary'] = summary
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
        openai.api_key = read_APIKEY()
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
    添加模板选择功能
    可以读取模板文件，实时搜索，选择时可以切换身份
    '''
    class DropdownSearchBar(ft.UserControl):
        def __init__(self):
            super(DropdownSearchBar, self).__init__()
            self.item_number = ft.Text(size=9,italic=True)

        def dropdown_search(self):
            _object_ = ft.Container(
                width=450,
                height=50,
                bgcolor="white10",
                border_radius=6,
                padding=ft.padding.only(top=15),
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                animate=ft.animation.Animation(400,"decelerate"),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.START,
                    controls=[
                        Row(
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Icon(
                                    ft.icons.SEARCH_ROUNDED,
                                    size=15,
                                    opacity=0.90,
                                ),
                                ft.TextField(
                                    border_color='transparent',
                                    height=20,
                                    text_size=12,
                                    content_padding=2,
                                    cursor_color='black',
                                    cursor_width=1,
                                    hint_text='搜索模板',
                                    on_change=None
                                ),
                                self.item_number,
                            ],
                        ),
                        ft.Column(
                            scroll='auto',
                            expand=True
                        )
                    ]
                )
            )
            return _object_

        def build(self):
            return ft.Container()

    page.add(DropdownSearchBar())
    # def template_change(self, e):
    #     template_name = template_dropbox.value
    #     renew_now_chat(
    #         chat_json_path=chat_json_path,
    #         hash_val=self.hash,
    #         role=self.role)
    #
    #
    # template_dropbox = ft.Dropdown(
    #         value=role,
    #         width=150,
    #         options=[
    #             ft.dropdown.Option("system"),
    #             ft.dropdown.Option("user"),
    #             ft.dropdown.Option("assistant"),
    #         ],
    #         on_change=template_change
    #     )

    '''
    设置布局 添加控件
    '''
    # 模板选择下拉框

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
            chat_area.controls.append(
                ft.Text(f'出现如下报错\n{str(error)}\n请在设置中更新可用的apikey'))
            page.update()
        except openai.error.InvalidRequestError as error:
            chat_area.controls.append(
                ft.Text(f'出现如下报错\n{str(error)}\n聊天上下文过长，请对长文本调用概括模块概括后重试'))
            page.update()

            # summarize_chatlog(chat_json_path)
            # chat_area.controls.append(
            #     ft.Text(f'概括完毕，已发送概括后消息'))
            # page.update()
            # message =  cut_message ( get_combined_data ( chat_json_path ) )
            # chatGPT_raw_response = openai.ChatCompletion.create(
            #     model="gpt-3.5-turbo",
            #     messages=message
            # )
            # chatGPT_response = decode_chr(
            #     chatGPT_raw_response.choices[0].message['content'])
            # return chatGPT_response.strip()


        except Exception as error:
            print(openai.api_key)
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
            print(openai.api_key)
            chat_area.controls.append(
                ft.Text(f'出现如下报错\n{str ( error )}\n请联系开发者微信B1lli_official'))
            page.update()

    '''
    版本信息
    '''
    ver_text = ft.Text('BillyGPT V5.3.1  By B1lli', size=10)
    page.add(ver_text)


if __name__ == '__main__':
    # 在客户端运行
    ft.app(target=ft_interface, assets_dir='assets')

    # 在内网运行
    # ft.app ( port=8550, target=ft_interface, view=ft.WEB_BROWSER ,assets_dir='assets')

    content = '''接下来你看到的是一个文字冒险游戏的剧情，你是剧情的女主角，名为钰鹤，下面是以对话形式展现出的剧情，你需要做出合理的判断，并说明原因：?？?：马路上的那个人怎么没撑伞
被雨淋湿的青年：
?？?：（他的样子好像有点奇怪···
?？?：睫··车开过来了那个人却没有发现.....！?
?？?：再这样下去，他会被车撞到！？
?？?：危险………！
???：(我为什么在这里
???：只记得自已跳入车道，之后的事完全没印象开眼睛就发现自己躺在医院病床上了
???：不知道那个人事故之后怎么样了
穿西装的男子：小姐·你从刚才就在发呆你听到我说的话了吗？
???：啊…………不好意思
???：对了，我想起来了。有人说发现我和某个人在一起而那个人身上带看违法药品
???：(本以为要继续接受盘问结果莫名其妙地就被带到了这座岛上
穿西装的男子：埃我知道，遇到这种事头脑难免会陷入一片混乱
穿西装的男子：正因为情况特殊你更应该振作起来才行你说得出自己的全名吗？
鹤：嗯，我是钰鹤
穿西装的男子：真是太好了。看来你还算比较冷静至少说得出自已的名字。
穿西装的男子：那么，你应该也能够理解我刚才的说明吧钰小姐。
鹤：嗯……你是
穿西装的男子：真是的·
穿西装的男子：真是的我的名字是『今部』。看来你真的睡糊涂了。
鹤：对了，他叫今部··
鹤：在被带来这里之前接受警方盘问正当事情始终理不出头绪时是他帮我脱离了困境
鹤：（但我完全不认识他不知道他是个怎么样的人
今部：没办法，只好挑重点再重新说明一次，这次请你务必专心听。
今部：首先第一个重点，正如刚刚所说的尔被怀疑涉及参与了某起事件现在被列为重点参考证人。
今部：由于事发现场，与你在一起的男子有交易非法药物的嫌疑。
今部：和他出现在同一个地点的人，也就是你，自然也被怀疑参与了违法买卖
鹤：你说我有嫌疑可是我真的什么都不知道也不认识那个男的
今部：可惜有自击者指出，曾经好几次看到男一女在事发地点附近的夜店出没进行非法药物交易
鹤：可是，我真的没有
今部：我了解。但现在的难点是没有人能证明你是无辜的。
鹤：那我该怎么做才好现在那个被环疑的男人在哪里？他看到我的脸应该就会知道抓错人了。
今部：你说的没错，请他真接和你见面确认，也许是最快的方法。
今部：只可惜他大概很难为你提供不在场证明
鹤：为什么…………·?
今部：你认得这名男子吧？
鹤：这个人的脸··我见过…
今部：这名涉嫌交易非法药物的男子可能因为车祸的冲击丧失了部分过去的记忆。
鹤：什么？丧失记忆
今部：是的。我想应该只是暂时性的失忆。但是他完全想不起来那天在夜店里和他在一起的女人是谁。
鹤：(怎么会难道真的没有人可以证明我的清白了？
今部：我帮你作证吧
今部：你没听清楚吗？我说我要帮你作证，证明你不认识那名男子，也和非法药物的犯罪无关。
鹤：你要帮我作证这样就能证明我的清白了吗？
今部：只要钰小姐愿意配合协助我。
今部：我的提议绝不会陷你干不利
鹤：(要我协助他可是如果他提出什么难题或是奇怪的条件，我该怎么办
今部：你似平还没完全了解你的处境
今部：事情发展到这地步，你没有选择的余地。请回我「好」或「YES」，二择其一。你会接受我的提议吧？
今部：我想请你帮的忙，就是在那名失忆男子的面前假装自己是『他的恋人』
鹤：要我扮演他的恋人·！?
今部：其实发生交通事故之前他和某位女性在一起，而那位女性很可能是他的女友。
今部：那名女性最后被目击到的地点就是那间夜店，随后不久她便失踪行踪成谜
今部：为了找出那位失踪的女性必须找回这名男子因车祸失去的记忆。
今部：所以才希望你假扮成他的恋人从他口中打听任何可能的线索找出他女友的所在地，
今部：在你协助的这段期间，我也会在别处进行搜索。只要找到和他出现在夜店的那名女性，就能顺利证明你的清白了。
鹤：可是我要怎么在素未谋面的陌生人面前假扮他的恋人，这未免太强人所难了·
今部：这不是担心做不做得到的时候你非做不可。
今部：麻烦你了。
鹤：为了洗清我的嫌疑也别无选择了
鹤：好我知道了
今部：谢谢你愿意协助据说这名男子周围的人都叫他也『葵』。
鹤：名字是『葵』吗
今部：啊，对了。差点忘了告诉你你从今天开始必须暂时住在这座小岛上。
鹤：什么？
今部：住宿的相关细节等下会由设施员工为你说明
鹤：等、等一下
看守员：不好意思我过来带钰小姐到她的房间。
今部：那就之后再见了钰小姐。
鹤：我到底会被带去挪里话说回来，在抵达小岛前好像坐了很久的船
鹤：该不会在找到他的女友之前我都回不了家？
鹤：..·嗯?
鹤：从这里能跳望到海面
鹤：这里真的是一座孤岛
看守员：今天的海面很平静呢
鹤：风景很美。大海和天空一望无际
看守员：毕竟这座设施坐落于岛上视野最佳的位置。
看守员：以前政府在这座岛上盖了监由国家管理
看守员：但战后因财政困难，没有经费维持而关闭后来由民间企业『西海普制药」将整座岛买下，加以利用。
看守员：我个现在所在的这栋建筑设施就是『西海普医疗中心』。
鹤：『西海普制药』?
看守员：那是一家专门研发、制造医疗用品及药品的制药厂。
看守员：这里就是『西海普制药』所管理的设施之一，用于收容病患以进行外地疗养
看守员：··表面上是这样。不过我想你也已经察觉到，实际用途不仅如此。
看守员：这里的收容人都有自己的房间只要在安全管理上不引发问题都能在允许的范围内从事自由活动。
看守员：也个的房间受到24小时全天候的监视一旦房间内发生任何意外，设施的勺人员都能马上应对。
鹤：·这么说的话，我的行动也会受到监视吗？
看守员：不会。我收到的指示是要带你去员工用宿舍的房间。那里不在监视的范围内，你大可放心。
看守员：一直站在这里说话也不是办法，我价们继续往前走吧
看守员：这里就是钰小姐的房间可供你自由使用
看守员：另外，还要给你这个
鹤：智能手机?
看守员：是的。在岛上的期间无法使用私人手机，请改用这台『SABOT』。
看守员：请收下。可以试着开启一下电源。
看守员：启动之后，手机内的引导功能就会为你介绍各功能的使用方法
看守员：这只手机也能当作你在岛上的身份证请务必随身携带
看守员：注意千万不要弄丢使用上也请多加小心
看守员：此外，在岛上只要出示这支手机证明身份，就能免费购物。不需要另外支付现金。
看守员：今部先生已经事先为钰小姐预付了一笔费用当作在岛上的生活费你不用担心金钱的问题。
看守员：最后说一件事关于明天会面请你明早10点到我们刚才经过的收容所入口处集合。
鹤：好的我明白了
看守员：那么，请好好休息
鹤：·是。
鹤：天呐没想到我被卷入了这么棘手的事件
鹤：今后，到底会怎样?
鹤：(太阳升起来了差不多该前往看守员所说的地点了
今部：早安，钰小姐。
今部：你好像很紧张。
鹤：嗯…是啊。
今部：那也是难免的。昨天离开后，我也重新思考了一遍
今部：你是普通人，不是职业演员：老实说我也不认为你能很自然地扮成他的恋人。
今部：今天就先以他的友人身份见面视状况往后再做调整吧
今部：请你在了解他的为人以后再看准合适的时机：告诉他你是他的女友。
看守员：早安。今部先生，钰小姐。让两位久等了。
今部：阿，已经到会面时间了吗那就拜托你好好表现了，钰小姐。
鹤：太、太强人所难了·
看守员：那我们走吧。
看守员：这间就是会面室。
看守员：进去以后，你会看见里面有块玻璃隔板将房间隔成会面者和收容人用的两间小房间。
看守员：会面过程中不会有职员陪同司，我们会在房间外待命，有任何问题或需要帮忙时，请随时叫我个
看守员：也许和收容人独处会让你感到不安但会面室的玻璃采用不易被打破的强化玻璃亚克力板制成，
看守员：即使搬起椅子用力砸玻璃房间内的隔板也绝对不会碎。这点你大可放心。
鹤：那个
看守员：是，请说。
鹤：请问·我该怎么面对收容人?
看守员：该怎么面对？如果你是他的朋友，就以平常心对待即可。
鹤：(我就是无法拿捏所谓的「平常心」
看守员：请问怎么了？还有什么事让你感到不安吗？
鹤：啊，没有没事。
看守员：等会面时间结束了，我会敲门提醒你就算事情没说完，也请尽快结束会面离开房间。
鹤：就是这人人吗·
葵：干嘛?一直町着别人的脸看
葵：我听说有人认识的人想找我谈谈
葵：
葵：不过很抱，我对你完全没印象。
葵：你叫什么名字？
葵：钰鹤
葵：嗯名字也没有印象。
葵：我们真的认识？
鹤：与其说认识，不如说
葵：啊，还是算了。反正我都不记得了问了也没有意义。
葵：如果我们以前真的见过面那很抱款，我现在都想不起来了。
葵：那么，你找我有什么事？
葵：特地跑到这种地方，应该不会只是为了闲聊吧？
葵：应该是有什么事想问我？
鹤：（就算这么说，我也不知道该问什么好.
鹤：（既然要装作认识的人要是表现得太客气的话反而会很不自然吧·
葵：怎么了？
鹤：啊，嗯那
葵：。。。
鹤：再这样下去会被怀疑的得随便问点问题才行···
鹤：（总之，先问问看关于那场意外他还记得什么吧
你面临着2个选择，第一个：我听人说 ，你正涉及某件危险的事。第二个：你还记得意外发生前 ，你跟谁在一起吗 ？'''

    # a = chatGPT_sum(content)
    # print(a)

'''
你是一个文字冒险游戏的女主角，名为钰鹤，钰是姓氏，鹤是名字。下面是游戏剧情，你需要根据剧情做出合理的判断，并说明原因：
 钰鹤被警方怀疑参与了某起事件，今部帮助她脱离困境，但他们需要找到一个可以证明钰鹤无辜的方法，最终他们决定让钰鹤和被环疑的男子见面，以确认钰鹤的无辜。
 鹤被要求去小岛上假扮一名失忆男子的恋人，以帮助他找回记忆，以洗清自己的嫌疑。小岛上有一座监狱，拥有最佳的视野，海面平静，风景美丽。
 鹤被卷入一个棘手的事件，被带到一个由民间企业『西海普制药」管理的设施，收容病患以进行外地疗养，但实际用途不仅如此。鹤被给予一台『SABOT』智能手机，可以用来证明身份，免费购物，以及收到一笔费用当作在岛上的生活费。最后，鹤被要求在第二天10点到
 鹤面对着葵，不知道该如何面对，看守员提醒他以平常心对待，葵表示自己对鹤完全没有印象，
你要向葵提问，你面临着2个提问选择：
1.我听人说，你正涉及某件危险的事。
2.你还记得意外发生前，你跟谁在一起吗？
你选择哪个，为什么？'''

