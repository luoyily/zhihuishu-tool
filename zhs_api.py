import requests
import re
import datetime
# windows 下请安装 pycryptodome 库
from Crypto.Cipher import AES
import base64
import time
import json

session = requests.session()
session.headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
}

# Constant:
# 学生首页AES Key
HOME_PAGE_AES_KEY = '7q9oko0vqb3la20r'
# 通用IV，MODE
ZHS_AES_IV = '1g3qqdh4jvbskb9x'
ZHS_AES_MODE = AES.MODE_CBC
# 共享学分课视频页AES Key
STUDY_VIDEO_AES_KEY = 'qz632524n86i7fk9'
# 共享学分课问答页AES Key
QA_AES_KEY = 'w1k5ntxecb8wmbc2'


class AESEncrypt:
    # 这里的AES字符串加密参考了 https://zhuanlan.zhihu.com/p/184968023
    def __init__(self, key, iv, mode):
        self.key = key.encode('utf-8')
        self.iv = iv.encode('utf-8')
        self.mode = mode

    def pkcs7padding(self, text):
        """明文使用PKCS7填充 """
        bs = 16
        length = len(text)
        bytes_length = len(text.encode('utf-8'))
        padding_size = length if (bytes_length == length) else bytes_length
        padding = bs - padding_size % bs
        padding_text = chr(padding) * padding
        self.coding = chr(padding)
        return text + padding_text

    def aes_encrypt(self, content):
        """ AES加密 """
        cipher = AES.new(self.key, self.mode, self.iv)
        # 处理明文
        content_padding = self.pkcs7padding(content)
        # 加密
        encrypt_bytes = cipher.encrypt(content_padding.encode('utf-8'))
        # 重新编码
        result = str(base64.b64encode(encrypt_bytes), encoding='utf-8')
        return result

    def aes_decrypt(self, content):
        """AES解密 """
        cipher = AES.new(self.key, self.mode, self.iv)
        content = base64.b64decode(content)
        text = cipher.decrypt(content).decode('utf-8')
        return text.rstrip(self.coding)


class ZHSEncrypt:
    """
    智慧树自写加密算法集
    """

    def gen_watch_point(self, start_time, end_time=300):
        """
        生成watchPoint（提交共享学分课视频进度接口用）
        :param start_time: 起始视频进度条时间，秒
        :param end_time: 提交时距离起始时间的间隔，秒。默认为正常观看时请求database接口的间隔时间
        """
        record_interval = 1990
        total_study_time_interval = 4990
        cache_interval = 180000
        database_interval = 300000
        watch_point = None
        total_stydy_time = start_time
        for i in range(int(end_time * 1000)):
            if i % total_study_time_interval == 0:
                total_stydy_time += 5
            if i % record_interval == 0 and i >= record_interval:
                t = int(total_stydy_time / 5) + 2
                if watch_point is None:
                    watch_point = '0,1,'
                else:
                    watch_point += ','
                watch_point += str(t)
        return watch_point

    def get_ev(self, t: list, key='zzpttjd'):
        """
        D26666 key:zzpttjd
        D24444 key:zhihuishu
        生成参数ev（提交共享学分课视频进度接口用）
        见面课页面加密参数D24444也使用此加密
        :param t:
        请注意，此列表不同接口顺序不同
        以下为Database进度提交接口的顺序
        [
           recruitId,
           lessonId,
           smallLessonId, （对应"videoSmallLessons": 下的ID， 没有为0）
           lastViewVideoId,
           videoDetail.chapterId,
           data.studyStatus, （str e.g:  "0"）
           parseInt(this.playTimes),(提交到进度的时间，比如从5秒观看到25秒，那么这里提交了20秒)
           parseInt(this.totalStudyTime),
           i.i(p.g) (ablePlayerX('container').getPosition())   （str e.g:  "00:04:43"）
         ],
         以下为见面课提交的参数列表：
         [recruitId, liveCourseId, userId, relativeTime, watchType, curVideoId]
        """
        # _d = 'zzpttjd'
        _d = key

        # Y/
        def y(_t):
            e_2 = str(hex(_t))[2:]
            if len(e_2) < 2:
                return '0' + e_2
            else:
                return e_2

        # Z
        e = ''
        for j in t:
            e += str(j) + ';'
        e = e[0:len(e) - 1]
        # X
        e_1 = ''
        for i in range(len(e)):
            n = ord(e[i]) ^ ord(_d[i % len(_d)])
            e_1 += y(n)
        return e_1


