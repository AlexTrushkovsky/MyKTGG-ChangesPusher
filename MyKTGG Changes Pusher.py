from datetime import date
import requests
import urllib.parse
import datetime
import json
import time
import sched
import os

def remove_first_end_spaces(string):
    return "".join(string.rstrip().lstrip())

def getListOfUsers(isStudent):
    if isStudent:
        URL = "http://localhost/cgi-bin/timetable_export.cgi?req_type=obj_list&req_mode=group&req_format=json&coding_mode=WINDOWS-1251&bs=ok"
    else:
        URL = "http://localhost/cgi-bin/timetable_export.cgi?req_type=obj_list&req_mode=teacher&req_format=json&coding_mode=WINDOWS-1251&bs=ok"
    r = requests.get(url = URL)
    data = r.text
    data = data.replace("department", "")
    data = data.replace("]", "")
    data = data.replace("[", "")
    data = data.replace("\"", "")
    data = data.replace("}", "")
    data = data.replace("{:", "")
    array = data.split(",")
    newArr = []

    if isStudent:
        for item in array:
            if len(item) <= 10:
                newArr.append(remove_first_end_spaces(item))
    else:
        for item in array:
            if item.count(".") >= 2:
                newArr.append(remove_first_end_spaces(item))
    return newArr

def sendPushWith(title, body, num, topic, date):
    serverToken = 'Your firebase api key'
    deviceToken = topic

    if "Увага! Цей викладач на заміні!" in body and "Увага! Заняття перенесено у іншу аудиторію" in body:
        temp = body.replace("Увага! Заняття перенесено у іншу аудиторію", "")
        temp = temp.replace("Увага! Цей викладач на заміні! Замість викладача", "")
        temp = temp.replace("!", "")
        temp = temp.replace("<br>", "").strip()
        newBody = f'Ви замінюєте {temp} на {num} парі'
    elif "Увага! Заняття перенесено у іншу аудиторію" in body and "Увага! Заміна!" in body:
        temp = body.replace("Увага! Заняття перенесено у іншу аудиторію", "")
        temp = temp.replace("Увага! Заміна!", "")
        temp = temp.replace("!", "")
        temp = temp.split("замість:")[0]
        temp = temp.replace("<br>", "").strip()
        newBody = f'{num} пара перенесена в {temp}'
    elif "Увага! Цей викладач на заміні!" in body:
        temp = body.replace("Увага! Цей викладач на заміні! Замість викладача", "")
        temp = temp.replace("<br>", "").strip()
        newBody = f'Ви замінюєте {temp} на {num} парі'
    elif "Увага! Заміна!" in body:
        temp = body.replace("Увага! Заміна!", "")
        temp = temp.split("замість:")[0]
        temp = temp.replace("<br>", "").strip()
        newBody = f'{temp} {num} парою'
    elif "Увага! Заняття перенесено у іншу аудиторію" in body:
        temp = body.replace("Увага! Заняття перенесено у іншу аудиторію", "")
        temp = temp.replace("<br>", "")
        temp = temp.replace("!", "").strip()
        newBody = f'{num} пара перенесена в {temp}'
    elif "Увага! Заняття відмінено!" in body:
        newBody = f'{num} пару відмінено'
    else:
        newBody = body

    headers = {
            'Content-Type': 'application/json',
            'Authorization': 'key=' + serverToken,
          }

    body = {
            'content_available': True,
            'apns-priority': '5',
            'to': deviceToken,
            'data' : {'title': title, 'body': newBody, 'date': date, 'icon': 'change' }
            }
    print(json.dumps(body))
    response = requests.post("https://fcm.googleapis.com/fcm/send",headers = headers, data=json.dumps(body))
    print(response.status_code)
    print(response.json())

