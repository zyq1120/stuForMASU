#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据查询服务器 - 运行在8081端口
提供学生数据查询API接口
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import traceback
from datetime import datetime
import os
import sys

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database_config import get_db_session, StudentInfo, Course, Exam, Grade

# 创建Flask应用
app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    handlers=[
        logging.FileHandler('logs/data_query.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'message': '数据查询服务运行正常',
        'timestamp': datetime.now().isoformat(),
        'service': 'data-query-server'
    }), 200

@app.route('/info', methods=['GET'])
def get_student_info():
    """获取学生基本信息"""
    try:
        student_id = request.args.get('studentId')
        if not student_id:
            return jsonify({
                'code': 400,
                'message': '学号参数缺失',
                'data': None
            }), 400
        
        db_session = get_db_session()
        student = db_session.query(StudentInfo).filter_by(student_id=student_id).first()
        
        if not student:
            db_session.close()
            return jsonify({
                'code': 404,
                'message': '未找到该学生信息',
                'data': None
            }), 404
        
        student_info = {
            'studentId': student.student_id,
            'studentName': student.student_name or '',
            'major': student.major or '',
            'department': student.department or '',
            'grade': student.grade or '',
            'className': student.class_name or ''
        }
        
        db_session.close()
        
        return jsonify({
            'code': 200,
            'message': '操作成功',
            'data': student_info
        }), 200
        
    except Exception as e:
        logging.error(f"获取学生信息失败: {e}")
        return jsonify({
            'code': 500,
            'message': f'服务器错误: {str(e)}',
            'data': None
        }), 500

@app.route('/courses', methods=['GET'])
def get_courses():
    """获取课程数据"""
    try:
        student_id = request.args.get('studentId')
        if not student_id:
            return jsonify({
                'code': 400,
                'message': '学号参数缺失',
                'data': []
            }), 400
        
        db_session = get_db_session()
        courses = db_session.query(Course).filter_by(student_id=student_id).all()
        
        course_list = []
        for course in courses:
            course_data = {
                'id': course.id,
                'courseName': course.course_name or '',
                'teacher': course.teacher or '',
                'classroom': course.classroom or '',
                'dayOfWeek': course.day_of_week or '',
                'periods': course.periods or '[]',
                'weeks': course.weeks or '[]'
            }
            course_list.append(course_data)
        
        db_session.close()
        
        return jsonify({
            'code': 200,
            'message': '操作成功',
            'data': course_list
        }), 200
        
    except Exception as e:
        logging.error(f"获取课程数据失败: {e}")
        return jsonify({
            'code': 500,
            'message': f'服务器错误: {str(e)}',
            'data': []
        }), 500

@app.route('/exams', methods=['GET'])
def get_exams():
    """获取考试数据"""
    try:
        student_id = request.args.get('studentId')
        if not student_id:
            return jsonify({
                'code': 400,
                'message': '学号参数缺失',
                'data': []
            }), 400
        
        db_session = get_db_session()
        exams = db_session.query(Exam).filter_by(student_id=student_id).all()
        
        exam_list = []
        for exam in exams:
            exam_data = {
                'id': exam.id,
                'courseName': exam.course_name or '',
                'examType': exam.exam_type or '',
                'examDate': exam.exam_date or '',
                'examTime': exam.exam_time or '',
                'classroom': exam.classroom or '',
                'seatNumber': exam.seat_number or '',
                'teacher': exam.teacher or ''
            }
            exam_list.append(exam_data)
        
        db_session.close()
        
        return jsonify({
            'code': 200,
            'message': '操作成功',
            'data': exam_list
        }), 200
        
    except Exception as e:
        logging.error(f"获取考试数据失败: {e}")
        return jsonify({
            'code': 500,
            'message': f'服务器错误: {str(e)}',
            'data': []
        }), 500

@app.route('/grades', methods=['GET'])
def get_grades():
    """获取成绩数据"""
    try:
        student_id = request.args.get('studentId')
        if not student_id:
            return jsonify({
                'code': 400,
                'message': '学号参数缺失',
                'data': []
            }), 400
        
        logging.info(f"获取学号 {student_id} 的成绩数据")
        
        db_session = get_db_session()
        grades = db_session.query(Grade).filter_by(student_id=student_id).all()
        
        logging.info(f"查询到 {len(grades)} 条成绩记录")
        
        grade_list = []
        for grade in grades:
            grade_data = {
                'id': grade.id,
                'courseName': grade.course_name or '',
                'courseCode': grade.course_code or '',
                'credits': float(grade.credits) if grade.credits else 0.0,
                'score': grade.grade or '',
                'gradePoint': float(grade.grade_point) if grade.grade_point else 0.0,
                'semester': grade.semester or '',
                'examType': grade.exam_type or '',
                'courseType': grade.course_type or '',
                'teacher': grade.teacher or ''
            }
            grade_list.append(grade_data)
            logging.info(f"课程: {grade_data['courseName']}, 成绩: {grade_data['score']}")
        
        db_session.close()
        
        logging.info(f"返回 {len(grade_list)} 条成绩数据")
        
        return jsonify({
            'code': 200,
            'message': '操作成功',
            'data': grade_list
        }), 200
        
    except Exception as e:
        logging.error(f"获取成绩数据失败: {e}")
        logging.error(traceback.format_exc())
        return jsonify({
            'code': 500,
            'message': f'服务器错误: {str(e)}',
            'data': []
        }), 500

@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return jsonify({
        'code': 404,
        'message': '接口不存在',
        'available_endpoints': [
            '/health (GET)',
            '/info?studentId=<id> (GET)',
            '/courses?studentId=<id> (GET)',
            '/exams?studentId=<id> (GET)',
            '/grades?studentId=<id> (GET)'
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    return jsonify({
        'code': 500,
        'message': '服务器内部错误',
        'timestamp': datetime.now().isoformat()
    }), 500

if __name__ == '__main__':
    logging.info("正在启动数据查询服务器...")
    logging.info("可用接口:")
    logging.info("  GET  /health - 健康检查")
    logging.info("  GET  /info?studentId=<id> - 获取学生信息")
    logging.info("  GET  /courses?studentId=<id> - 获取课程数据")
    logging.info("  GET  /exams?studentId=<id> - 获取考试数据")
    logging.info("  GET  /grades?studentId=<id> - 获取成绩数据")
    
    # 创建日志目录
    os.makedirs('logs', exist_ok=True)
    
    # 启动服务器
    app.run(
        host='0.0.0.0',
        port=8081,
        debug=False,
        threaded=True
    )
