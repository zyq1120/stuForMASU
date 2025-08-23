#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的数据提取和存储模块
基于getlogin.py的成功方法，添加数据库存储功能
支持不同用户的数据管理（新增和更新）
"""

import requests
import hashlib
import json
import re
import time
import uuid
import logging
from bs4 import BeautifulSoup
from datetime import datetime
from database_config import (
    get_db_session, StudentInfo, Course, Exam, Grade, UserSession, StudentCredentials
)

# 设置日志
logger = logging.getLogger(__name__)

class MASUDataExtractor:
    def __init__(self):
        self.session = None
        self.login_url = "https://jwxt.masu.edu.cn/eams/login.action"
        self.base_url = "https://jwxt.masu.edu.cn/eams"
        self.schedule_page_url = "https://jwxt.masu.edu.cn/eams/courseTableForStd.action"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
            'Referer': self.login_url,
            'Origin': 'https://jwxt.masu.edu.cn',
        }
    
    def parse_float(self, value):
        """安全地将字符串转换为Float类型，处理空值和无效值"""
        if not value or value.strip() == '':
            return None
        try:
            return float(value.strip())
        except (ValueError, TypeError):
            return None
        
    def encrypt_password(self, password, prefix):
        """加密密码"""
        return hashlib.sha1((prefix + password).encode('utf-8')).hexdigest()
    
    def login(self, username, password):
        """登录系统"""
        try:
            logger.info(f"开始登录用户: {username}")
            self.session = requests.Session()
            
            # 获取登录页面
            logger.info("正在获取登录页面...")
            resp = self.session.get(self.login_url, headers=self.headers)
            logger.info(f"登录页面响应状态: {resp.status_code}")
            
            if resp.status_code != 200:
                return False, "无法访问登录页面"
            
            # 提取加密前缀
            match = re.search(r"SHA1\('([\w\-]+)-' \+ form\['password'\]", resp.text)
            if not match:
                logger.error("未找到密码加密前缀")
                return False, "未找到密码加密前缀"
            
            password_prefix = match.group(1) + '-'
            logger.info(f"密码加密前缀: {password_prefix}")
            
            # 准备登录数据
            form_data = {
                'username': username,
                'password': self.encrypt_password(password, password_prefix),
                'encodedPassword': '',
                'session_locale': 'zh_CN',
            }
            
            logger.info("准备发送登录请求，等待1秒...")
            time.sleep(1)
            
            # 发送登录请求
            resp = self.session.post(self.login_url, data=form_data, headers=self.headers)
            logger.info(f"登录响应状态码: {resp.status_code}")
            logger.info(f"登录响应URL: {resp.url}")
            
            # 检查登录结果
            login_successful = False
            if resp.status_code == 200:
                if "loginForm" not in resp.text:
                    if "教学管理信息系统" in resp.text and "我的账户" in resp.text:
                        login_successful = True
                        logger.info("登录成功 - 检测到系统主页面")
                    elif not resp.text:
                        logger.warning("登录响应状态码为200，但页面内容为空")
                        login_successful = False
                    else:
                        logger.info("登录响应状态码为200且未找到登录表单，初步认为登录成功")
                        login_successful = True
                else:
                    logger.error("登录失败：在响应页面中找到了登录表单")
                    login_successful = False
            else:
                logger.error(f"登录失败：响应状态码为 {resp.status_code}")
                login_successful = False
            
            if login_successful:
                return True, "登录成功"
            else:
                return False, "登录失败"
                
        except Exception as e:
            logger.error(f"登录时发生错误: {e}")
            return False, f"登录时发生错误: {e}"
    
    def get_student_info(self):
        """获取学生基本信息"""
        try:
            logger.info("开始获取学生信息...")
            
            info = {
                'student_id': '', 'student_name': '', 'major': '', 'department': '', 'grade': '', 'class_name': '',
                'student_type': '', 'enrollment_date': '', 'graduation_date': '', 'study_duration': '',
                'gender': '', 'political_status': '', 'ethnic_group': '', 'health_status': '', 'campus': '',
                'student_status': '', 'is_enrolled': '', 'is_on_campus': '', 'project_type': '',
                'education_level': ''
            }
            
            # 获取学生详细信息
            std_detail_url = self.base_url + '/stdDetail.action'
            logger.info(f"尝试从 {std_detail_url} 获取详细学生信息...")
            resp_detail = self.session.get(std_detail_url, headers=self.headers)
            
            if resp_detail.status_code == 200:
                html_std_detail = resp_detail.text
                soup = BeautifulSoup(html_std_detail, 'html.parser')
                
                # 标签映射（移除student_category）
                label_map = {
                    '学号': 'student_id', '学生号': 'student_id',
                    '姓名': 'student_name', '学生姓名': 'student_name',
                    '院系': 'department', '行政管理院系': 'department',
                    '专业': 'major',
                    '行政班': 'class_name', '班级': 'class_name', '所属班级': 'class_name',
                    '年级': 'grade',
                    '性别': 'gender',
                    '学制': 'study_duration',
                    '项目': 'project_type',
                    '学历层次': 'education_level',
                    '学生类别': 'student_type',
                    '入校时间': 'enrollment_date', '入学日期': 'enrollment_date',
                    '毕业时间': 'graduation_date', '预计毕业时间': 'graduation_date',
                    '是否在籍': 'is_enrolled', '是否有学籍': 'is_enrolled',
                    '是否在校': 'is_on_campus',
                    '所属校区': 'campus',
                    '学籍状态': 'student_status',
                    '民族': 'ethnic_group',
                    '健康状况': 'health_status',
                    '政治面貌': 'political_status'
                }
                
                # 解析表格数据
                found_fields = 0
                for td in soup.find_all('td', class_='title'):
                    label = td.get_text(strip=True).replace('：','').replace(':','')
                    field = label_map.get(label)
                    if field:
                        val_td = td.find_next_sibling('td')
                        if val_td:
                            value = val_td.get_text(strip=True)
                            if value:
                                info[field] = value
                                found_fields += 1
                                logger.info(f"✅ {label}: {value}")
                
                logger.info(f"从表格中找到 {found_fields} 个字段")
                
                # 补充正则兜底
                if not info['student_name']:
                    m = re.search(r'var stdName\s*=\s*["\']([^"\']+)["\'];', html_std_detail)
                    if m:
                        info['student_name'] = m.group(1).strip()
                        logger.info(f"[js] 提取到姓名: {info['student_name']}")
                        
                if not info['student_id']:
                    m = re.search(r'var stdCode\s*=\s*["\']([^"\']+)["\'];', html_std_detail)
                    if m:
                        info['student_id'] = m.group(1).strip()
                        logger.info(f"[js] 提取到学号: {info['student_id']}")
            
            # fallback 多路径
            if not info.get('student_id') or not info.get('student_name'):
                fallback_paths = [
                    '/home.action', '/personInfo.action', '/system/baseinfo.action', '/security/myInfo.action',
                ]
                for path in fallback_paths:
                    url = self.base_url + path
                    try:
                        logger.info(f"尝试后备路径: {url}")
                        resp_fallback = self.session.get(url, headers=self.headers)
                        if resp_fallback.status_code == 200:
                            html_fallback = resp_fallback.text
                            m = re.search(r'<a[^>]*href="/eams/security/my.action"[^>]*>([\u4e00-\u9fa5]+)\((\d+)\)</a>', html_fallback)
                            if m:
                                if not info.get('student_name'):
                                    info['student_name'] = m.group(1).strip()
                                    logger.info(f"[后备] 提取到姓名: {info['student_name']}")
                                if not info.get('student_id'):
                                    info['student_id'] = m.group(2).strip()
                                    logger.info(f"[后备] 提取到学号: {info['student_id']}")
                                break
                    except Exception as e_fallback:
                        logger.error(f"从后备路径 {path} 获取个人信息时发生错误: {e_fallback}")
            
            # 补全所有字段
            for k in info:
                if info[k] is None:
                    info[k] = ''
            logger.info(f"最终获取的学生信息: {info}")
            # 只保留StudentInfo模型支持的字段，彻底过滤无效字段
            valid_fields = {c.name for c in StudentInfo.__table__.columns}
            filtered_info = {k: v for k, v in info.items() if k in valid_fields}
            logger.info(f"过滤后student_info: {filtered_info}")
            return filtered_info
        except Exception as e:
            logger.error(f"获取学生信息时发生错误: {e}")
            return None

    def _parse_js_args(self, args_string):
        """解析 TaskActivity 的参数字符串"""
        args = []
        current = ''
        in_str = False
        str_char = ''
        depth = 0
        for c in args_string:
            if in_str:
                current += c
                if c == str_char:
                    in_str = False
            elif c in ('"', "'"):
                in_str = True
                str_char = c
                current += c
            elif c == ',' and not in_str and depth == 0:
                args.append(current.strip())
                current = ''
            elif c == '(':
                depth += 1
                current += c
            elif c == ')':
                depth -= 1
                current += c
            else:
                current += c
        if current.strip():
            args.append(current.strip())
        # 去除引号
        args = [a[1:-1] if (a.startswith('"') and a.endswith('"')) or (a.startswith("'") and a.endswith("'")) else a for a in args]
        return args

    def parse_schedule_html(self, html_content):
        """解析课表HTML"""
        unit_count_match = re.search(r'var\s+unitCount\s*=\s*(\d+);', html_content)
        unit_count = int(unit_count_match.group(1)) if unit_count_match else 11
        num_days = 7
        chinese_numerals = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一"]
        periods = [f"第{chinese_numerals[i]}节" for i in range(1, unit_count+1)]
        days_map = {0: "星期一", 1: "星期二", 2: "星期三", 3: "星期四", 4: "星期五", 5: "星期六", 6: "星期日"}
        
        # 课程信息收集: (课程名, 教师, 教室, 星期) -> {节次set, 周次set}
        course_dict = {}
        
        for m in re.finditer(r'(var actTeachers\s*=\s*\[.*?\];.*?var assistantName\s*=\s*(["\'])(.*?)\2;.*?)activity\s*=\s*new TaskActivity\((.*?)\);(.*?)(?=activity\s*=|var teachers|$)', html_content, re.DOTALL):
            var_block = m.group(1)
            # actTeachers
            act_teachers_match = re.search(r'var actTeachers\s*=\s*\[(.*?)\];', var_block, re.DOTALL)
            act_teacher_names = []
            if act_teachers_match:
                for n in re.finditer(r'name\s*:\s*["\'](.*?)["\']', act_teachers_match.group(1)):
                    act_teacher_names.append(n.group(1))
            assistant_name = m.group(3) if m.group(3) else ""
            args = self._parse_js_args(m.group(4))
            if len(args) < 10:
                continue
            teacher = args[1]
            if teacher == "actTeacherName.join(',')":
                teacher = ','.join(act_teacher_names)
            course_name = args[3]
            room = args[5]
            weeks = args[6]
            assistant = args[9]
            if assistant == "assistantName":
                assistant = assistant_name
                
            for assign in re.finditer(r'index\s*=\s*(\d+)\*unitCount\+(\d+);\s*table0.activities\[index\]\[.*?\]=activity;', m.group(5)):
                day = int(assign.group(1))
                slot = int(assign.group(2))
                course_name_disp = re.sub(r'\(.*?\)', '', course_name).strip()
                week_list = [i+1 for i, c in enumerate(weeks) if c == '1']
                key = (course_name_disp, teacher, room, days_map[day])
                if key not in course_dict:
                    course_dict[key] = {"periods": set(), "weeks": set()}
                course_dict[key]["periods"].add(periods[slot])
                course_dict[key]["weeks"].update(week_list)
        
        # 整理输出
        result = []
        for (course_name, teacher, room, week_day), v in course_dict.items():
            result.append({
                "course_name": course_name,
                "teacher": teacher,
                "classroom": room,
                "day_of_week": week_day,
                "periods": sorted(v["periods"], key=lambda x: periods.index(x)),
                "weeks": sorted(v["weeks"])
            })
        return result

    def get_schedule_data(self, student_id):
        """获取课程表数据"""
        try:
            logger.info("开始获取课程表数据...")
            schedule_data = []
            
            logger.info(f"尝试获取课表框架页面: {self.schedule_page_url}")
            ajax_referer_url = self.schedule_page_url
            
            # 获取课表页面
            page_headers = self.headers.copy()
            schedule_page_resp = self.session.get(self.schedule_page_url, headers=page_headers)
            schedule_page_resp.raise_for_status()
            
            # 设置AJAX头
            ajax_headers = self.headers.copy()
            ajax_headers['Referer'] = ajax_referer_url
            ajax_headers['X-Requested-With'] = 'XMLHttpRequest'
            
            # 获取project.id
            project_id_payload = {'dataType': 'projectId'}
            project_id_url = f"{self.base_url}/dataQuery.action"
            logger.info(f"尝试获取 project.id 从: {project_id_url}")
            project_id_resp = self.session.post(project_id_url, data=project_id_payload, headers=ajax_headers)
            project_id_resp.raise_for_status()
            project_id = project_id_resp.text.strip()
            logger.info(f"获取到的 project.id: {project_id}")
            
            if not project_id:
                logger.error("错误：未能获取到有效的 project.id")
                return []
            
            # 从课表页面提取ids
            ids_value = None
            try:
                html = schedule_page_resp.text
                m = re.search(r'bg\.form\.addInput\(form,\s*"ids",\s*"(\d+)"\)', html)
                if m:
                    ids_value = m.group(1)
                    logger.info(f"自动提取到课表ids: {ids_value}")
                else:
                    logger.error("未能从课表页面提取到课表ids")
                    return []
            except Exception as e:
                logger.error(f"自动提取课表ids失败: {e}")
                return []
            
            # 获取实际课表数据
            schedule_data_payload = {
                'ids': ids_value,
                'setting.kind': 'std',
                'startWeek': '',
                'project.id': project_id,
                'semester.id': '343',
                'ignoreHead': '1'
            }
            actual_schedule_url = f"{self.base_url}/courseTableForStd!courseTable.action"
            logger.info(f"尝试获取实际课表数据从: {actual_schedule_url}")
            actual_schedule_resp = self.session.post(actual_schedule_url, data=schedule_data_payload, headers=ajax_headers)
            actual_schedule_resp.raise_for_status()
            
            if actual_schedule_resp.text:
                parsed_courses = self.parse_schedule_html(actual_schedule_resp.text)
                logger.info(f"解析到 {len(parsed_courses)} 门课程")
                return parsed_courses
            else:
                logger.warning("课表数据为空")
                return []                
        except Exception as e:
            logger.error(f"获取课程表数据时发生错误: {e}")
            return []

    def get_exam_data(self):
        """获取考试数据"""
        try:
            logger.info("开始获取考试数据...")
            exams = []
            
            # 获取考试批次ID - 尝试多种方法
            exam_batch_ids = []
            exam_main_url = self.base_url + '/stdExamTable.action'
            logger.info(f"尝试从 {exam_main_url} 获取考试批次...")
            resp_main = self.session.get(exam_main_url, headers=self.headers)
            
            if resp_main.status_code == 200:
                html_main = resp_main.text
                soup = BeautifulSoup(html_main, 'html.parser')
                
                # 方法1: 查找select下拉框中的所有批次
                select = soup.find('select', {'id': 'examBatchId'})
                if select:
                    options = select.find_all('option')
                    for option in options:
                        if option.get('value') and option.get('value') != '':
                            exam_batch_ids.append(option.get('value'))
                            logger.info(f"找到考试批次ID: {option.get('value')} - {option.get_text(strip=True)}")
                
                # 方法2: 从JavaScript代码中提取批次ID
                batch_match = re.findall(r'examBatch\.id["\']?\s*[:=]\s*["\']?(\d+)', html_main)
                for batch_id in batch_match:
                    if batch_id not in exam_batch_ids:
                        exam_batch_ids.append(batch_id)
                        logger.info(f"从JS中找到考试批次ID: {batch_id}")
              # 如果没有找到任何批次ID，使用常见的fallback值
            if not exam_batch_ids:
                exam_batch_ids = ['661', '662', '663', '664', '665']  # 从最新的开始尝试
                logger.warning("未找到考试批次ID，使用默认值")
            
            # 遍历所有批次ID获取考试数据
            for exam_batch_id in exam_batch_ids:
                logger.info(f"尝试获取批次 {exam_batch_id} 的考试安排...")
                
                # 获取考试安排
                ajax_url = self.base_url + f'/stdExamTable!examTable.action?examBatch.id={exam_batch_id}'
                try:
                    resp_ajax = self.session.get(ajax_url, headers=self.headers)
                    
                    if resp_ajax.status_code == 200:
                        html_ajax = resp_ajax.text
                        soup = BeautifulSoup(html_ajax, 'html.parser')
                        
                        # 尝试多种表格查找方式
                        exam_tables = []
                        
                        # 方法1: 查找带有class的表格
                        tables_with_class = soup.find_all('table', class_=['gridtable', 'grid', 'table'])
                        exam_tables.extend(tables_with_class)
                        
                        # 方法2: 查找所有表格
                        all_tables = soup.find_all('table')
                        for table in all_tables:
                            if table not in exam_tables:
                                # 检查表格是否包含考试相关内容
                                table_text = table.get_text()
                                if any(keyword in table_text for keyword in ['课程', '考试', '地点', '时间', '座位']):
                                    exam_tables.append(table)
                        
                        batch_exams_found = 0
                        for exam_table in exam_tables:
                            if not exam_table:
                                continue
                                
                            rows = exam_table.find_all('tr')
                            if len(rows) < 2:
                                continue
                                
                            # 获取表头
                            header_row = rows[0]
                            headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
                            logger.info(f"批次 {exam_batch_id} 表格标题: {headers}")
                              # 创建字段映射表（支持多种可能的字段名）
                            field_mapping = {
                                'course_name': ['课程名称', '课程', '科目', '课程名', '考试科目'],
                                'exam_type': ['考试类型', '考试性质', '类型', '考试类别'],
                                'exam_date': ['考试日期', '日期'],
                                'exam_time': ['考试时间', '时间段', '具体时间', '开始时间', '考试安排'],
                                'classroom': ['考试地点', '地点', '考场', '教室', '考试教室'],
                                'seat_number': ['座位号', '座号', '位置', '考试座位', '考场座位号'],
                                'teacher': ['监考教师', '监考', '教师', '监考员']
                            }
                              # 建立字段索引映射
                            field_indices = {}
                            for field, possible_names in field_mapping.items():
                                for idx, header in enumerate(headers):
                                    # 优先匹配更精确的字段名，避免误匹配
                                    if field == 'course_name':
                                        # 课程名称必须精确匹配，避免与课程序号混淆
                                        if header in ['课程名称', '课程名', '科目名称', '考试科目']:
                                            field_indices[field] = idx
                                            break
                                    else:
                                        # 其他字段使用包含匹配
                                        if any(name in header for name in possible_names):
                                            field_indices[field] = idx
                                            break
                            
                            logger.info(f"批次 {exam_batch_id} 字段映射: {field_indices}")
                            
                            # 解析数据行
                            for tr in rows[1:]:
                                tds = tr.find_all('td')
                                if len(tds) < 2:
                                    continue
                                    
                                cells = [td.get_text(strip=True) for td in tds]
                                
                                # 提取考试信息
                                exam_record = {
                                    'course_name': '',
                                    'exam_type': '',
                                    'exam_date': '',
                                    'exam_time': '',
                                    'classroom': '',
                                    'seat_number': '',
                                    'teacher': ''
                                }
                                  # 根据字段映射提取数据
                                for field, idx in field_indices.items():
                                    if idx < len(cells):
                                        value = cells[idx]
                                        if value and value not in ['', '-', '无', '未安排']:
                                            exam_record[field] = value
                                
                                # 记录提取到的原始考试数据
                                if exam_record.get('course_name'):
                                    logger.info(f"[考试原始数据] 课程名: '{exam_record['course_name']}', 类型: '{exam_record.get('exam_type', '')}', 日期: '{exam_record.get('exam_date', '')}'")
                                
                                # 处理时间字段的特殊情况
                                if exam_record['exam_date'] and '至' in exam_record['exam_date']:
                                    # 分离日期和时间
                                    parts = exam_record['exam_date'].split()
                                    if len(parts) >= 2:
                                        exam_record['exam_date'] = parts[0]
                                        if not exam_record['exam_time']:
                                            exam_record['exam_time'] = parts[1]
                                  # 只有在有课程名称的情况下才添加记录
                                if exam_record['course_name']:
                                    exams.append(exam_record)
                                    batch_exams_found += 1
                                    logger.info(f"找到考试: {exam_record['course_name']} - {exam_record['exam_date']} - {exam_record['classroom']}")
                                else:
                                    logger.warning(f"跳过空课程名的考试记录: {exam_record}")
                        
                        logger.info(f"批次 {exam_batch_id} 共找到 {batch_exams_found} 条考试记录")
                    else:
                        logger.warning(f"批次 {exam_batch_id} 请求失败，状态码: {resp_ajax.status_code}")
                        
                except Exception as e:
                    logger.error(f"处理批次 {exam_batch_id} 时发生错误: {e}")
                    continue
            
            logger.info(f"总共解析到 {len(exams)} 条考试安排")
              # 去重处理（基于课程名称和考试日期）
            unique_exams = []
            seen = set()
            for exam in exams:
                key = (exam['course_name'], exam['exam_date'])
                if key not in seen:
                    seen.add(key)
                    unique_exams.append(exam)
            
            logger.info(f"去重后保留 {len(unique_exams)} 条考试安排")
            return unique_exams
            
        except Exception as e:
            logger.error(f"获取考试数据时发生错误: {e}")
            return []

    def get_grades_data(self):
        """获取成绩数据"""
        try:
            logger.info("开始获取成绩数据...")
            grades = []
            
            # 尝试多个成绩页面URL
            grades_urls = [
                self.base_url + '/teach/grade/course/person!historyCourseGrade.action?projectType=MAJOR',
                self.base_url + '/teach/grade/course/person!search.action',
                self.base_url + '/teach/grade/course/person.action',
                self.base_url + '/stdGrade.action'
            ]
            
            for grades_url in grades_urls:
                logger.info(f"尝试从 {grades_url} 获取成绩数据...")
                try:
                    resp = self.session.get(grades_url, headers=self.headers)
                    
                    if resp.status_code == 200:
                        html = resp.text
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # 尝试多种表格查找方式
                        grade_tables = []
                        
                        # 方法1: 查找带有特定class的表格
                        tables_with_class = soup.find_all('table', class_=['gridtable', 'grid', 'table', 'listtable'])
                        grade_tables.extend(tables_with_class)
                        
                        # 方法2: 查找所有表格并筛选包含成绩信息的表格
                        all_tables = soup.find_all('table')
                        for table in all_tables:
                            if table not in grade_tables:
                                table_text = table.get_text()
                                if any(keyword in table_text for keyword in ['课程', '成绩', '学分', '绩点', '学期']):
                                    grade_tables.append(table)
                        
                        page_grades_found = 0
                        for table in grade_tables:
                            if not table:
                                continue
                                
                            rows = table.find_all('tr')
                            if len(rows) < 2:
                                continue
                                
                            # 获取表头
                            header_row = rows[0]
                            headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
                            logger.info(f"成绩表格标题: {headers}")
                            
                            # 创建更完善的字段映射表
                            field_mapping = {
                                'course_name': ['课程名称', '课程', '科目名称', '课程名'],
                                'course_code': ['课程代码', '课程号', '代码', '课程编号'],
                                'credits': ['学分', '学分数'],
                                'grade': ['成绩', '总成绩', '最终成绩', '期末成绩'],
                                'grade_point': ['绩点', '学分绩点', 'GPA'],
                                'semester': ['学期', '开课学期', '学年学期'],
                                'exam_type': ['考试类型', '考核方式', '考试性质'],
                                'course_type': ['课程性质', '课程类型', '课程属性', '性质'],
                                'teacher': ['任课教师', '教师', '授课教师', '主讲教师']
                            }
                              # 建立字段索引映射
                            field_indices = {}
                            for field, possible_names in field_mapping.items():
                                for idx, header in enumerate(headers):
                                    # 优先匹配更精确的字段名
                                    if field == 'course_name':
                                        # 课程名称必须精确匹配，避免与课程代码混淆
                                        if header in ['课程名称', '课程名', '科目名称']:
                                            field_indices[field] = idx
                                            break
                                    elif field == 'course_code':
                                        # 课程代码字段
                                        if header in ['课程代码', '课程号', '代码', '课程编号']:
                                            field_indices[field] = idx
                                            break
                                    else:
                                        # 其他字段使用原有逻辑
                                        for name in possible_names:
                                            if name in header:
                                                field_indices[field] = idx
                                                break
                                        if field in field_indices:
                                            break
                            
                            logger.info(f"成绩字段映射: {field_indices}")
                            
                            # 解析数据行
                            for row in rows[1:]:
                                cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
                                if len(cells) < 2:
                                    continue
                                
                                # 提取成绩信息
                                grade_record = {
                                    'course_name': '',
                                    'course_code': '',
                                    'credits': None,
                                    'grade': '',
                                    'grade_point': None,
                                    'semester': '',
                                    'exam_type': '',
                                    'course_type': '',
                                    'teacher': ''
                                }
                                  # 根据字段映射提取数据
                                for field, idx in field_indices.items():
                                    if idx < len(cells):
                                        value = cells[idx]
                                        if value and value not in ['', '-', '无']:
                                            if field in ['credits', 'grade_point']:
                                                grade_record[field] = self.parse_float(value)
                                            else:
                                                grade_record[field] = value
                                
                                # 记录提取到的原始成绩数据
                                if grade_record.get('course_name'):
                                    logger.info(f"[成绩原始数据] 课程名: '{grade_record['course_name']}', 课程代码: '{grade_record.get('course_code', '')}', 成绩: '{grade_record.get('grade', '')}'")
                                
                                # 尝试从其他字段推断缺失信息
                                if not grade_record['semester']:
                                    # 尝试从其他地方提取学期信息
                                    for cell in cells:
                                        if re.match(r'\d{4}-\d{4}-\d', cell):  # 匹配学期格式如2023-2024-1
                                            grade_record['semester'] = cell
                                            break
                                
                                if not grade_record['course_type']:
                                    # 根据课程名称推断课程类型
                                    course_name = grade_record['course_name']
                                    if '数学' in course_name or '英语' in course_name or '体育' in course_name:
                                        grade_record['course_type'] = '必修课'
                                    elif '选修' in course_name:
                                        grade_record['course_type'] = '选修课'
                                    else:
                                        grade_record['course_type'] = '专业课'
                                  # 只有在有课程名称的情况下才添加记录
                                if grade_record['course_name']:
                                    grades.append(grade_record)
                                    page_grades_found += 1
                                    logger.info(f"找到成绩: {grade_record['course_name']} - {grade_record['grade']} - {grade_record['semester']}")
                                else:
                                    logger.warning(f"跳过空课程名的成绩记录: {grade_record}")
                        
                        if page_grades_found > 0:
                            logger.info(f"从 {grades_url} 找到 {page_grades_found} 条成绩记录")
                            break  # 如果找到数据就不继续尝试其他URL
                        else:
                            logger.warning(f"从 {grades_url} 未找到成绩数据")
                    else:
                        logger.warning(f"访问 {grades_url} 失败，状态码: {resp.status_code}")
                        
                except Exception as e:
                    logger.error(f"处理成绩URL {grades_url} 时发生错误: {e}")
                    continue
            
            logger.info(f"总共解析到 {len(grades)} 条成绩记录")
            
            # 去重处理（基于课程名称和学期）
            unique_grades = []
            seen = set()
            for grade in grades:
                key = (grade['course_name'], grade['semester'])
                if key not in seen:
                    seen.add(key)
                    unique_grades.append(grade)
            
            logger.info(f"去重后保留 {len(unique_grades)} 条成绩记录")
            return unique_grades
            
        except Exception as e:
            logger.error(f"获取成绩数据时发生错误: {e}")
            return []

    def check_user_exists(self, student_id):
        """检查用户是否已存在于数据库中"""
        try:
            db_session = get_db_session()
            existing_student = db_session.query(StudentInfo).filter_by(
                student_id=student_id
            ).first()
            return existing_student is not None
        except Exception as e:
            logger.error(f"检查用户是否存在时发生错误: {e}")
            return False
        finally:
            db_session.close()

    def get_user_from_database(self, student_id):
        """从数据库获取用户信息"""
        try:
            db_session = get_db_session()
            student = db_session.query(StudentInfo).filter_by(
                student_id=student_id
            ).first()
            
            if student:
                # 转换为字典格式
                return {
                    'student_id': student.student_id,
                    'student_name': student.student_name,
                    'major': student.major,
                    'department': student.department,
                    'grade': student.grade,
                    'class_name': student.class_name,                    'updated_at': student.updated_at
                }
            return None
        except Exception as e:
            logger.error(f"从数据库获取用户信息时发生错误: {e}")
            return None
        finally:
            db_session.close()

    def save_to_database(self, student_info, schedule_data, exam_data, grades_data, username=None, password=None):
        """保存数据到数据库"""
        # 只在入口过滤一次，后续全部用 student_info
        valid_student_fields = {c.name for c in StudentInfo.__table__.columns}
        valid_course_fields = {c.name for c in Course.__table__.columns}
        valid_exam_fields = {c.name for c in Exam.__table__.columns}
        valid_grade_fields = {c.name for c in Grade.__table__.columns}
        valid_credential_fields = {c.name for c in StudentCredentials.__table__.columns}
        
        if not isinstance(student_info, dict):
            student_info = dict(student_info)
        student_info = {k: v for k, v in student_info.items() if k in valid_student_fields}
        
        try:
            logger.info(f"原始student_info: {student_info}")
            db_session = get_db_session()
            
            # 保存学生信息
            existing_student = db_session.query(StudentInfo).filter_by(
                student_id=student_info['student_id']
            ).first()
            if existing_student:
                # 更新现有记录
                for key, value in student_info.items():
                    if hasattr(existing_student, key) and value:
                        setattr(existing_student, key, value)
                existing_student.updated_at = datetime.now()
                logger.info(f"更新学生信息: {student_info['student_name']}")
            else:
                # 创建新记录
                new_student = StudentInfo(**student_info)
                db_session.add(new_student)
                logger.info(f"创建新学生记录: {student_info['student_name']}")
            
            # 保存学生登录凭据（学号+姓名+密码）
            if username and password:
                logger.info("正在保存学生登录凭据...")
                existing_credentials = db_session.query(StudentCredentials).filter_by(
                    student_id=student_info['student_id']
                ).first()
                
                if existing_credentials:
                    # 更新现有凭据
                    existing_credentials.student_name = student_info.get('student_name', '')
                    existing_credentials.password = password  # 这里可以考虑加密存储
                    existing_credentials.updated_at = datetime.now()
                    logger.info(f"更新学生凭据: {student_info['student_name']} ({student_info['student_id']})")
                else:
                    # 创建新凭据记录
                    credential_data = {
                        'student_id': student_info['student_id'],
                        'student_name': student_info.get('student_name', ''),
                        'password': password  # 这里可以考虑加密存储
                    }
                    filtered_credential = {k: v for k, v in credential_data.items() if k in valid_credential_fields}
                    new_credentials = StudentCredentials(**filtered_credential)
                    db_session.add(new_credentials)
                    logger.info(f"创建新学生凭据记录: {student_info['student_name']} ({student_info['student_id']})")
            
            # 删除旧的课程、考试、成绩记录
            db_session.query(Course).filter_by(student_id=student_info['student_id']).delete()
            db_session.query(Exam).filter_by(student_id=student_info['student_id']).delete()
            db_session.query(Grade).filter_by(student_id=student_info['student_id']).delete()            # 清理和标准化数据
            logger.info("正在清理和标准化数据...")
            
            # 从课程表数据中提取教师信息映射
            teacher_mapping = self.get_teacher_mapping_from_schedule(schedule_data)
            logger.info(f"建立了 {len(teacher_mapping)} 个教师映射关系")
            
            # 补充成绩数据中的教师信息
            enhanced_grades_data = self.enhance_grades_with_teachers(grades_data, teacher_mapping)
              # 优化课程名称显示
            logger.info("正在优化课程名称显示...")
            
            # 首先处理成绩数据（已有真实中文名）
            improved_grades_data = self.improve_course_names(enhanced_grades_data, 'grade')
            
            # 从成绩数据中构建课程代码到中文名的映射
            course_name_mapping = {}
            for grade in improved_grades_data:
                course_code = grade.get('course_code', '')
                course_name = grade.get('course_name', '')
                if course_code and course_name:
                    course_name_mapping[course_code] = course_name
            
            logger.info(f"构建了 {len(course_name_mapping)} 个课程代码到中文名的映射")
            
            # 使用映射处理考试和课程数据
            improved_schedule_data = self.improve_course_names(schedule_data, 'course', course_name_mapping)
            improved_exam_data = self.improve_course_names(exam_data, 'exam', course_name_mapping)
            
            cleaned_schedule_data = self.clean_data_fields(improved_schedule_data, 'course')
            cleaned_exam_data = self.clean_data_fields(improved_exam_data, 'exam')
            cleaned_grades_data = self.clean_data_fields(improved_grades_data, 'grade')
            
            logger.info(f"清理后数据统计: 课程{len(cleaned_schedule_data)}条, 考试{len(cleaned_exam_data)}条, 成绩{len(cleaned_grades_data)}条")
            
            # 保存课程表数据
            for course in cleaned_schedule_data:
                course['student_id'] = student_info['student_id']
                if 'periods' in course:
                    course['periods'] = json.dumps(course['periods'], ensure_ascii=False)
                if 'weeks' in course:
                    course['weeks'] = json.dumps(course['weeks'], ensure_ascii=False)
                filtered_course = {k: v for k, v in course.items() if k in valid_course_fields}
                new_course = Course(**filtered_course)
                db_session.add(new_course)
            
            # 保存考试数据
            for exam in cleaned_exam_data:
                exam['student_id'] = student_info['student_id']
                filtered_exam = {k: v for k, v in exam.items() if k in valid_exam_fields}
                new_exam = Exam(**filtered_exam)
                db_session.add(new_exam)
            
            # 保存成绩数据
            for grade in cleaned_grades_data:
                grade['student_id'] = student_info['student_id']
                filtered_grade = {k: v for k, v in grade.items() if k in valid_grade_fields}
                new_grade = Grade(**filtered_grade)
                db_session.add(new_grade)
            db_session.commit()
            logger.info("数据保存成功")
            return True, "数据保存成功"
        except Exception as e:
            db_session.rollback()
            logger.error(f"保存数据时发生错误: {e}", exc_info=True)
            return False, f"保存数据时发生错误: {e}"
        finally:
            db_session.close()

    def create_user_session(self, student_id, student_name):
        """创建用户会话"""
        try:
            db_session = get_db_session()
            
            # 生成会话ID
            session_id = str(uuid.uuid4())
            
            # 清除该用户的旧会话
            db_session.query(UserSession).filter_by(student_id=student_id).delete()
            
            # 创建新会话
            new_session = UserSession(
                session_id=session_id,
                student_id=student_id,
                student_name=student_name
            )
            db_session.add(new_session)
            db_session.commit()
            
            logger.info(f"用户会话创建成功: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"创建用户会话时发生错误: {e}")
            return None
        finally:
            db_session.close()

    def extract_and_save_all_data(self, username, password):
        """提取并保存所有数据"""
        logger.info(f"开始为用户 {username} 提取和保存数据")
        
        # 步骤0: 检查用户是否已存在
        logger.info("步骤0: 检查用户是否已存在于数据库中")
        user_exists = self.check_user_exists(username)
        if user_exists:
            existing_user = self.get_user_from_database(username)
            logger.info(f"用户 {username} 已存在: {existing_user.get('student_name', '未知')} - 将更新数据")
        else:
            logger.info(f"用户 {username} 不存在 - 将创建新记录")
        
        # 登录
        logger.info("步骤1: 登录系统")
        success, message = self.login(username, password)
        if not success:
            logger.error(f"登录失败: {message}")
            return False, f"登录失败: {message}"
        logger.info(f"登录成功: {message}")
        
        # 获取学生信息
        logger.info("步骤2: 获取学生信息")
        student_info = self.get_student_info()
        if not student_info:
            logger.error("获取学生信息失败: 返回None")
            return False, "无法获取学生信息"
        
        if not student_info.get('student_id'):
            logger.error(f"获取学生信息失败: 缺少学号 - {student_info}")
            return False, "无法获取学生学号"
        
        # 验证学号是否匹配
        extracted_student_id = student_info.get('student_id')
        if extracted_student_id != username:
            logger.warning(f"警告: 登录用户名({username})与提取到的学号({extracted_student_id})不匹配")
            # 继续处理，但使用提取到的学号
            username = extracted_student_id
        
        logger.info(f"成功获取学生信息: {student_info.get('student_name')} ({student_info.get('student_id')})")
        
        # 获取其他数据
        logger.info("步骤3: 获取课程表数据")
        schedule_data = self.get_schedule_data(student_info['student_id'])
        schedule_count = len(schedule_data) if schedule_data else 0
        logger.info(f"获取到 {schedule_count} 条课程记录")
        
        logger.info("步骤4: 获取考试数据")
        exam_data = self.get_exam_data()
        exam_count = len(exam_data) if exam_data else 0
        logger.info(f"获取到 {exam_count} 条考试记录")
        
        logger.info("步骤5: 获取成绩数据")
        grades_data = self.get_grades_data()
        grades_count = len(grades_data) if grades_data else 0
        logger.info(f"获取到 {grades_count} 条成绩记录")
          # 保存到数据库
        logger.info("步骤6: 保存数据到数据库")
        success, message = self.save_to_database(student_info, schedule_data, exam_data, grades_data, username, password)
        if not success:
            logger.error(f"保存数据失败: {message}")
            return False, f"保存数据失败: {message}"
        
        action_type = "更新" if user_exists else "新增"
        logger.info(f"数据保存成功 - {action_type}了用户 {student_info.get('student_name')} 的数据")
        
        # 创建用户会话
        logger.info("步骤7: 创建用户会话")
        session_id = self.create_user_session(
            student_info['student_id'], 
            student_info['student_name']
        )
        
        if session_id:
            logger.info(f"用户会话创建成功: {session_id}")
            return True, {
                'message': f'数据获取和保存成功 - {action_type}用户数据',
                'session_id': session_id,
                'student_info': student_info,
                'data_summary': {
                    'courses': schedule_count,
                    'exams': exam_count,
                    'grades': grades_count
                },
                'action_type': action_type,
                'user_existed': user_exists
            }
        else:
            logger.error("创建用户会话失败")
            return False, "创建用户会话失败"

    def extract_and_save_data(self, username, password=None):
        """为Web应用提供的公共接口方法"""
        # 添加错误处理和验证
        if not username or username.strip() == '':
            return False, "用户名不能为空"
        
        username = username.strip()
        
        # 如果没有提供密码，尝试使用已知的测试账户
        if password is None:
            if username == "242040338":
                password = "Liu112613"
                logger.info(f"使用测试密码登录用户: {username}")
            else:
                return False, f"用户 {username} 需要提供密码"
        
        # 记录操作开始
        logger.info(f"开始处理用户: {username}")
        start_time = datetime.now()
        
        try:
            # 调用主要的数据提取和保存方法
            success, result = self.extract_and_save_all_data(username, password)
            
            # 记录操作结果
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            if success:
                logger.info(f"用户 {username} 数据处理成功，耗时 {duration:.2f} 秒")
                if isinstance(result, dict):
                    result['processing_time'] = duration
                    result['timestamp'] = end_time.isoformat()
            else:
                logger.error(f"用户 {username} 数据处理失败，耗时 {duration:.2f} 秒: {result}")
            
            return success, result
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            error_msg = f"处理用户 {username} 时发生异常: {str(e)}"
            logger.error(f"{error_msg}，耗时 {duration:.2f} 秒")
            return False, error_msg

    def get_user_data_summary(self, student_id):
        """获取用户数据摘要"""
        try:
            db_session = get_db_session()
            
            # 获取学生信息
            student = db_session.query(StudentInfo).filter_by(student_id=student_id).first()
            if not student:
                return None
            
            # 统计各类数据数量
            courses_count = db_session.query(Course).filter_by(student_id=student_id).count()
            exams_count = db_session.query(Exam).filter_by(student_id=student_id).count()
            grades_count = db_session.query(Grade).filter_by(student_id=student_id).count()
            
            return {
                'student_id': student.student_id,
                'student_name': student.student_name,
                'major': student.major,
                'department': student.department,
                'courses_count': courses_count,
                'exams_count': exams_count,
                'grades_count': grades_count,
                'last_updated': student.updated_at.isoformat() if student.updated_at else None
            }
            
        except Exception as e:
            logger.error(f"获取用户数据摘要时发生错误: {e}")
            return None
        finally:
            db_session.close()

    def clean_data_fields(self, data_list, data_type):
        """清理和标准化数据字段"""
        cleaned_data = []
        
        for item in data_list:
            cleaned_item = item.copy()
            
            if data_type == 'exam':
                # 处理考试数据的默认值
                if not cleaned_item.get('exam_date') or cleaned_item['exam_date'] in ['', '时间未安排', '未安排']:
                    cleaned_item['exam_date'] = '时间未安排'
                if not cleaned_item.get('exam_time') or cleaned_item['exam_time'] in ['', '时间未安排', '未安排']:
                    cleaned_item['exam_time'] = '时间未安排'
                if not cleaned_item.get('classroom') or cleaned_item['classroom'] in ['', '地点未安排', '未安排']:
                    cleaned_item['classroom'] = '地点未安排'
                if not cleaned_item.get('exam_type'):
                    cleaned_item['exam_type'] = '期末考试'
                if not cleaned_item.get('seat_number'):
                    cleaned_item['seat_number'] = ''
                if not cleaned_item.get('teacher'):
                    cleaned_item['teacher'] = ''
                    
            elif data_type == 'grade':
                # 处理成绩数据的默认值
                if not cleaned_item.get('semester'):
                    # 根据当前时间推断学期
                    current_year = datetime.now().year
                    current_month = datetime.now().month
                    if current_month >= 9:  # 9月以后是上学期
                        cleaned_item['semester'] = f'{current_year}-{current_year+1}-1'
                    elif current_month <= 2:  # 2月以前是上学期
                        cleaned_item['semester'] = f'{current_year-1}-{current_year}-1'
                    else:  # 3-8月是下学期
                        cleaned_item['semester'] = f'{current_year-1}-{current_year}-2'
                        
                if not cleaned_item.get('exam_type'):
                    cleaned_item['exam_type'] = '期末考试'
                if not cleaned_item.get('course_type'):
                    # 根据课程名称智能推断课程类型
                    course_name = cleaned_item.get('course_name', '')
                    if any(keyword in course_name for keyword in ['马克思', '毛泽东', '思想', '政治', '形势', '党']):
                        cleaned_item['course_type'] = '思政课'
                    elif any(keyword in course_name for keyword in ['数学', '高等数学', '线性代数', '概率', '统计']):
                        cleaned_item['course_type'] = '数学基础课'
                    elif any(keyword in course_name for keyword in ['英语', '外语']):
                        cleaned_item['course_type'] = '外语课'
                    elif any(keyword in course_name for keyword in ['体育', '运动']):
                        cleaned_item['course_type'] = '体育课'
                    elif any(keyword in course_name for keyword in ['计算机', '编程', 'Java', 'Python', '数据库', '算法', '软件']):
                        cleaned_item['course_type'] = '专业课'
                    else:
                        cleaned_item['course_type'] = '专业课'
                        
                if not cleaned_item.get('teacher'):
                    cleaned_item['teacher'] = ''
                    
            elif data_type == 'course':
                # 处理课程数据的默认值
                if not cleaned_item.get('teacher'):
                    cleaned_item['teacher'] = ''
                if not cleaned_item.get('classroom'):
                    cleaned_item['classroom'] = ''
                    
            cleaned_data.append(cleaned_item)
            
        return cleaned_data

    def get_teacher_mapping_from_schedule(self, schedule_data):
        """从课程表数据中提取课程-教师映射关系"""
        teacher_mapping = {}
        
        for course in schedule_data:
            course_name = course.get('course_name', '')
            teacher = course.get('teacher', '')
            
            if course_name and teacher:
                # 清理课程名称（去除括号内容等）
                clean_course_name = re.sub(r'\(.*?\)', '', course_name).strip()
                teacher_mapping[clean_course_name] = teacher                # 也尝试用原始课程名映射
                teacher_mapping[course_name] = teacher                
                logger.info(f"建立教师映射: {clean_course_name} → {teacher}")
        
        return teacher_mapping

    def enhance_grades_with_teachers(self, grades_data, teacher_mapping=None):
        """使用真实的教师映射关系补充成绩数据中的教师信息，只使用真实数据，不使用模拟信息"""
        enhanced_grades = []
        
        for grade in grades_data:
            enhanced_grade = grade.copy()
            course_name = grade.get('course_name', '')
            course_code = grade.get('course_code', '')
              # 只有在课程表映射中找到真实教师时才补充，否则保持为空
            if not enhanced_grade.get('teacher') and teacher_mapping:
                teacher = None
                
                # 1. 直接匹配课程名称
                if course_name in teacher_mapping:
                    teacher = teacher_mapping[course_name]
                    logger.info(f"✅ 课程表直接匹配找到真实教师: {course_name} → {teacher}")
                
                # 2. 模糊匹配（仅匹配有意义的关键词）
                if not teacher:
                    for mapped_course, mapped_teacher in teacher_mapping.items():
                        if course_name and mapped_course and len(course_name) > 2:
                            # 检查课程名称是否包含在课程表的课程名中，或反之
                            # 排除纯数字的课程代码进行匹配
                            if not course_name.isdigit() and not mapped_course.isdigit():
                                if course_name in mapped_course or mapped_course in course_name:
                                    teacher = mapped_teacher
                                    logger.info(f"✅ 课程表模糊匹配找到真实教师: {course_name} → {mapped_course} → {teacher}")
                                    break
                
                # 只有找到真实教师才赋值，否则保持为空
                if teacher:
                    enhanced_grade['teacher'] = teacher
                    logger.info(f"✅ 成功补充真实教师信息: {course_name}({course_code}) → {teacher}")
                else:
                    # 不使用任何模拟或备用信息，保持为空
                    enhanced_grade['teacher'] = ''
                    logger.info(f"ℹ️ 未找到真实教师信息，保持为空: {course_name}({course_code})")
            
            enhanced_grades.append(enhanced_grade)
        
        # 统计补全效果
        total_courses = len(enhanced_grades)
        real_teachers = sum(1 for g in enhanced_grades if g.get('teacher'))
        coverage = real_teachers / total_courses * 100 if total_courses > 0 else 0
        
        logger.info(f"真实教师信息补全统计:")
        logger.info(f"  总课程数: {total_courses}")
        logger.info(f"  找到真实教师: {real_teachers} ({coverage:.1f}%)")
        logger.info(f"  未找到教师: {total_courses - real_teachers} ({100 - coverage:.1f}%)")
        
        return enhanced_grades
    
    def improve_course_names(self, data_list, data_type, course_name_mapping=None):
        """过滤课程数据 - 只保留真实的中文课程名，删除课程代码格式的数据"""
        logger.info(f"开始过滤 {data_type} 数据，原始数据量: {len(data_list)}")
        improved_data = []
        
        def is_course_code_format(name):
            """判断是否为课程代码格式"""
            if not name:
                return False
            # 检查是否为纯数字格式（如 04212001）
            if re.match(r'^\d{8}$', name):
                return True
            # 检查是否为序号.课程代码格式（如 1.04212001）
            if '.' in name and len(name.split('.')) >= 2:
                code_part = name.split('.')[1].strip()
                if re.match(r'^\d{8}$', code_part):
                    return True
            # 检查是否为复杂的考试代码格式（如 202420252.04212004.009）
            if '.' in name and len(name.split('.')) >= 3:
                parts = name.split('.')
                if len(parts) >= 2 and re.match(r'^\d{8}$', parts[1]):
                    return True
            return False
            
        def extract_course_code(name):
            """从课程名中提取课程代码"""
            if not name:
                return None
            # 检查是否为纯数字格式（如 04212001）
            if re.match(r'^\d{8}$', name):
                return name
            # 检查是否为序号.课程代码格式（如 1.04212001）
            if '.' in name and len(name.split('.')) >= 2:
                code_part = name.split('.')[1].strip()
                if re.match(r'^\d{8}$', code_part):
                    return code_part
            # 检查是否为复杂的考试代码格式（如 202420252.04212004.009）
            if '.' in name and len(name.split('.')) >= 3:
                parts = name.split('.')
                if len(parts) >= 2 and re.match(r'^\d{8}$', parts[1]):
                    return parts[1]
            return None
        
        for item in data_list:
            improved_item = item.copy()
            original_course_name = improved_item.get('course_name', '')
            
            # 记录原始课程名称
            logger.info(f"[课程名称检查] 原始课程名: '{original_course_name}', 数据类型: {data_type}")
              # 只保留真实的中文课程名，删除课程代码格式
            should_keep = False
            
            if original_course_name:
                if data_type == 'exam':
                    # 考试数据中的课程名称列本身就是真实中文名，直接保留
                    should_keep = True
                    logger.info(f"✅ {data_type}保留考试数据的真实中文名: '{original_course_name}'")
                elif is_course_code_format(original_course_name):
                    # 是课程代码格式，尝试从映射中获取中文名
                    course_code = extract_course_code(original_course_name)
                    if course_name_mapping and course_code in course_name_mapping:
                        chinese_name = course_name_mapping[course_code]
                        improved_item['course_name'] = chinese_name
                        should_keep = True
                        logger.info(f"✅ {data_type}映射课程代码到中文名: '{original_course_name}' -> '{chinese_name}'")
                    else:
                        # 没有找到精确映射，不使用模糊匹配，直接删除
                        should_keep = False
                        logger.info(f"❌ {data_type}删除课程代码格式: '{original_course_name}' (无精确映射，不使用模拟数据)")
                else:
                    # 已经是真实中文名称，保留
                    should_keep = True
                    logger.info(f"✅ {data_type}保留真实中文名: '{original_course_name}'")
            else:
                logger.info(f"⚠️ {data_type}课程名为空，跳过")
            
            # 只有真实中文课程名才添加到结果中
            if should_keep:
                improved_data.append(improved_item)
        
        logger.info(f"📊 {data_type}数据过滤结果: 原始{len(data_list)}条 → 保留{len(improved_data)}条")
        return improved_data

if __name__ == "__main__":
    # 测试课程名称修复功能
    print("🎯 开始测试数据提取和课程名称修复功能")
    print("=" * 60)
    
    extractor = MASUDataExtractor()
      # 检查命令行参数
    import sys
    if len(sys.argv) >= 3:
        test_username = sys.argv[1]
        test_password = sys.argv[2]
    else:
        # 使用默认测试账号：242040390
        test_username = "242040390"
        test_password = "Zzhouyu007"
    
    print(f"📋 测试账号: {test_username}")
    print(f"🔑 测试密码: {test_password}")
    print("🔄 开始数据提取...")
    
    try:
        success, result = extractor.extract_and_save_all_data(test_username, test_password)
        
        if success:
            print("✅ 数据提取成功!")
            print(f"📊 处理结果: {result['message']}")
            
            if 'student_info' in result:
                student_info = result['student_info']
                print(f"\n👤 学生信息:")
                print(f"  学号: {student_info.get('student_id', 'N/A')}")
                print(f"  姓名: {student_info.get('student_name', 'N/A')}")
                print(f"  专业: {student_info.get('major', 'N/A')}")
                print(f"  班级: {student_info.get('class_name', 'N/A')}")
            
            if 'data_summary' in result:
                summary = result['data_summary']
                print(f"\n📈 数据统计:")
                print(f"  课程数: {summary.get('courses', 0)}")
                print(f"  考试数: {summary.get('exams', 0)}")
                print(f"  成绩数: {summary.get('grades', 0)}")
            
            if 'processing_time' in result:
                print(f"\n⏱️ 处理耗时: {result['processing_time']:.2f} 秒")
                
        else:
            print(f"❌ 数据提取失败: {result}")
            
    except Exception as e:
        print(f"💥 异常发生: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🎉 测试完成!")
