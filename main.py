import http.server
import socketserver
import threading
import requests
import re
import os
import io
import csv
import json
import sys
from DataBase import msg_db, misc_db, close_db, init_db
from DataBase.merge import merge_databases, merge_MediaMSG_databases
from decrypt import get_wx_info, decrypt
import time
import schedule
from output import Output
import pandas as pd
from datetime import datetime, timedelta
from flask import Flask, render_template
from web.app import app, record_task_execution

# 是否需要生成日报
IsNeedOut = False
# 数据存放文件路径
INFO_FILE_PATH = 'C:/PM_AI/DEMO/WeChatMsg/WeChatMsg/app/data/info.json'  # 个人信息文件
DB_DIR = 'C:/PM_AI/DEMO/WeChatMsg/WeChatMsg/app/Database/Msg'
OUTPUT_DIR = 'C:/PM_AI/DEMO/WeChatMsg/WeChatMsg/data'  # 输出文件夹
os.makedirs('C:/PM_AI/DEMO/WeChatMsg/WeChatMsg/app/data', exist_ok=True)
os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 创建配置目录和数据目录
os.makedirs('config', exist_ok=True)
os.makedirs('data', exist_ok=True)

# 加载配置文件
def load_config(file_path, default_value=None):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载配置文件 {file_path} 失败: {str(e)}")
    return default_value

# 保存配置文件
def save_config(file_path, data):
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存配置文件 {file_path} 失败: {str(e)}")
        return False

class DecryptHandler:
    def __init__(self):
        self.load_decrypt_config()
    
    def load_decrypt_config(self):
        config = load_config('config/decrypt_params.json', {})
        self.wx_dir = config.get('wx_dir', '')
        self.info = {
            'filePath': config.get('filePath', ''),
            'key': config.get('key', ''),
            'mobile': config.get('mobile', ''),
            'name': config.get('name', ''),
            'pid': config.get('pid', 0),
            'version': config.get('version', ''),
            'wxid': config.get('wxid', ''),
            'mobel': config.get('mobel', '')
        }
        self.ready = bool(self.wx_dir and self.info['key'])
       
    
    def save_decrypt_config(self):
        config = {
            'wx_dir': self.wx_dir,
            'filePath': self.info['filePath'],
            'key': self.info['key'],
            'mobile': self.info['mobile'],
            'name': self.info['name'],
            'pid': self.info['pid'],
            'version': self.info['version'],
            'wxid': self.info['wxid'],
            'mobel': self.info['mobel']
        }
        save_config('config/decrypt_params.json', config)
            
    def decrypt(self):
        self.load_decrypt_config()  # 每次解密前重新加载配置
        db_dir = os.path.join(self.wx_dir, 'Msg')
        close_db()
        if self.DecryptThread(db_dir, self.info['key']):
            print("解密完成")

    def DecryptThread(self, db_path, key):
        close_db()
        output_dir = DB_DIR
        os.makedirs(output_dir, exist_ok=True)
        tasks = []
        if os.path.exists(db_path):
            for root, dirs, files in os.walk(db_path):
                for file in files:
                    if '.db' == file[-3:]:
                        if 'xInfo.db' == file:
                            continue
                        inpath = os.path.join(root, file)
                        output_path = os.path.join(output_dir, file)
                        tasks.append([key, inpath, output_path])
                    else:
                        try:
                            name, suffix = file.split('.')
                            if suffix.startswith('db_SQLITE'):
                                inpath = os.path.join(root, file)
                                output_path = os.path.join(output_dir, name + '.db')
                                tasks.append([self.key, inpath, output_path])
                        except:
                            continue
        for i, task in enumerate(tasks):
            if decrypt.decrypt(*task) == -1:
                return False
        
        # 目标数据库文件
        target_database = os.path.join(DB_DIR, 'MSG.db')
        # 源数据库文件列表
        source_databases = [os.path.join(DB_DIR, f"MSG{i}.db") for i in range(1, 50)]
        import shutil
        if os.path.exists(target_database):
            os.remove(target_database)
        shutil.copy2(os.path.join(DB_DIR, 'MSG0.db'), target_database)  # 使用一个数据库文件作为模板
        # 合并数据库
        merge_databases(source_databases, target_database)

        # 音频数据库文件
        target_database = os.path.join(DB_DIR, 'MediaMSG.db')
        # 源数据库文件列表
        if os.path.exists(target_database):
            os.remove(target_database)
        source_databases = [os.path.join(DB_DIR, f"MediaMSG{i}.db") for i in range(1, 50)]
        shutil.copy2(os.path.join(DB_DIR, 'MediaMSG0.db'), target_database)  # 使用一个数据库文件作为模板

        # 合并数据库
        merge_MediaMSG_databases(source_databases, target_database)
        return True

