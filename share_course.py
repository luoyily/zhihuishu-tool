import zhs_api
import time

"""
视频学习进度提交流程：
    1. 登录
    2. 获取课程信息
    3. 提交进度（前置：watch point, ev , learning token , course id）
    4. wp: 需要获取之前的视频观看进度，视频总时长。弹题点时间。
    5. ev：需要获取视频信息
    6. learning token： 请求prel后对结果中id b64
        start   300      300      300      300      300
        -------------0-------------------0--------------
        ^        ^   ^                                 ^
        |        |   |                              到达结尾，提交正常请求
        |        |   弹题打断，提交正常请求，完成弹题后继续
        |       达到计时，提交正常请求
        |提交只有ev, lid, date的请求（也可以不管）
"""

course = zhs_api.Course()
print("登录：（未做账号密码正确性验证，请确定后再输入！）")
username = input("请输入账号：")
password = input("请输入密码：")
course.login(username, password)
is_immediately_submit = True


class ShareCourse:
    def __init__(self, course_id, name, progress, recruit_id, secret):
        self.course_id = course_id
        self.name = name
        self.progress = progress
        self.recruit_id = recruit_id
        self.secret = secret


class VideoLesson:
    def __init__(self, chapter_id, lesson_id, lesson_name, video_id, video_sec, small_lesson_id=None):
        self.chapter_id = chapter_id
        self.lesson_id = lesson_id
        self.lesson_name = lesson_name
        self.video_id = video_id
        self.video_sec = video_sec
        self.small_lesson_id = small_lesson_id


def pass_pop_exam(video_pointer, lesson_id, course_id, recruit_id, small_lesson_id=None):
    print(f'触发弹题，已自动提交')
    qids = []
    ans = []
    for q in video_pointer['data']['questionPoint']:
        qids.append(q['questionIds'])
    for q in qids:
        pop_exam = course.get_popup_exam(lessonId=lesson_id, questionIds=q, small_lesson_id=small_lesson_id)
        options = pop_exam['data']["lessonTestQuestionUseInterfaceDtos"][0]["testQuestion"]["questionOptions"]
        ans_str = ','
        current_opt = []
        for option in options:
            if option["result"] == "1":
                current_opt.append(str(option['id']))
        ans.append(ans_str.join(current_opt))

    for a, q in zip(ans, qids):
        sub = course.submit_popup_exam(courseId=course_id, recruitId=recruit_id, testQuestionId=q, isCurrent='1',
                                       lessonId=lesson_id, small_lesson_id=small_lesson_id, answer=a)
        return sub


def submit_study_record(video_lesson, init_learn_time, dt, recruit_id, study_total_time, learning_token_id, course_id):
    print(f'当前视频：{video_lesson.lesson_name}, 视频总时长：{video_lesson.video_sec}, '
          f'\n上此观看到：{init_learn_time}, 本次需要观看：{dt}')
    watch_point = zhs_encrypt.gen_watch_point(init_learn_time, dt)
    small_lesson_id = 0
    if video_lesson.small_lesson_id:
        small_lesson_id = video_lesson.small_lesson_id
    last_view_id = course.query_user_recruit_id_last_video_id(recruit_id)['data']["lastViewVideoId"]
    # 提交时的学习时间相关（之前视频观看到的时间点加上dt）
    play_time = dt - (dt % 5)
    video_pos = time.strftime("%H:%M:%S", time.gmtime(init_learn_time + dt))
    # 生成ev
    evt = [recruit_id, video_lesson.lesson_id, small_lesson_id, last_view_id, video_lesson.chapter_id, "0",
           play_time, study_total_time, video_pos]
    ev = zhs_encrypt.get_ev(evt)
    resp = course.save_database_interval_time(watch_point, ev, learningTokenId=learning_token_id, courseId=course_id)
    print(resp)
    if not is_immediately_submit:
        time.sleep(dt)
    else:
        time.sleep(10)
    return resp


share_course_list = []

# 获取全部共享课信息
share_course_count = course.query_share_course_info(page_no=1)["result"]["totalCount"]
for page_no in range(1, int((share_course_count-1)/5)+2):
    # 请求每一页，并添加课程信息到列表中
    share_course_info = course.query_share_course_info(page_no=page_no)
    for sci in share_course_info["result"]["courseOpenDtos"]:
        cid = sci["courseId"]
        name = sci["courseName"]
        progress = sci["progress"]
        rid = sci["recruitId"]
        secret = sci["secret"]
        item = ShareCourse(cid, name, progress, rid, secret)
        share_course_list.append(item)
# 打印全部课程名字
print("正在进行的课程：")
for course_ in share_course_list:
    print(course_.name, "\n")
if int(input("接下来将会学习每个课程25分钟，是否确定？ 1：确定 0：退出")) == 1:
    pass
else:
    exit(0)