class Account:
    def __init__(self):
        self.uuid = None

    def validata_account_and_password(self, account, password):
        """
        验证账号密码
        :return: 加密pwd字符串，uuid
        """
        url = 'https://passport.zhihuishu.com/user/validateAccountAndPassword'
        data = {'account': account, 'password': password}
        r = session.post(url, data=data)
        pwd = r.json()['pwd']
        uuid = r.json()['uuid']
        return pwd, uuid

    def check_need_auth(self, uuid):
        """检查是否需要验证"""
        url = 'https://appcomm-user.zhihuishu.com/app-commserv-user/userInfo/checkNeedAuth'
        data = {'uuid', uuid}
        r = session.post(url, data=data)
        return r.json()

    def get_lt(self):
        """获取登录用参数 ’lt‘ """
        url = 'https://passport.zhihuishu.com/login?service=https://onlineservice.zhihuishu.com/login/gologin'
        r = session.get(url)
        lt = str(re.search('LT(.*?).com', r.text).group())
        return lt

    def login(self, username, password):
        """登录"""
        # 获取uuid
        pwd, uuid = self.validata_account_and_password(username, password)
        self.uuid = uuid
        url = 'https://passport.zhihuishu.com/login'
        data = {
            "lt": self.get_lt(),
            "execution": "e1s1",
            "_eventId": "submit",
            "username": username,
            "password": password,
            "clCode": "",
            "clPassword": "",
            "tlCode": "",
            "tlPassword": "",
            "remember": "on"
        }
        session.post(url, data)

    def go_login(self, go_link):
        """
        在基于主页登录的情况下，登录共享学分课视频页面
        """
        url = f'https://studyservice-api.zhihuishu.com/login/gologin?fromurl={go_link}'
        r = session.get(url)

    def get_utc_iso_time(self):
        """
        获取UTC时区的ISO时间格式
        :return: ISO时间字符串
        """
        now = datetime.datetime.now()
        utc_time = now - datetime.timedelta(hours=8)
        iso_time = utc_time.strftime("%Y-%m-%dT%H:%M:%S.{0}Z").format(int(round(utc_time.microsecond / 1000.0)))
        return iso_time