def transliterated(topic):
    dic = {'ь':'', 'ъ':'', 'а':'a', 'б':'b','в':'v',
           'г':'g', 'д':'d', 'е':'e', 'ё':'y','ж':'z',
           'з':'z', 'и':'i', 'і':'i', 'ї':'i', 'й':'y',
           'к':'k', 'л':'l', 'м':'m', 'н':'n', 'о':'o',
           'п':'p', 'р':'r', 'с':'s', 'т':'t', 'у':'u',
           'ф':'f', 'х':'h', 'ц':'c', 'ч':'c', 'ш':'s',
           'щ':'s', 'ы':'i', 'э':'e', 'є':'e', 'ю':'u',
           'я':'a', ' ':'', 'ь':'', '(':'', ')':''}
    transliterated = ''
    for i in topic:
        transliterated += dic.get(i.lower(), i.lower()) if i.isupper() else dic.get(i, i)
    return transliterated

def checkChanges():
    today = date.today()
    tomorrow = today + datetime.timedelta(days=1)
    tomorrow = tomorrow.strftime("%d.%m.%Y")
    print("Tomorrow's date:", tomorrow)
    arrayOfGroups = getListOfUsers(True)
    arrayOfTeachers = getListOfUsers(False)
    for teacher in arrayOfTeachers:
        convertedUrl = urllib.parse.quote(teacher, encoding='cp1251')
        URL = f"http://localhost//cgi-bin/timetable_export.cgi?req_type=rozklad&req_mode=teacher&OBJ_ID=&OBJ_name={convertedUrl}&dep_name=&begin_date={tomorrow}&end_date={tomorrow}&req_format=json&coding_mode=WINDOWS-1251&bs=ok"

        for i in range(3):
            try:
                r = requests.get(url = URL)
                if i>1:
                    print(f"trying to get data from {i+1} attempt")
                break
            except :
                continue
        else:
            print("problems with network")
            continue

        data = r.text
        data = data.replace(", \"item\":", ",")
        data = data.replace("\"item\": {", "\"item\": [{")
        data = data.replace("}}", "}]}")
        try:
            array = json.loads(data)
        except:
            continue

        lessons = array['item']
        for lesson in lessons:
            desc = lesson['lesson_description']
            teacher = lesson['teacher']
            num = lesson['lesson_number']
            print(teacher)
            if desc != "":
                if "Увага!" in desc:
                    transliteratedTeacher = transliterated(teacher)
                    topic = f'/topics/changesOf{transliteratedTeacher}'
                    print(f"{desc}\n{topic}\n{num}")
                    sendPushWith('Заміна', desc, num, topic, tomorrow)
    for group in arrayOfGroups:
        convertedUrl = urllib.parse.quote(group, encoding='cp1251')
        URL = f"http://localhost//cgi-bin/timetable_export.cgi?req_type=rozklad&req_mode=group&OBJ_ID=&OBJ_name={convertedUrl}&dep_name=&begin_date={tomorrow}&end_date={tomorrow}&req_format=json&coding_mode=WINDOWS-1251&bs=ok"

        for i in range(3):
            try:
                r = requests.get(url = URL)
                if i>1:
                    print(f"trying to get data from {i+1} attempt")
                break
            except :
                continue
        else:
            print("problems with network")
            continue

        data = r.text
        data = data.replace(", \"item\":", ",")
        data = data.replace("\"item\": {", "\"item\": [{")
        data = data.replace("}}", "}]}")
        try:
            array = json.loads(data)
        except:
            continue
        lessons = array['item']
        for lesson in lessons:
            desc = lesson['lesson_description']
            group = lesson['group']
            num = lesson['lesson_number']
            print(group)
            if desc != "":
                if "Увага!" in desc:
                    transliteratedGroup = transliterated(group)
                    topic = f'/topics/changesOf{transliteratedGroup}'
                    print(f"{desc}\n{topic}\n{num}")
                    sendPushWith('Заміна', desc, num, topic, tomorrow)

def main(sc):
    t = time.localtime()
    current_time = time.strftime("%H:%M:%S", t)
    print(f'{current_time} Checking changes...')
    checkChanges()
    s.enter(3600, 1, main, (sc,))
###############################End of implemetration############################

checkChanges()
s = sched.scheduler(time.time, time.sleep)
s.enter(3600, 1, main, (s,))
s.run()
