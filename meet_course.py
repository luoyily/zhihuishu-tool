import zhs_api
import math
import io
from PIL import Image

def showImage(img):
    img = Image.open(io.BytesIO(img))
    img.show()

course = zhs_api.Course()
zhs_encrypt = zhs_api.ZHSEncrypt()
#print("登录：（未做账号密码正确性验证，请确定后再输入！）")
#username = input("请输入账号：")
#password = input("请输入密码：")
#course.login(username, password)
course.login(use_qr=True, qr_callback=showImage)


class MeetCourse:
    def __init__(self, rid, live_id, uid, video_ids, status, name):
        self.rid = rid
        self.live_id = live_id
        self.uid = uid
        self.video_ids = video_ids
        self.status = status
        self.name = name
        self.watch_history = None


sc_rids = []
meet_course_list = []
# 获取全部共享课信息
share_course_count = course.query_share_course_info(page_no=1)["result"]["totalCount"]
for page_no in range(1, int((share_course_count - 1) / 5) + 2):
    # 请求每一页，并添加课程信息到列表中
    share_course_info = course.query_share_course_info(page_no=page_no)
    for sci in share_course_info["result"]["courseOpenDtos"]:
        rid = sci["recruitId"]
        sc_rids.append(rid)

zhs_api.session.get(f'https://passport.zhihuishu.com/login?service=https://stuonline.zhihuishu.com/stuonline'
                    f'/teachMeeting/stuListV2?recruitId={sc_rids[0]}')
# 获取全部见面课信息
status_dic = {'1': '未开始',
              '2': '进行中',
              '3': '已结束',
              '4': '提前30分钟开始预播'}

for rid in sc_rids:
    meet_course = course.get_meet_course_list(rid)
    if meet_course['maps']:
        for m in meet_course['maps']:
            live_id = m['liveCourseId']
            uid = m['userId']
            video_ids = m['videoId'].split(',')
            status = m['taskStatus']
            name = m['taskName']
            item = MeetCourse(rid, live_id, uid, video_ids, status, name)
            meet_course_list.append(item)

# 查询待完成的见面课
print('直播已结束且未观看完成的见面课:')
for n, mc in enumerate(meet_course_list):
    # print(mc.name, mc.status)
    if mc.status:
        if int(mc.status) == 3:
            r = course.get_mc_watch_history(mc.live_id, mc.uid)
            mc.watch_history = str(r['history']).split(',')
            if r['history'] != '#':
                print(f'Num:{n}, Name:{mc.name}')


def finish_meet_course(meet_course:MeetCourse):
    videos = course.get_videos_by_live_id(meet_course.live_id)
    total_min = 1
    for video in videos:
        video_id = video['id']
        duration = video['duration']
        video_min = math.ceil(duration/60)
        total_min += video_min
        points = list(range(total_min-video_min, total_min))
        for x in meet_course.watch_history:
            if x:
                if int(x) in points:
                    points.remove(int(x))
        for relative_time in points:
            t = [
                meet_course.rid,
                meet_course.live_id,
                meet_course.uid,
                relative_time,
                "2",
                video_id
            ]
            secret = zhs_encrypt.get_ev(t, key='zhihuishu')
            print(course.submit_meet_course_progress(secret))


pre_fin_mc = int(input("请输入一个需要完成的见面课序号（-1：完成全部）"))
if pre_fin_mc == -1:
    for mc in meet_course_list:
        if mc.status:
            if mc.watch_history != ['#'] and int(mc.status) == 3:
                finish_meet_course(mc)
else:
    mc = meet_course_list[pre_fin_mc]
    if mc.status:
        if mc.watch_history != ['#'] and int(mc.status) == 3:
            finish_meet_course(mc)



