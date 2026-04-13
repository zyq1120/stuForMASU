# 马鞍山大学教务系统数据库配置
"""
数据库配置文件
包含数据库连接参数和表结构定义
"""

import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import pymysql

# 数据库配置
DATABASE_CONFIG = {
    'host': os.getenv('DATABASE_HOST', ''),
    'port': int(os.getenv('DATABASE_PORT', 3306)),
    'user': os.getenv('DATABASE_USER', 'root'),
    'password': os.getenv('DATABASE_PASSWORD', 'newpassword'),
    'database': os.getenv('DATABASE_NAME', 'masu_system'),
    'charset': 'utf8mb4'
}

# 创建数据库引擎
def get_database_url():
    return f"mysql+pymysql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}?charset={DATABASE_CONFIG['charset']}"

# 创建基类
Base = declarative_base()

# 学生信息表
class StudentInfo(Base):
    __tablename__ = 'student_info'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(20), unique=True, nullable=False, comment='学号')
    student_name = Column(String(50), nullable=False, comment='姓名')
    major = Column(String(100), comment='专业')
    department = Column(String(100), comment='院系')
    grade = Column(String(10), comment='年级')
    class_name = Column(String(50), comment='班级')
    gender = Column(String(10), comment='性别')
    study_duration = Column(String(10), comment='学制')
    project_type = Column(String(50), comment='项目类型')
    education_level = Column(String(50), comment='学历层次')
    student_type = Column(String(50), comment='学生类别')
    enrollment_date = Column(String(20), comment='入学日期')
    graduation_date = Column(String(20), comment='毕业日期')
    is_enrolled = Column(String(10), comment='是否在籍')
    is_on_campus = Column(String(10), comment='是否在校')
    campus = Column(String(50), comment='校区')
    student_status = Column(String(20), comment='学籍状态')
    political_status = Column(String(20), comment='政治面貌')
    ethnic_group = Column(String(20), comment='民族')
    health_status = Column(String(20), comment='健康状况')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

# 学生登录凭据表
class StudentCredentials(Base):
    __tablename__ = 'student_credentials'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(20), unique=True, nullable=False, comment='学号')
    student_name = Column(String(50), nullable=False, comment='姓名')
    password = Column(String(255), nullable=False, comment='密码')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

# 课程表
class Course(Base):
    __tablename__ = 'courses'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(20), nullable=False, comment='学号')
    course_name = Column(String(100), nullable=False, comment='课程名称')
    teacher = Column(String(50), comment='任课教师')
    classroom = Column(String(50), comment='教室')
    day_of_week = Column(String(10), comment='星期')
    periods = Column(Text, comment='节次（JSON格式）')
    weeks = Column(Text, comment='周次（JSON格式）')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

# 考试安排表
class Exam(Base):
    __tablename__ = 'exams'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(20), nullable=False, comment='学号')
    course_name = Column(String(100), comment='课程名称')
    exam_date = Column(String(20), comment='考试日期')
    exam_time = Column(String(20), comment='考试时间')
    classroom = Column(String(50), comment='考场')
    seat_number = Column(String(10), comment='座位号')
    exam_type = Column(String(20), comment='考试类型')
    teacher = Column(String(50), comment='监考教师')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

# 成绩表
class Grade(Base):
    __tablename__ = 'grades'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(20), nullable=False, comment='学号')
    course_name = Column(String(100), comment='课程名称')
    course_code = Column(String(20), comment='课程代码')
    credits = Column(Float, comment='学分')
    grade = Column(String(10), comment='成绩')
    grade_point = Column(Float, comment='绩点')
    semester = Column(String(20), comment='学期')
    exam_type = Column(String(20), comment='考试类型')
    course_type = Column(String(20), comment='课程类型')
    teacher = Column(String(50), comment='任课教师')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

# 用户会话表
class UserSession(Base):
    __tablename__ = 'user_sessions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), unique=True, nullable=False, comment='会话ID')
    student_id = Column(String(20), nullable=False, comment='学号')
    student_name = Column(String(50), comment='姓名')
    login_time = Column(DateTime, default=datetime.now, comment='登录时间')
    last_activity = Column(DateTime, default=datetime.now, comment='最后活动时间')
    is_active = Column(Boolean, default=True, comment='是否活跃')

# 数据库初始化函数
def init_database():
    """初始化数据库"""
    try:
        print(f"🔄 正在连接到 MySQL 服务器 {DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}...")
          # 先创建数据库（如果不存在）
        temp_url = f"mysql+pymysql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}"
        temp_engine = create_engine(temp_url)
        
        print(f"🔄 正在创建数据库 '{DATABASE_CONFIG['database']}'（如果不存在）...")
        with temp_engine.connect() as conn:
            # 使用 text() 来执行原生SQL
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {DATABASE_CONFIG['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            conn.commit()
        
        print(f"✅ 数据库 '{DATABASE_CONFIG['database']}' 已创建/确认存在")
        
        # 创建表
        print("🔄 正在创建数据表...")
        engine = create_engine(get_database_url())
        Base.metadata.create_all(engine)
        print("✅ 数据库表创建完成!")
        print("✅ 数据库初始化成功!")
        return True
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        print(f"错误详情: {type(e).__name__}: {str(e)}")
        return False

# 获取数据库会话
def get_db_session():
    """获取数据库会话"""
    engine = create_engine(get_database_url())
    Session = sessionmaker(bind=engine)
    return Session()

# 测试数据库连接
def test_connection():
    """测试数据库连接"""
    try:
        engine = create_engine(get_database_url())
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ 数据库连接测试成功!")
            return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

if __name__ == "__main__":
    print("正在初始化数据库...")
    if init_database():
        print("正在测试数据库连接...")
        if test_connection():
            print("🎉 数据库系统已就绪！")
        else:
            print("⚠️ 数据库已创建但连接测试失败")
    else:
        print("❌ 数据库初始化失败，请检查配置!")