is_immediately_submit = bool(int(input("选择进度提交模式：0：按正常时间提交（正常挂完25分钟） 1：立即提交（立即刷完）")))
course.go_login(f'https://studyh5.zhihuishu.com/videoStudy.html#/'
                f'studyVideo?recruitAndCourseId={share_course_list[0].secret}')

for c_index in range(0, len(share_course_list)):
    # 每到一个课程，VideoLessonList清空一次
    video_lesson_list = []
    # 获取视频信息
    recruit_and_course_id = share_course_list[c_index].secret
    video_list = course.get_video_list(recruit_and_course_id)
    for video_chapter in video_list["data"]["videoChapterDtos"]:
        for video in video_chapter["videoLessons"]:
            chapter_id = video["chapterId"]
            lesson_id = video["id"]
            lesson_name = video["name"]
            video_id = ''
            if "videoId" in video:
                video_id = video["videoId"]
                video_sec = video["videoSec"]
                item = VideoLesson(chapter_id, lesson_id, lesson_name, video_id, video_sec)
                video_lesson_list.append(item)
            elif "videoSmallLessons" in video:
                for s_video in video["videoSmallLessons"]:
                    small_lesson_id = s_video["id"]
                    video_id = s_video["videoId"]
                    video_sec = s_video["videoSec"]
                    item = VideoLesson(chapter_id, lesson_id, lesson_name, video_id, video_sec, small_lesson_id)
                    video_lesson_list.append(item)
    # 进度提交测试

    course_id = share_course_list[c_index].course_id
    recruit_id = share_course_list[c_index].recruit_id
    name_ = share_course_list[c_index].name
    zhs_encrypt = zhs_api.ZHSEncrypt()
    # 程序本地记录的学习时长，用于判断是否学满25分钟。
    local_study_time = 0
    # 计划学习时长: 分钟
    plan_time = 25
    # 遍历该课程的视频
    for vl in video_lesson_list:
        play_time = 0
        # 判断本地学习时长是否大于指定时间（25分钟）
        if local_study_time <= plan_time*60:
            # 查询该课程的观看情况，看完的视频则跳过
            learning_note = course.pre_learning_note(ccCourseId=course_id, chapterId=vl.chapter_id, lessonId=vl.lesson_id,
                                                     recruitId=recruit_id, videoId=vl.video_id, small_lesson_id=vl.small_lesson_id)
            # 获取learn token id
            learning_token_id = learning_note['data']["studiedLessonDto"]['id']
            learn_time = learning_note['data']["studiedLessonDto"]["learnTimeSec"]
            study_total_time = learning_note['data']["studiedLessonDto"]["studyTotalTime"]
            # 学习时长接近视频时长，跳过该视频
            if learn_time >= vl.video_sec - 5:
                continue
            # 计算需要提交的时间点
            # 先获取视频弹题点
            video_pointer = course.load_video_pointer_info(vl.lesson_id, recruit_id, course_id, vl.small_lesson_id)
            submit_times = []
            question_times = []
            # 如果有弹题再添加
            if "questionPoint" in video_pointer['data']:
                for q in video_pointer['data']['questionPoint']:
                    question_times.append(q['timeSec'])
            # 从视频观看过的时间开始，每次加300秒，大于弹题点，则将当前弹题点添加到提交时间点，小于则添加起始+300秒
            # 计算一共需要提交记录的次数，最少次数为视频总时长/300
            for i in range(int((vl.video_sec - 1)/300)+1+len(question_times)):
                # print(vl.lesson_name)
                print(f'本地学习时长：{local_study_time}')
                # 预计下次提交时间
                t_ = learn_time + 300
                qi = 0
                # 再次判断学习时长是否超过25分钟：
                if local_study_time <= plan_time*60:
                    # 如果视频有弹题，且没回答完
                    if question_times and qi <= len(question_times) and t_-300 < question_times[qi] <= t_:
                        # 弹题在预计提交时间前
                        # if t_-300 < question_times[qi] <= t_:
                        # 提交记录，完成弹题
                        dt = question_times[qi] - learn_time
                        pass_pop_exam(video_pointer, vl.lesson_id, course_id, recruit_id, vl.small_lesson_id)
                        submit_study_record(vl, learn_time, dt, recruit_id, study_total_time, learning_token_id, course_id)
                        learn_time += dt
                        study_total_time += dt
                        t_ += question_times[qi]
                        qi += 1
                        local_study_time += dt
                    # 视频剩下时间没有弹题
                    else:
                        # 到达视频末尾，视频剩余时间不足300秒
                        if t_ > vl.video_sec:
                            dt = vl.video_sec - (t_ - 300)
                            submit_study_record(vl, learn_time, dt, recruit_id, study_total_time, learning_token_id, course_id)
                            study_total_time += dt
                            learn_time += dt
                            local_study_time += dt
                            # 提交进度
                        else:
                            # 提交进度
                            dt = 300
                            submit_study_record(vl, learn_time, dt, recruit_id, study_total_time, learning_token_id, course_id)
                            study_total_time += dt
                            learn_time += dt
                            t_ += 300
                            local_study_time += dt

