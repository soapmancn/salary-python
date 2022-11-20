import os
import mysql.connector
import ddddocr
import requests
from PIL import Image
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# 实例化浏览器
options = Options()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')
driver = webdriver.Chrome(executable_path='/usr/bin/chromedriver', options=options)
# 对指定的url发起请求
driver.get(os.environ['GZ_URL'])
sleep(1)
# 获取验证码并截图
driver.save_screenshot('screenshot.png')
element = driver.find_element(By.ID, 'Image1')
left = int(element.location['x'])
top = int(element.location['y'])
right = int(element.location['x'] + element.size['width'])
bottom = int(element.location['y'] + element.size['height'])
im = Image.open('screenshot.png')
im = im.crop((left, top, right, bottom))
im.save('screenshot.png')
# 识别验证码
ocr = ddddocr.DdddOcr()
with open('screenshot.png', 'rb') as f:
    img_bytes = f.read()
checkText = ocr.classification(img_bytes)
os.remove('screenshot.png')

# 登录
driver.find_element(By.ID, 'UserCode').send_keys(os.environ['USER_CODE'])
driver.find_element(By.ID, 'PassWord').send_keys(os.environ['PASS_WORD'])
driver.find_element(By.ID, 'txtCheckCode').send_keys(checkText)
driver.find_element(By.ID, 'ImageButton2').click()

# 解析
# 表头
th_list = []
thName = driver.find_elements(By.TAG_NAME, 'tr').__getitem__(6).find_elements(By.TAG_NAME, 'th')
for i in thName:
    th_list.append(i.text)
# 表内容
td_list = []
tdContent = driver.find_element(By.ID, 'GridView1_0').find_elements(By.TAG_NAME, 'td')
for i in tdContent:
    td_list.append(i.text)
driver.quit()

# 组装消息
message = ''
fgx = '-----------------------'
hhf = '\n'
year = ''
month = ''
for i, val in enumerate(th_list):
    if td_list[i] != '0.00' and val != '公司名称' and val != '人员':
        message += val + ':' + td_list[i] + hhf
    if val == '计发工资' or val == '企业社保小计' or val == '个人扣保险及住房合计' or val == '累计住房租金支出扣除':
        message += fgx + hhf
    if val == '工资年度':
        year = td_list[i]
    if val == '工资月份':
        month = td_list[i]

# 查询数据库入库
conn = mysql.connector.connect(host=os.environ['MYSQL_HOST'], user='root', passwd=os.environ['MYSQL_PASS'], db='mysql')
cursor = conn.cursor()
sql = 'select count(*) from my_salary where year = %s and month = %s'
val = (year, month)
cursor.execute(sql, val)
count = cursor.fetchone()[0]
if count < 1:
    # 发送通知
    token = os.environ['TEL_TOKEN']
    chat_id = os.environ['CHAT_ID']
    r = requests.post(f'https://api.telegram.org/bot{token}/sendMessage', json={"chat_id": chat_id, "text": message})
    # 入库
    insertSql = 'insert into my_salary(message, year, month) values(%s, %s, %s)'
    insertVal = (message, year, month)
    cursor.execute(insertSql, insertVal)
    conn.commit()
    conn.close()


