# coding=utf-8
"""
@author B1lli
@date 2023年03月09日 17:11:42
@File:main.py
"""
# coding=utf-8
"""
@author B1lli
@date 2023年03月09日 15:49:44
@File:main_backup3.py
"""
import json
import os
import time
import openai
import flet as ft
import re


openai.api_key = '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'

# 设置全局继承文本的列表
global success_lst
success_lst = []

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

# markdown检测
def markdown_check(gpt_msg):
    pass


def ft_interface(page: ft.Page) :
    # 设置字体与主题
    page.title = 'BillyGPT'
    page.fonts = {'A75方正像素12' : '../assets/font.ttf'}
    page.theme = ft.Theme ( font_family='A75方正像素12' )
    page.dark_theme = page.theme


    # 设置滚动列表
    gpt_text = ft.ListView ( expand=True, spacing=10, auto_scroll=True, padding=20 )
    page.add ( gpt_text )

    def chat_row(character,value):
        return ft.Row(
            [
                ft.Dropdown(
                    value=character,
                    width=150,
                    options=[
                        ft.dropdown.Option("system"),
                        ft.dropdown.Option("user"),
                        ft.dropdown.Option("assistant"),
                    ],
                ),
                ft.TextField(
                    value=value,
                    filled=True,
                    # bgcolor='#1c1c1c',
                    expand=True,
                    multiline=True
                ),
            ]
        )




    # 按下对话按钮
    def add_msg(e):
        gpt_text.controls.append ( chat_row('user',chat_text.value) )
        page.update()
        view.update ()
        gpt_text.controls.append(chat_row('assistant',chat2(chat_text.value)))
        chat_text.value = ""
        page.update()
        view.update()

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
            msg = [{"role" : "user", "content" : f"{msg}"}]
            message = [
                {"role" : "system",
                 "content" : '''你是名为Billy的助手'''}
            ]
            if success_lst :
                success_lst.extend(msg)
                message.extend ( success_lst )
            else:
                message.extend(msg)
            completion = openai.ChatCompletion.create (
                model="gpt-3.5-turbo",
                messages=message
            )
            gpt_msg = completion.choices[0].message['content']
            d_msg = decode_chr ( gpt_msg )
            success_lst.append({"role" : "assistant", "content" : f"{d_msg}"})
            return d_msg

        except openai.error.RateLimitError:
            print( "频率过高，请过一分钟再试，或更换API-KEY" )
            pass
        except Exception as e:
            print( f"出现如下报错：\n{e}，如果无法重新发起对话，请尝试重启程序，或者检查自己的网络环境能否连接到openai的服务器" )
        finally:
            print( success_lst )


    # 版本信息
    ver_text = ft.Text('V1.0.0 有技术问题请咨询qq2508285107',size=10)
    page.add(ver_text)

if __name__ == '__main__':
    ft.app ( target=ft_interface, assets_dir='assets' )