def kill_wechat_process():
    global IsNeedOut
    IsNeedOut = True

def clean_chat_logs(file_path, output_dir):
    # 读取 CSV
    df = pd.read_csv(file_path, encoding="utf-8")
    df["StrTime"] = pd.to_datetime(df["StrTime"], format="%Y-%m-%d %H:%M:%S")

    # 获取本周起始日期
    #today = datetime.today()
    #start_of_week = today - timedelta(days=today.weekday()+1)

    # 筛选本周数据
    #df_this_week = df[df["StrTime"] >= start_of_week]
    df_cleaned = df
    # 从配置文件加载不相关的群组
    #irrelevant_groups = load_config('config/irrelevant_groups.json')

    # 过滤掉不相关群组
    #df_cleaned = df_this_week[~df_this_week["NickName"].isin(irrelevant_groups)]

    # 去除 XML 相关内容
    df_cleaned = df_cleaned[~df_cleaned["StrContent"].str.contains(r"<revokemsg>", regex=True, na=False)]
    df_cleaned = df_cleaned[~df_cleaned["StrContent"].str.contains(r"xml version", regex=True, na=False)]
    df_cleaned = df_cleaned[~df_cleaned["StrContent"].str.contains(r"<voipmsg", regex=True, na=False)]
    df_cleaned = df_cleaned[~df_cleaned["StrContent"].str.contains(r"<location", regex=True, na=False)]
    df_cleaned = df_cleaned[~df_cleaned["StrContent"].str.contains(r"<emoji", regex=True, na=False)]
    df_cleaned = df_cleaned[~df_cleaned["StrContent"].str.contains(r"<voicemsg", regex=True, na=False)]

    # 生成输出文件路径
    #cleaned_file = os.path.join(output_dir, f"cleaned_messages_{start_of_week.strftime('%Y-%m-%d')}.csv")
    cleaned_file = os.path.join(output_dir, f"cleaned_messages.csv")

    # 保存文件
    df_cleaned.to_csv(cleaned_file, index=False, encoding="utf-8-sig")
    print(f"清洗后的聊天记录: {cleaned_file}")


# def start_server():
#     """
#     启动HTTP服务器的函数。使用 ThreadingTCPServer 以支持多线程，
#     确保HTTP服务器运行在后台线程中，不阻塞主循环。
#     """
#     PORT = 8000
#     with socketserver.ThreadingTCPServer(("", PORT), MyHandler) as httpd:
#         print(f"Serving HTTP on port {PORT} in background...")
#         httpd.serve_forever()

def start_flask_app():
    """
    启动Flask应用的函数。
    """
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

def find_latest_message_file(directory_path):
        latest_date = None
        latest_message_file = None

        for filename in os.listdir(directory_path): # 直接遍历目录获取文件名
            if filename.startswith('cleaned_messages_') and filename.endswith('.csv'):
                # 使用正则表达式提取日期部分
                match = re.match(r'cleaned_messages_(\d{4}-\d{2}-\d{2})\.csv', filename)
                if match:
                    try:
                        date_str = match.group(1)
                        file_date = datetime.strptime(date_str, '%Y-%m-%d').date() # 将日期字符串转换为 date 对象
                        if latest_date is None or file_date > latest_date:
                            latest_date = file_date
                            latest_message_file = filename
                    except ValueError:
                        # 如果日期格式不正确，则忽略此文件
                        continue

        if latest_message_file:
            return os.path.join(directory_path, latest_message_file)
        else:
            return None
            
def find_latest_weekly_report(directory_path):
    latest_week_number = -1
    latest_report_file = None

    for filename in os.listdir(directory_path): # 直接遍历目录获取文件名
        if filename.startswith('W') and filename.endswith('周报.md'):
            # 使用正则表达式提取周数，更加健壮
            match = re.match(r'W(\d+)周报\.md', filename)
            if match:
                try:
                    week_number = int(match.group(1))
                    if week_number > latest_week_number:
                        latest_week_number = week_number
                        latest_report_file = filename
                except ValueError:
                    # 如果周数不是有效的数字，则忽略此文件
                    continue

    if latest_report_file:
        return os.path.join(directory_path, latest_report_file)
    else:
        return None

