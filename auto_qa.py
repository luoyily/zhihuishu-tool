import zhs_api
import time
import io
from PIL import Image

def show_image(img):
    img = Image.open(io.BytesIO(img))
    img.show()

course = zhs_api.Course()
zhs_encrypt = zhs_api.ZHSEncrypt()
#print("登录：（未做账号密码正确性验证，请确定后再输入！）")
#username = input("请输入账号：")
#password = input("请输入密码：")
#course.login(username, password)
course.login(use_qr=True, qr_callback=show_image)


sc_list = []
# 获取全部共享课信息
print("正在查询你的共享学分课信息...")
share_course_count = course.query_share_course_info(page_no=1)["result"]["totalCount"]
for page_no in range(1, int((share_course_count - 1) / 5) + 2):
    # 请求每一页，并添加课程信息到列表中
    share_course_info = course.query_share_course_info(page_no=page_no)
    for n, sci in enumerate(share_course_info["result"]["courseOpenDtos"]):
        rid = sci["recruitId"]
        cid = sci["courseId"]
        name = sci["courseName"]
        sc_list.append((rid, cid))
        print(f'ID:{n+(page_no-1)*5} Name:{name}')

zhs_api.session.get(f'https://qah5.zhihuishu.com/qa.html#/web/home/{sc_list[0][1]}?role=2&recruitId={sc_list[0][0]}')
# 获取问题
# 设置回答数量(最大50)
ans_num = 30
# for rid, cid in sc_list:
sc_num = int(input("请输入你想自动回答的课程ID："))
rid, cid = sc_list[sc_num]
q_list = course.get_question_list(cid, rid)["rt"]["questionInfoList"]
if len(q_list) > ans_num:
    for q in q_list[:ans_num]:
        qid = q["questionId"]
        q_name = q["content"]
        print(f'当前问题：{q_name}')
        # 获取回答
        a_info = course.get_answer_in_info_order_by_time(qid, cid, rid)["rt"]
        if "answerInfos" in a_info:
            a_text = a_info["answerInfos"][0]["answerContent"]
            # 回答问题
            # is_answer = bool(int(input(f"将要回答：{a_text}，是否确定？（0，否 1，是）")))
            is_answer = True
            is_answered = bool(course.get_question_info(qid)["rt"]["questionInfo"]["isAnswer"])
            if is_answer and not(is_answered):
                a_rt = course.save_answer(qid, cid, rid, a_text)
                print(f'将要回答：{a_text}\n返回状态：{a_rt}')
                aid = a_rt["rt"]["answerId"]
                course.set_answer_like(aid)
                time.sleep(2)