class Course(Account):
    def __init__(self):
        Account.__init__(self)

    """
    课程信息页部分（学生主页）
    """

    def query_share_course_info(self, status=0, page_no=1, page_size=5):
        """
        获取共享学分课信息
        :param status: 学习状态，0：进行中，1：已完成
        :param page_no: 第几页
        :param page_size: 每页数据条数（默认5）
        """
        url = 'https://onlineservice-api.zhihuishu.com/gateway/t/v1/student/course/share/queryShareCourseInfo'
        aes = AESEncrypt(key=HOME_PAGE_AES_KEY, iv=ZHS_AES_IV, mode=ZHS_AES_MODE)
        raw_data = f'{{"status":{status},"pageNo":{page_no},"pageSize":{page_size}}}'
        secret_str = aes.aes_encrypt(raw_data)
        data = {"secretStr": secret_str}
        r = session.post(url, data=data)
        return r.json()

    def get_my_course_list(self):
        """获取校内学分课信息"""
        url = 'https://hikeservice.zhihuishu.com/student/course/aided/getMyCourseList'
        params = {'uuid': self.uuid, 'date': self.get_utc_iso_time()}
        r = session.get(url, params=params)
        return r.json()

    """
    成绩分析页部分
    """

    def load_study_sertify(self, course_id, recruit_id):
        """获取学习证书（成绩信息）"""
        url = 'https://stuonline.zhihuishu.com/stuonline/json/stuLearnReportNew/loadStudyCertify'
        data = {
            "courseId": course_id,
            "recruitId": recruit_id
        }
        r = session.post(url, data=data)
        return r.json()

    def load_stu_learing_tab(self, course_id, recruit_id):
        """获取详细学习信息（学习进度分，每小节学习情况）"""
        url = 'https://stuonline.zhihuishu.com/stuonline/json/stuLearnReportNew/loadStuLearingTab/'
        data = {
            "courseId": course_id,
            "recruitId": recruit_id,
            "type": "l"
        }
        r = session.post(url, data=data)
        return r.json()

    def load_stu_habit(self, course_id, recruit_id):
        """获取学习习惯信息（习惯分，最近学习时长信息表）"""
        url = 'https://stuonline.zhihuishu.com/stuonline/json/stuLearnReportNew/loadStuHabit/'
        data = {
            "courseId": course_id,
            "recruitId": recruit_id,
            "type": "l"
        }
        r = session.post(url, data=data)
        return r.json()

    def load_course_forum(self, course_id, recruit_id):
        """获取课程互动信息"""
        url = 'https://stuonline.zhihuishu.com/stuonline/json/stuLearnReportNew/loadCourseForum/'
        data = {
            "courseId": course_id,
            "recruitId": recruit_id,
            "type": "l"
        }
        r = session.post(url, data=data)
        return r.json()

    def load_exam_and_score(self, recruit_id, chapter_ids, lesson_ids="", lesson_type=""):
        """
        获取平时测试信息
        :param chapter_ids:章节ID，由每个章节ID按逗号隔开的字符串。例如："123,1234"
        """
        url = 'https://stuonline.zhihuishu.com/stuonline/json/stuLearnReportNew/loadExamAndScore/'
        data = {
            "recruitId": recruit_id,
            "chapterIds": chapter_ids,
            "lessonIds": lesson_ids,
            "lessonType": lesson_type
        }
        r = session.post(url, data=data)
        return r.json()

    """
    共享学分课 课程问答页部分
    """

    def get_question_list(self, course_id, recruit_id, page_index=0, page_size=50, mode='hot'):
        """
        获取问题列表(热门，最新，镜华, 话题讨论)
        :param mode:hot: 热门，recommend: 最新, essence：镜华, topic:话题讨论
        """
        url = 'https://creditqa-api.zhihuishu.com/creditqa/gateway/t/v1/web/qa/getHotQuestionList'
        if mode == 'recommend':
            url = 'https://creditqa-api.zhihuishu.com/creditqa/gateway/t/v1/web/qa/getRecommendList'
        elif mode == 'essence':
            url = 'https://creditqa-api.zhihuishu.com/creditqa/gateway/t/v1/web/qa/getEssenceList'
        elif mode == 'topic':
            url = 'https://creditqa-api.zhihuishu.com/creditqa/gateway/t/v1/web/qa/getTopicList'
        aes = AESEncrypt(key=QA_AES_KEY, iv=ZHS_AES_IV, mode=ZHS_AES_MODE)
        raw_data = f'{{"courseId":"{course_id}","pageIndex":{page_index},' \
                   f'"pageSize":{page_size},"recruitId":"{recruit_id}"}}'
        if mode == 'topic':
            raw_data = f'{{"courseId":"{course_id}","pageIndex":{page_index},' \
                       f'"pageSize":{page_size},"recruitId":"{recruit_id}","chapterId":0}}'
        secret_str = aes.aes_encrypt(raw_data)
        data = {
            "dateFormate": int(round(time.time()) * 1000),
            "secretStr": secret_str
        }
        r = session.post(url, data=data)
        return r.json()

    def get_answer_in_info_order_by_time(self, question_id, course_id, recruit_id, page_index=0, page_size=20):
        """获取问题回答信息"""
        url = 'https://creditqa-api.zhihuishu.com/creditqa/gateway/t/v1/web/qa/getAnswerInInfoOrderByTime'
        aes = AESEncrypt(key=QA_AES_KEY, iv=ZHS_AES_IV, mode=ZHS_AES_MODE)
        raw_data = f'{{"questionId":"{question_id}","sourceType":"2","courseId":"{course_id}",' \
                   f'"recruitId":"{recruit_id}","pageIndex":{page_index},"pageSize":{page_size}}}'
        secret_str = aes.aes_encrypt(raw_data)
        data = {
            "dateFormate": int(round(time.time()) * 1000),
            "secretStr": secret_str
        }
        r = session.post(url, data=data)
        return r.json()

    def save_answer(self, qid, courseId, recruitId, answer_text):
        """
        提交问题回答
        """
        url = 'https://creditqa-api.zhihuishu.com/creditqa/gateway/t/v1/web/qa/saveAnswer'
        aes = AESEncrypt(key=QA_AES_KEY, iv=ZHS_AES_IV, mode=ZHS_AES_MODE)
        raw_data = f'{{"annexs":"[]","qid":"{qid}","source":"2","aContent":"{answer_text}","courseId":"{courseId}",' \
                   f'"recruitId":"{recruitId}"}}'
        secret_str = aes.aes_encrypt(raw_data)
        data = {
            "dateFormate": int(round(time.time()) * 1000),
            "secretStr": secret_str
        }
        r = session.post(url, data=data)
        return r.json()

    def delet_answer(self, answerId):
        """
        删除自己的某个回答
        """
        url = 'https://creditqa-api.zhihuishu.com/creditqa/gateway/t/v1/web/qa/deleteAnswerByAnswerId'
        aes = AESEncrypt(key=QA_AES_KEY, iv=ZHS_AES_IV, mode=ZHS_AES_MODE)
        raw_data = f'{{"answerId":{answerId},"deleteType":3}}'
        secret_str = aes.aes_encrypt(raw_data)
        data = {
            "dateFormate": int(round(time.time()) * 1000),
            "secretStr": secret_str
        }
        r = session.post(url, data=data)
        return r.json()

    def set_answer_like(self, answer_id, is_like=0):
        """
        点赞/取消赞
        :param answer_id: 回答ID
        :param is_like: 是否点赞，0：未点赞，请求后点赞回答。1：已点赞，请求后取消赞
        """
        url = 'https://creditqa-api.zhihuishu.com/creditqa/gateway/t/v1/web/qa/updateOperationToLike'
        aes = AESEncrypt(key=QA_AES_KEY, iv=ZHS_AES_IV, mode=ZHS_AES_MODE)
        raw_data = f'{{"islike":"{is_like}","answerId":{answer_id}}}'
        secret_str = aes.aes_encrypt(raw_data)
        data = {
            "dateFormate": int(round(time.time()) * 1000),
            "secretStr": secret_str
        }
        r = session.post(url, data=data)
        return r.json()

    def get_my_qa_join_info(self, course_id, recruit_id, page_index=0, page_size=50, mode='answer'):
        """
        获取个人参加的课程问答信息（我的回答，我的提问，我的围观）
        :param mode: answer:我的回答, question我的提问，watching我的围观
        """
        url = 'https://creditqa-api.zhihuishu.com/creditqa/gateway/t/v1/web/qa/myAnswerList'
        if mode == 'question':
            url = 'https://creditqa-api.zhihuishu.com/creditqa/gateway/t/v1/web/qa/myQuestionList'
        elif mode == 'watching':
            url = 'https://creditqa-api.zhihuishu.com/creditqa/gateway/t/v1/web/qa/getMyOnlookerList'
        aes = AESEncrypt(key=QA_AES_KEY, iv=ZHS_AES_IV, mode=ZHS_AES_MODE)
        raw_data = f'{{"courseId":"{course_id}","pageIndex":{page_index},"pageSize":{page_size},' \
                   f'"recruitId":"{recruit_id}"}}'
        secret_str = aes.aes_encrypt(raw_data)
        data = {
            "dateFormate": int(round(time.time()) * 1000),
            "secretStr": secret_str
        }
        r = session.post(url, data=data)
        return r.json()

    """
    共享学分课视频页相关
    """

    def query_course(self, recruit_and_course_id):
        """
        查询课程信息（此请求包含class id,  school id, recruit id, course info...）
        """
        url = 'https://studyservice-api.zhihuishu.com/gateway/t/v1/learning/queryCourse'
        aes = AESEncrypt(key=STUDY_VIDEO_AES_KEY, iv=ZHS_AES_IV, mode=ZHS_AES_MODE)
        raw_data = f'{{"recruitAndCourseId":"{recruit_and_course_id}","dateFormate":{int(round(time.time()) * 1000)}}}'
        secret_str = aes.aes_encrypt(raw_data)
        data = {
            "secretStr": secret_str
        }
        r = session.post(url, data=data)
        return r.json()

    def get_video_list(self, recruit_and_course_id):
        """
        获取课程视频列表
        """
        url = 'https://studyservice-api.zhihuishu.com/gateway/t/v1/learning/videolist'
        aes = AESEncrypt(key=STUDY_VIDEO_AES_KEY, iv=ZHS_AES_IV, mode=ZHS_AES_MODE)
        raw_data = f'{{"recruitAndCourseId":"{recruit_and_course_id}","dateFormate":{int(round(time.time()) * 1000)}}}'
        secret_str = aes.aes_encrypt(raw_data)
        data = {
            "secretStr": secret_str
        }
        r = session.post(url, data=data)
        return r.json()

    # 摆烂了，不管代码规范了 = =
    def query_study_info(self, lessonIds, lessonVideoIds, recruitId):
        """
        查询学习信息(此请求包含 studyTotalTime， watchState)
        :param lessonIds: list[int] [123,124]
        :param lessonVideoIds: list[int] [123,124]
        """
        url = 'https://studyservice-api.zhihuishu.com/gateway/t/v1/learning/queryStuyInfo'
        aes = AESEncrypt(key=STUDY_VIDEO_AES_KEY, iv=ZHS_AES_IV, mode=ZHS_AES_MODE)
        lessonIds = f'[{",".join([str(i) for i in lessonIds])}]'
        lessonVideoIds = f'[{",".join([str(i) for i in lessonVideoIds])}]'
        raw_data = f'{{"lessonIds":{lessonIds},"lessonVideoIds":{lessonVideoIds},"recruitId":{recruitId},' \
                   f'"dateFormate":{int(round(time.time()) * 1000)}}}'
        secret_str = aes.aes_encrypt(raw_data)
        data = {"secretStr": secret_str}
        r = session.post(url, data=data)
        return r.json()

    def query_user_recruit_id_last_video_id(self, recruitId):
        """
        查询上一次观看的视频ID
        """
        url = 'https://studyservice-api.zhihuishu.com/gateway/t/v1/learning/queryUserRecruitIdLastVideoId'
        aes = AESEncrypt(key=STUDY_VIDEO_AES_KEY, iv=ZHS_AES_IV, mode=ZHS_AES_MODE)
        raw_data = f'{{"recruitId":{recruitId},"dateFormate":{int(round(time.time()) * 1000)}}}'
        secret_str = aes.aes_encrypt(raw_data)
        data = {"secretStr": secret_str}
        r = session.post(url, data=data)
        return r.json()

    def pre_learning_note(self, ccCourseId, chapterId, lessonId, recruitId, videoId, small_lesson_id):
        """
        查询具体视频课程的学习信息？（包含learningTokenId需要Base64编码的ID, 已学时间等关于该视频的状态）
        :param ccCourseId: CourseId
        :param chapterId: videoChapterDtos.id
        :param lessonId: videoLessons.id
        """
        url = 'https://studyservice-api.zhihuishu.com/gateway/t/v1/learning/prelearningNote'
        aes = AESEncrypt(key=STUDY_VIDEO_AES_KEY, iv=ZHS_AES_IV, mode=ZHS_AES_MODE)
        raw_data = f'{{"ccCourseId":{ccCourseId},"chapterId":{chapterId},"isApply":1,"lessonId":{lessonId},' \
                   f'"recruitId":{recruitId},"videoId":{videoId},"dateFormate":{int(round(time.time()) * 1000)}}}'
        if small_lesson_id:
            raw_data = f'{{"ccCourseId":{ccCourseId},"chapterId":{chapterId},"isApply":1,"lessonId":{lessonId},"lessonVideoId":{small_lesson_id},' \
                       f'"recruitId":{recruitId},"videoId":{videoId},"dateFormate":{int(round(time.time()) * 1000)}}}'
        secret_str = aes.aes_encrypt(raw_data)
        data = {"secretStr": secret_str}
        r = session.post(url, data=data)
        return r.json()

    def load_video_pointer_info(self, lessonId, recruitId, courseId, small_lesson_id=None):
        """
        获取视频额外内容检查点
        """
        url = 'https://studyservice-api.zhihuishu.com/gateway/t/v1/popupAnswer/loadVideoPointerInfo'
        aes = AESEncrypt(key=STUDY_VIDEO_AES_KEY, iv=ZHS_AES_IV, mode=ZHS_AES_MODE)
        raw_data = f'{{"lessonId":{lessonId},"recruitId":{recruitId},"courseId":{courseId},' \
                   f'"dateFormate":{int(round(time.time()) * 1000)}}}'
        if small_lesson_id:
            raw_data = f'{{"lessonId":{lessonId},"lessonVideoId":{small_lesson_id},"recruitId":{recruitId},' \
                       f'"courseId":{courseId},"dateFormate":{int(round(time.time()) * 1000)}}}'
        secret_str = aes.aes_encrypt(raw_data)
        data = {"secretStr": secret_str}
        r = session.post(url, data=data)
        return r.json()

    def get_popup_exam(self, lessonId, questionIds, small_lesson_id=None):
        """
        获取弹题数据
        """
        url = 'https://studyservice-api.zhihuishu.com/gateway/t/v1/popupAnswer/lessonPopupExam'
        aes = AESEncrypt(key=STUDY_VIDEO_AES_KEY, iv=ZHS_AES_IV, mode=ZHS_AES_MODE)
        raw_data = f'{{"lessonId":{lessonId},"questionIds":"{questionIds}",' \
                   f'"dateFormate":{int(round(time.time()) * 1000)}}}'
        if small_lesson_id:
            raw_data = f'{{"lessonId":{lessonId},"lessonVideoId":{small_lesson_id},"questionIds":"{questionIds}",' \
                       f'"dateFormate":{int(round(time.time()) * 1000)}}}'
        secret_str = aes.aes_encrypt(raw_data)
        data = {"secretStr": secret_str}
        r = session.post(url, data=data)
        return r.json()

    def submit_popup_exam(self, courseId, recruitId, testQuestionId, lessonId, answer, isCurrent, small_lesson_id=None):
        """
        提交弹题回答
        :param answer: String like "123", "123,124"（分别为单选，多选）
        :param isCurrent: 是否正确 0错， 1对
        """
        url = 'https://studyservice-api.zhihuishu.com/gateway/t/v1/popupAnswer/saveLessonPopupExamSaveAnswer'
        aes = AESEncrypt(key=STUDY_VIDEO_AES_KEY, iv=ZHS_AES_IV, mode=ZHS_AES_MODE)
        raw_data = f'{{"courseId":{courseId},"recruitId":{recruitId},"testQuestionId":{testQuestionId},' \
                   f'"isCurrent":"{isCurrent}","lessonId":{lessonId},"answer":"{answer}","testType":0,' \
                   f'"dateFormate":{int(round(time.time()) * 1000)}}}'
        if small_lesson_id:
            raw_data = f'{{"courseId":{courseId},"recruitId":{recruitId},"testQuestionId":{testQuestionId},' \
                       f'"isCurrent":"{isCurrent}","lessonId":{lessonId},"lessonVideoId":{small_lesson_id},' \
                       f'"answer":"{answer}","testType":0,"dateFormate":{int(round(time.time()) * 1000)}}}'
        secret_str = aes.aes_encrypt(raw_data)
        data = {"secretStr": secret_str}
        r = session.post(url, data=data)
        return r.json()

    def save_database_interval_time(self, watchPoint, ev, learningTokenId, courseId):
        """
        提交视频学习进度
        """
        url = 'https://studyservice-api.zhihuishu.com/gateway/t/v1/learning/saveDatabaseIntervalTime'
        aes = AESEncrypt(key=STUDY_VIDEO_AES_KEY, iv=ZHS_AES_IV, mode=ZHS_AES_MODE)
        ltid = base64.encodebytes(str(learningTokenId).encode()).decode('utf-8').rstrip()
        raw_data = f'{{"watchPoint":"{watchPoint}","ev":"{ev}","learningTokenId":"{ltid}","courseId":{courseId},' \
                   f'"dateFormate":{int(round(time.time()) * 1000)}}}'
        secret_str = aes.aes_encrypt(raw_data)
        data = {"secretStr": secret_str}
        r = session.post(url, data=data)
        return r.json()

    """
    见面课相关
    """

    def get_meet_course_list(self, recruit_id):
        """
        获取见面课信息
        """
        url = 'https://stuonline.zhihuishu.com/stuonline/json/teachMeeting/listTeachMeetingStu?examV2=ss'
        data = {
            "recruitId": f"{recruit_id}",
            "page.pageNo": "0",
            "page.pageSize": "10"
        }
        r = session.post(url, data=data)
        return r.json()

    def get_videos_by_live_id(self, live_id):
        """
        获取见面课视频信息
        """
        url = f'https://im.zhihuishu.com/livehome/getVideosByLiveId?liveId={live_id}'
        r = session.get(url)
        return json.loads(r.text)

    def get_mc_watch_history(self, live_id, user_id):
        """
        获取观看记录
        """
        url = 'http://im.zhihuishu.com//live/getWatchHistory'
        params = {
            "s": f"{round(time.time() * 1000)}",
            "jsonpCallBack": "getWatchHistoryCallBack",
            "courseId": f"{live_id}",
            "userId": f"{user_id}",
            "_": f"{round(time.time() * 1000)}"
        }
        r = session.get(url, params=params)
        return json.loads(r.text.replace('getWatchHistoryCallBack(', '')[:-1])

    def submit_meet_course_progress(self, param_secret):
        """
        提交见面课进度
        """
        url = 'https://im.zhihuishu.com//live/setWatchHistorySecret'
        params = {
            "callback": "jsonpCallBack",
            "paramSecret": f"{param_secret}",
            "jsonpCallBack": "jsonpCallBack",
            "_": f"{round(time.time() * 1000)}"
        }
        r = session.get(url, params=params)
        return r.text
