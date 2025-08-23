#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的RESTful API服务器
只提供一个接口：POST /extract 接收学号和密码，爬取数据并存储到数据库
"""

from flask import Flask, request, jsonify
import logging
import traceback
from datetime import datetime
import os
import sys

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_extractor import MASUDataExtractor
from database_config import init_database

# 创建Flask应用
app = Flask(__name__)

# 配置日志
def setup_logging():
    """设置详细的日志配置（按日期命名日志文件）"""
    import atexit
    from datetime import datetime
    log_dir = os.path.abspath('logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_file = os.path.join(log_dir, f"api_{datetime.now().strftime('%Y%m%d')}.log")
    log_format = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    root_logger = logging.getLogger()
    root_logger.handlers.clear()  # 防止重复添加
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(log_format)
    file_handler.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.INFO)
    # 强制flush
    def flush_log():
        file_handler.flush()
    atexit.register(flush_log)
    logging.info(f"【日志测试】setup_logging已执行，日志文件: {log_file}")

# 初始化日志
setup_logging()
logging.info("【日志测试】主入口已执行")

print("【代码热加载测试】api_server.py 已被执行")

@app.route('/extract', methods=['POST'])
def extract_student_data():
    logging.info("【日志测试】收到/extract请求")
    """
    提取学生数据API接口
    POST /extract
    参数：
    - student_id: 学号
    - password: 密码
    """
    try:
        # 记录请求开始
        request_time = datetime.now()
        app.logger.info(f"收到数据提取请求 - 时间: {request_time}")
        
        # 获取请求数据
        if not request.is_json:
            app.logger.error("请求格式错误: 不是JSON格式")
            return jsonify({
                'success': False,
                'message': '请求必须是JSON格式',
                'timestamp': request_time.isoformat()
            }), 400
        
        data = request.get_json()
        app.logger.info(f"请求数据: {data}")
        
        # 验证必填参数
        student_id = data.get('student_id', '').strip()
        password = data.get('password', '').strip()
        
        if not student_id:
            app.logger.error("参数错误: 学号为空")
            return jsonify({
                'success': False,
                'message': '学号不能为空',
                'timestamp': request_time.isoformat()
            }), 400
        
        if not password:
            app.logger.error(f"参数错误: 用户{student_id}密码为空")
            return jsonify({
                'success': False,
                'message': '密码不能为空',
                'timestamp': request_time.isoformat()
            }), 400
        
        app.logger.info(f"开始处理用户: {student_id}")
        
        # 创建数据提取器实例
        extractor = MASUDataExtractor()
        app.logger.info("数据提取器实例创建成功")
        
        # 执行数据提取和保存
        success, result = extractor.extract_and_save_data(student_id, password)
        
        # 计算处理时间
        end_time = datetime.now()
        processing_time = (end_time - request_time).total_seconds()
        
        if success:
            app.logger.info(f"用户 {student_id} 数据处理成功，耗时 {processing_time:.2f} 秒")
            
            # 构建成功响应
            response_data = {
                'success': True,
                'message': '数据提取和保存成功',
                'student_id': student_id,
                'processing_time': processing_time,
                'timestamp': end_time.isoformat()
            }
            
            # 如果result是字典，添加详细信息
            if isinstance(result, dict):
                response_data.update({
                    'action_type': result.get('action_type', 'unknown'),
                    'user_existed': result.get('user_existed', False),
                    'data_summary': result.get('data_summary', {}),
                    'student_info': {
                        'student_name': result.get('student_info', {}).get('student_name', ''),
                        'major': result.get('student_info', {}).get('major', ''),
                        'department': result.get('student_info', {}).get('department', '')
                    }
                })
            
            return jsonify(response_data), 200
        
        else:
            app.logger.error(f"用户 {student_id} 数据处理失败，耗时 {processing_time:.2f} 秒: {result}")
            
            return jsonify({
                'success': False,
                'message': f'数据提取失败: {result}',
                'student_id': student_id,
                'processing_time': processing_time,
                'timestamp': end_time.isoformat()
            }), 500
    
    except Exception as e:
        # 记录详细错误信息
        error_time = datetime.now()
        error_msg = str(e)
        error_trace = traceback.format_exc()
        
        app.logger.error(f"API处理异常 - 时间: {error_time}")
        app.logger.error(f"错误信息: {error_msg}")
        app.logger.error(f"错误堆栈:\n{error_trace}")
        
        return jsonify({
            'success': False,
            'message': f'服务器内部错误: {error_msg}',
            'timestamp': error_time.isoformat()
        }), 500

@app.route('/api/exam/<student_id>', methods=['GET'])
def get_exam_data(student_id):
    """获取学生考试数据"""
    try:
        from database_config import get_db_session, Exam
        
        db_session = get_db_session()
        exams = db_session.query(Exam).filter_by(student_id=student_id).all()
        
        exam_list = []
        for exam in exams:
            exam_data = {
                'course_name': exam.course_name,
                'exam_type': exam.exam_type,
                'exam_date': exam.exam_date,
                'exam_time': exam.exam_time,
                'classroom': exam.classroom,
                'seat_number': exam.seat_number,
                'teacher': exam.teacher
            }
            exam_list.append(exam_data)
        
        db_session.close()
        
        return jsonify(exam_list), 200
        
    except Exception as e:
        logging.error(f"获取考试数据失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取考试数据失败: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/grade/<student_id>', methods=['GET'])
def get_grade_data(student_id):
    """获取学生成绩数据"""
    try:
        from database_config import get_db_session, Grade
        
        db_session = get_db_session()
        grades = db_session.query(Grade).filter_by(student_id=student_id).all()
        
        grade_list = []
        for grade in grades:
            grade_data = {
                'course_name': grade.course_name,
                'course_code': grade.course_code,
                'credits': grade.credits,
                'grade': grade.grade,
                'grade_point': grade.grade_point,
                'semester': grade.semester,
                'exam_type': grade.exam_type,
                'course_type': grade.course_type,
                'teacher': grade.teacher
            }
            grade_list.append(grade_data)
        
        db_session.close()
        
        return jsonify(grade_list), 200
        
    except Exception as e:
        logging.error(f"获取成绩数据失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取成绩数据失败: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/course/<student_id>', methods=['GET'])
def get_course_data(student_id):
    """获取学生课程数据"""
    try:
        from database_config import get_db_session, Course
        import json
        
        db_session = get_db_session()
        courses = db_session.query(Course).filter_by(student_id=student_id).all()
        
        course_list = []
        for course in courses:
            course_data = {
                'course_name': course.course_name,
                'teacher': course.teacher,
                'classroom': course.classroom,
                'day_of_week': course.day_of_week,
                'periods': json.loads(course.periods) if course.periods else [],
                'weeks': json.loads(course.weeks) if course.weeks else []
            }
            course_list.append(course_data)
        
        db_session.close()
        
        return jsonify(course_list), 200
        
    except Exception as e:
        logging.error(f"获取课程数据失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取课程数据失败: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    logging.info("【日志测试】收到/health请求")
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'student-data-extractor'
    }), 200

@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return jsonify({
        'success': False,
        'message': '接口不存在',
        'available_endpoints': [
            '/extract (POST)', 
            '/health (GET)',
            '/api/exam/<student_id> (GET)',
            '/api/grade/<student_id> (GET)', 
            '/api/course/<student_id> (GET)'
        ],
        'timestamp': datetime.now().isoformat()
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    """405错误处理"""
    return jsonify({
        'success': False,
        'message': '请求方法不被允许',
        'note': '/extract接口只支持POST请求',
        'timestamp': datetime.now().isoformat()
    }), 405

if __name__ == '__main__':
    logging.info("【日志测试】Flask主进程启动")
    # 启动前自动初始化数据库和表
    app.logger.info("[自动初始化] 正在检测并创建数据库及表...")
    db_init_ok = init_database()
    if db_init_ok:
        app.logger.info("[自动初始化] 数据库和表结构已就绪！")
    else:
        app.logger.error("[自动初始化] 数据库或表结构初始化失败，请检查配置和MySQL服务！")

    app.logger.info("正在启动学生数据提取API服务器...")
    app.logger.info("可用接口:")
    app.logger.info("  POST /extract - 提取学生数据")
    app.logger.info("  GET  /health  - 健康检查")
    
    # 启动服务器
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,  # 生产环境关闭调试模式
        threaded=True
    )