def output_saveMeetingCSV(content):
    data_dir = 'data'
    time_file = os.path.join(data_dir, 'meeting_time.txt')
    record_file = os.path.join(data_dir, 'meeting_record.csv')
    daily_file = os.path.join(data_dir, 'daily_record.csv')
    wechat_file = os.path.join(data_dir, 'other_record.csv')

    # 1. 读取上次会议时间（如果存在，否则默认为当天 0 点）
    start_time = datetime.strptime('2025-01-01 00:00:00', '%Y-%m-%d %H:%M:%S')
    if os.path.exists(time_file):
        try:
            with open(time_file, 'r', encoding='utf-8') as f:
                time_str = f.readline().strip()
                if time_str:
                    start_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                    start_time += timedelta(minutes=1) # 增加一分钟
        except Exception as e:
            print(f"读取会议时间文件出错，使用默认时间：{start_time}。错误信息：{e}")

    meeting_records = []
    daily_records = [] #存储日报内容
    modified_rows = [] # 用于存储修改后的 CSV 行 (不包含会议纪要行)

    last_meeting_time = start_time  # 初始化最后一条会议记录时间

    # 2. 筛选 content 中开始时间之后的数据，并提取会议纪要
    content_io = io.StringIO(content.strip()) # 使用 io.StringIO 将字符串转换为文件like对象
    csv_reader = csv.reader(content_io) # 使用 csv.reader 处理文件like对象
    header = next(csv_reader, None) # 读取并跳过 header 行
    if header: # 确保有 header 行
        #modified_rows.append(header) #  header 行始终保留
        for fields in csv_reader: # 遍历 csv_reader 获取每一行字段
            if not fields: # 跳过空行
                #modified_rows.append(fields) # 保留空行
                continue

            str_content = fields[0] if fields else ""   # 确保 str_content 始终有值
            #if '邓恒恒：三花曲线图片问题排查' in str_content:
            #    print('check')
            str_time = fields[1] if len(fields) > 1 else ""    # 确保 str_time 始终有值
            remark = fields[2] if len(fields) > 2 else ""     # 确保 remark 始终有值
            nick_name = fields[3] if len(fields) > 3 else ""  # 确保 nick_name 始终有值
            sender = fields[4] if len(fields) > 4 else ""     # 确保 sender 始终有值

            record_time = None  # 初始化 record_time 为 None
            if str_time:  # 只有当 str_time 不为空时才尝试解析
                try:
                    record_time = datetime.strptime(str_time, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    print(f"时间格式解析错误，跳过记录的时间筛选，但仍会检查会议纪要内容：{fields}") # 打印 fields 而不是 line
                    record_time = start_time  # 时间解析失败，为了后续逻辑，设置为 start_time，这样会包含所有会议纪要内容
            
            #屏蔽参会链接
            if record_time is not None and record_time >= start_time:
                if "点击链接" not in str_content:
                    if "会议纪要"  in str_content or "软件部门日报" in nick_name:
                        if record_time is None or record_time >= start_time :  # 如果 record_time 为 None (即 str_time 为空) 或者时间晚于开始时间
                            if "会议纪要" in str_content:
                                if "\n" in str_content:
                                    meeting_records.append([str_content, str_time, nick_name])
                            elif "软件部门日报" in nick_name:
                                daily_records.append([str_content, str_time, sender])
                            #  会议纪要行不添加到 modified_rows      
                    else:
                        modified_rows.append(fields) # 时间早于 start_time 的行也保留在 modified_rows 中
                
                last_meeting_time = max(last_meeting_time, record_time)  # 更新最后一条会议记录时间
    else: # 如果没有 header 行
        print("CSV 内容没有 header 行，请检查 CSV 格式。")
        modified_content = content #  如果解析 header 失败，则返回原始 content, 不进行修改
        return modified_content

    # 3. 将会议纪要 append 到 CSV 文件
    if meeting_records:
        os.makedirs(data_dir, exist_ok=True)  # 确保 data 文件夹存在
        file_exists = os.path.exists(record_file)
        try:
            with open(record_file, 'a', newline='', encoding='utf-8') as csvfile:
                csv_writer = csv.writer(csvfile)
                if not file_exists:
                    # 写入 CSV 文件头
                    csv_writer.writerow(['StrContent', 'StrTime', 'NickName'])
                # 写入会议纪要数据
                csv_writer.writerows(meeting_records)
            print(f"成功提取并保存 {len(meeting_records)} 条会议纪要到 {record_file}")
        except Exception as e:
            print(f"保存会议纪要到 CSV 文件出错。错误信息：{e}")
    else:
        print("没有找到新的会议纪要。")

    if daily_records:
        os.makedirs(data_dir, exist_ok=True)  # 确保 data 文件夹存在
        file_exists = os.path.exists(daily_file)
        try:
            with open(daily_file, 'a', newline='', encoding='utf-8') as csvfile:
                csv_writer = csv.writer(csvfile)
                if not file_exists:
                    # 写入 CSV 文件头
                    csv_writer.writerow(['StrContent', 'StrTime', 'sender'])
                # 写入会议纪要数据
                csv_writer.writerows(daily_records)
            print(f"成功提取并保存 {len(daily_records)} 条软件日报到 {daily_file}")
        except Exception as e:
            print(f"保存软件日报到 CSV 文件出错。错误信息：{e}")
    else:
        print("没有找到新的软件日报。")
        

    # 4. 将最后一条会议记录的时间保存到 meeting_time.txt
    if meeting_records or daily_records:  # 只有当有新的会议纪要被记录时才更新时间
        try:
            with open(time_file, 'w', encoding='utf-8') as f:
                # 保存最后一条会议纪要的时间，格式化为 'YYYY-MM-DD HH:MM:SS'
                f.write(last_meeting_time.strftime('%Y-%m-%d %H:%M:%S'))
            print(f"成功更新会议时间记录到 {time_file}：{last_meeting_time.strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"保存最后会议时间到文件出错。错误信息：{e}")
    else:
        print("由于没有新的会议纪要，会议时间记录文件未更新。")
    print(f"保存会议纪要完成")

    #return modified_rows
    #5.  将 modified_rows 重新组合成 CSV 格式的字符串
    #modified_content = ""
    if modified_rows:
        other_dir = os.path.join(data_dir, 'other') # 定义 other 文件夹路径
        os.makedirs(other_dir, exist_ok=True)  # 确保 other 文件夹存在

        nick_name_data = {} # 用于存储按 nick_name 划分的数据

        for row in modified_rows:
            nick_name = row[3] if len(row) > 3 else "未知用户" # 获取 nick_name，如果不存在则设置为 "未知用户"
            if nick_name not in nick_name_data:
                nick_name_data[nick_name] = []
            nick_name_data[nick_name].append(row)

        for nick_name, data_rows in nick_name_data.items():
            if not data_rows: # 如果某个 nick_name 没有数据，则跳过
                continue

            csv_file_name = f"{nick_name}.csv" # 以 nick_name 命名 CSV 文件
            csv_file_path = os.path.join(other_dir, csv_file_name) # 完整的 CSV 文件路径

            file_exists = os.path.exists(csv_file_path)
            try:
                with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile: # 使用 'w' 模式，每次都重新写入文件
                    csv_writer = csv.writer(csvfile)
                    if not file_exists:
                        # 写入 CSV 文件头 (每个文件都写入文件头)
                        csv_writer.writerow(['StrContent','StrTime','remark', 'nick_name', 'sender'])
                    # 写入数据
                    csv_writer.writerows(data_rows)
                print(f"成功保存 {len(data_rows)} 条记录到 {csv_file_path}")
            except Exception as e:
                print(f"保存 {nick_name} 的记录到 CSV 文件出错。错误信息：{e}")
    else:
        print("没有找到剩余记录。")


    # return modified_content
def output_tagCSV(startTime, endTime):
    print(f'开始按标签导出CSV，时间范围：{startTime} 至 {endTime}')
    
    # 确保tmp文件夹存在
    os.makedirs('tmp', exist_ok=True)
    
    # 加载标签配置
    tags_config = load_config('config/group_tags.json', {})
    if not tags_config:
        print('未找到标签配置文件或配置为空')
        return
    
    # 将时间字符串转换为datetime对象
    try:
        start_datetime = datetime.strptime(startTime, '%Y-%m-%d')
        end_datetime = datetime.strptime(endTime, '%Y-%m-%d')
        # 将结束时间设置为当天的23:59:59
        end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
    except ValueError as e:
        print(f'时间格式错误: {e}')
        return
    
    # 源数据文件夹
    source_dir = os.path.join('data', 'other')
    if not os.path.exists(source_dir):
        print(f'源数据文件夹 {source_dir} 不存在')
        return
    
    # 遍历标签配置
    for tag, csv_files in tags_config.items():
        print(f'处理标签: {tag}')
        
        # 用于存储该标签下所有符合时间范围的数据
        all_tag_data = []
        has_data = False
        
        # 遍历该标签下的所有CSV文件
        for csv_file in csv_files:
            csv_path = os.path.join(source_dir, csv_file)
            
            if not os.path.exists(csv_path):
                print(f'  文件不存在: {csv_file}')
                continue
            
            try:
                # 读取CSV文件
                df = pd.read_csv(csv_path, encoding='utf-8')
                
                # 确保StrTime列存在
                if 'StrTime' not in df.columns:
                    print(f'  文件 {csv_file} 中没有StrTime列')
                    continue
                
                # 将StrTime列转换为datetime类型
                df['StrTime'] = pd.to_datetime(df['StrTime'], errors='coerce')
                
                # 筛选时间范围内的数据
                filtered_df = df[(df['StrTime'] >= start_datetime) & (df['StrTime'] <= end_datetime)]
                
                if not filtered_df.empty:
                    all_tag_data.append(filtered_df)
                    has_data = True
                    print(f'  从 {csv_file} 中找到 {len(filtered_df)} 条符合时间范围的数据')
                
            except Exception as e:
                print(f'  处理文件 {csv_file} 时出错: {e}')
        
        # 如果该标签下有符合时间范围的数据，则保存为CSV
        if has_data and all_tag_data:
            # 合并该标签下所有数据
            combined_df = pd.concat(all_tag_data, ignore_index=True)
            
            # 按时间排序
            combined_df.sort_values('StrTime', inplace=True)
            
            # 保存到tmp文件夹
            output_file = os.path.join('tmp', f'{tag}.csv')
            combined_df.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f'  已保存 {len(combined_df)} 条数据到 {output_file}')
        else:
            print(f'  标签 {tag} 在指定时间范围内没有数据，跳过生成CSV')
    
    print('按标签导出CSV完成')

def output_task():
    #csv_filepath = find_latest_message_file('tmp')
    csv_filepath = 'tmp/cleaned_messages.csv'
    try:
        with open(csv_filepath, 'r', encoding='utf-8') as f:
            csv_content = f.read()
            #先提取出会议纪要和日报
            output_saveMeetingCSV(csv_content)
            #todo 继续按照标签导出客户csv
            output_tagCSV('2025-02-01','2025-02-28')
            print('finish')
    except Exception as e:
        print(f"读取CSV文件时发生错误: {e}")


if __name__ == "__main__":

    # 确保配置目录和数据目录存在
    os.makedirs('config', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    
    # 初始化处理器和输出对象
    handler = DecryptHandler()
    output = Output()
    
    # 设置每日任务
    schedule.every().day.at("21:00").do(kill_wechat_process)

    # 启动HTTP服务器
    # server_thread = threading.Thread(target=start_server, daemon=True)
    # server_thread.start()
    
    # 启动Flask应用
    flask_thread = threading.Thread(target=start_flask_app, daemon=True)
    flask_thread.start()
    
    print("WeChat2Report 服务已启动，访问以下网址管理：")
    print("* 管理面板:   http://localhost:5000/")
    print("* 原始接口:   http://localhost:8000/")

    while True:
        try:
            handler.decrypt()  # 执行解密操作
            # 开始输出csv
            init_db()
            output.to_csv_all()
            output_directory = "./tmp"  # 输出文件夹
            os.makedirs(output_directory, exist_ok=True)
            clean_chat_logs("messages.csv", output_directory)
            
            output_task()

            #开始归档客户群，先将群聊名称列出来，然后从config文件夹中的tag.json中读取对应的数据，tag.json中存有客户和群聊名称对应关系，如果不在的，自动归为单独的忽略一类，
            #然后将


            # if IsNeedOut:
            #     print("检测到 IsNeedOut 为 True，启动后台输出任务...")
            #     # 创建并启动后台线程执行输出任务
            #     output_thread = threading.Thread(target=background_output_task)
            #     output_thread.start()
            #     IsNeedOut = False

            schedule.run_pending()
        except Exception as e:
            print(f"发生异常: {e}")
        finally:
            time.sleep(600)
