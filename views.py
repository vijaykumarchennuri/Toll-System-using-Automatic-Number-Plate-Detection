from django.shortcuts import render
from django.template import RequestContext
from django.contrib import messages
from django.http import HttpResponse
from django.core.files.storage import FileSystemStorage
import pymysql
import os, sys
import glob
import numpy as np
import cv2
from PIL import Image
import pytesseract
import re
from datetime import date

global uname, vehicle_num

def clean2_plate(plate):
    gray_img = cv2.cvtColor(plate, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray_img, 110, 255, cv2.THRESH_BINARY)
    if cv2.waitKey(0) & 0xff == ord('q'):
        pass
    num_contours,hierarchy = cv2.findContours(thresh.copy(),cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if num_contours:
        contour_area = [cv2.contourArea(c) for c in num_contours]
        max_cntr_index = np.argmax(contour_area)
        max_cnt = num_contours[max_cntr_index]
        max_cntArea = contour_area[max_cntr_index]
        x,y,w,h = cv2.boundingRect(max_cnt)
        if not ratioCheck(max_cntArea,w,h):
            return plate,None
        final_img = thresh[y:y+h, x:x+w]
        return final_img,[x,y,w,h]
    else:
        return plate,None
    
def ratioCheck(area, width, height):
    ratio = float(width) / float(height)
    if ratio < 1:
        ratio = 1 / ratio
    if (area < 1063.62 or area > 73862.5) or (ratio < 3 or ratio > 6):
        return False
    return True
    
def isMaxWhite(plate):
    avg = np.mean(plate)
    if(avg>=115):
        return True
    else:
        return False
    
def ratio_and_rotation(rect):
    (x, y), (width, height), rect_angle = rect
    if(width>height):
        angle = -rect_angle
    else:
        angle = 90 + rect_angle
    if angle>15:
        return False
    if height == 0 or width == 0:
        return False
    area = height*width
    if not ratioCheck(area,width,height):
        return False
    else:
        return True

def number_plate_detection(img):
    img2 = cv2.GaussianBlur(img, (5,5), 0)
    img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    img2 = cv2.Sobel(img2,cv2.CV_8U,1,0,ksize=3)	
    _,img2 = cv2.threshold(img2,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    element = cv2.getStructuringElement(shape=cv2.MORPH_RECT, ksize=(17, 3))
    morph_img_threshold = img2.copy()
    cv2.morphologyEx(src=img2, op=cv2.MORPH_CLOSE, kernel=element, dst=morph_img_threshold)
    num_contours, hierarchy= cv2.findContours(morph_img_threshold,mode=cv2.RETR_EXTERNAL,method=cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(img2, num_contours, -1, (0,255,0), 1)    
    
    for i,cnt in enumerate(num_contours):
        min_rect = cv2.minAreaRect(cnt)
        if ratio_and_rotation(min_rect):
            x,y,w,h = cv2.boundingRect(cnt)
            plate_img = img[y:y+h,x:x+w]
            if(isMaxWhite(plate_img)):
                clean_plate, rect = clean2_plate(plate_img)
                if rect:
                    fg=0
                    x1,y1,w1,h1 = rect
                    x,y,w,h = x+x1,y+y1,w1,h1
                    plate_im = Image.fromarray(clean_plate)
                    text = pytesseract.image_to_string(plate_im, lang='eng')
                    return text

def RechargeAccount(request):
    if request.method == 'GET':
        global uname, vehicle_num
        #output = '<tr><td><font size='' color="black">Vehicle&nbsp;No</b></td>'
        output = '<td><input type="text" name="t1" style="font-family: Comic Sans MS" size="30" value="'+vehicle_num+'" readonly></td></tr>'
        context= {'data1':output}
        return render(request, 'RechargeAccount.html', context)

def ViewPayment(request):
    if request.method == 'GET':
        output = '<table border=1 align=center width=100%>'
        font = '<font size="" color="black">'
        output += "<tr>"
        dataset_columns = ['Vehicle', 'Amount', 'Payment Date']
        for i in range(len(dataset_columns)):
            output += "<th>"+font+dataset_columns[i]+"</th>"
        con = pymysql.connect(host='127.0.0.1',port = 3306,user = 'root', password = 'root', database = 'tollgate',charset='utf8')
        with con:
            cur = con.cursor()
            cur.execute("select * FROM payments")
            rows = cur.fetchall()
            for row in rows:
                output += "<tr><td>"+font+str(row[0])+"</td>"
                output += "<td>"+font+str(row[1])+"</td>"
                output += "<td>"+font+str(row[2])+"</td></tr>"
        context= {'data':output}
        return render(request, 'AdminScreen.html', context)       

def CollectPayment(request):
    if request.method == 'GET':
       return render(request, 'CollectPayment.html', {})

def isBalanceAvailable(vehicle):
    balance = 0
    con = pymysql.connect(host='127.0.0.1',port = 3306,user = 'root', password = 'root', database = 'tollgate',charset='utf8')
    with con:
        cur = con.cursor()
        cur.execute("select available_amount FROM recharge where vehicle_no='"+vehicle+"'")
        rows = cur.fetchall()
        for row in rows:
            balance = row[0]
            break
    if balance < 201:
        balance = 0
    return balance    
    

def CollectPaymentAction(request):
    global uname, vehicle_num
    if request.method == 'POST':
        today = date.today()
        myfile = request.FILES['t1']
        fname = request.FILES['t1'].name
        today = date.today()
        fs = FileSystemStorage()
        if os.path.exists('TollGateApp/static/test.png'):
            os.remove('TollGateApp/static/test.png')
        filename = fs.save('TollGateApp/static/test.png', myfile)
        img = cv2.imread('TollGateApp/static/test.png')
        number_plate = number_plate_detection(img)
        res2 = str("".join(re.split("[^a-zA-Z0-9]*", number_plate)))
        res2 = res2.strip().upper()
        print(res2+"=================")
        balance = isBalanceAvailable(res2)
        output = 'Account does not exists or insufficient funds'
        if balance > 0:
            db_connection = pymysql.connect(host='127.0.0.1',port = 3306,user = 'root', password = 'root', database = 'tollgate',charset='utf8')
            db_cursor = db_connection.cursor()
            student_sql_query = "update recharge set available_amount = available_amount - 200, transaction_status='Toll Amount Deducted', transaction_date="+str(today)+" where vehicle_no='"+res2+"'"
            db_cursor.execute(student_sql_query)
            db_connection.commit()
            output = 'Toll Amount Successfully Paid'

            db_connection = pymysql.connect(host='127.0.0.1',port = 3306,user = 'root', password = 'root', database = 'tollgate',charset='utf8')
            db_cursor = db_connection.cursor()
            student_sql_query = "INSERT INTO payments(vehicle_no,amount,payment_date) VALUES('"+res2+"','200','"+str(today)+"')"
            db_cursor.execute(student_sql_query)
            db_connection.commit()
        context= {'data':output}
        return render(request, 'CollectPayment.html', context)    
        

def UserLogin(request):
    if request.method == 'GET':
       return render(request, 'UserLogin.html', {})

def AdminLogin(request):
    if request.method == 'GET':
       return render(request, 'AdminLogin.html', {})

def index(request):
    if request.method == 'GET':
        return render(request, 'index.html', {})

def Signup(request):
    if request.method == 'GET':
       return render(request, 'Signup.html', {})
    
def AdminLoginAction(request):
    global uname
    if request.method == 'POST':
        username = request.POST.get('t1', False)
        password = request.POST.get('t2', False)
        if username == "admin" and password == "admin":
            context= {'data':'welcome '+username}
            return render(request, 'AdminScreen.html', context)
        else:
            context= {'data':'login failed'}
            return render(request, 'AdminLogin.html', context)   
    

def UserLoginAction(request):
    global uname, vehicle_num
    if request.method == 'POST':
        username = request.POST.get('t1', False)
        password = request.POST.get('t2', False)
        index = 0
        con = pymysql.connect(host='127.0.0.1',port = 3306,user = 'root', password = 'root', database = 'tollgate',charset='utf8')
        with con:
            cur = con.cursor()
            cur.execute("select username,password,vehicle_no FROM signup")
            rows = cur.fetchall()
            for row in rows:
                if row[0] == username and password == row[1]:
                    uname = username
                    vehicle_num = row[2]
                    index = 1
                    break		
        if index == 1:
            context= {'data':'welcome '+uname}
            return render(request, 'UserScreen.html', context)
        else:
            context= {'data':'login failed'}
            return render(request, 'UserLogin.html', context)

def ViewBalance(request):
    if request.method == 'GET':
        global uname
        output = '<table border=1 align=center width=100%>'
        font = '<font size="" color="black">'
        output += "<tr>"
        dataset_columns = ['Username', 'Vehicle', 'Available Amount', 'Last Transaction Status']
        output += "<tr>"
        for i in range(len(dataset_columns)):
            output += "<th>"+font+dataset_columns[i]+"</th>"
        con = pymysql.connect(host='127.0.0.1',port = 3306,user = 'root', password = 'root', database = 'tollgate',charset='utf8')
        with con:
            cur = con.cursor()
            cur.execute("select * FROM recharge")
            rows = cur.fetchall()
            for row in rows:
                if row[0] == uname:
                    output += "<tr><td>"+font+str(row[0])+"</td>"
                    output += "<td>"+font+str(row[1])+"</td>"
                    output += "<td>"+font+str(row[2])+"</td>"
                    output += "<td>"+font+str(row[3])+"</td></tr>"
        context= {'data':output}
        return render(request, 'UserScreen.html', context)            


def RechargeAccountAction(request):
    if request.method == 'POST':
        global uname
        vehicle = request.POST.get('t1', False)
        amount = request.POST.get('t2', False)
        card = request.POST.get('t3', False)
        cvv = request.POST.get('t4', False)
        today = date.today()
        con = pymysql.connect(host='127.0.0.1',port = 3306,user = 'root', password = 'root', database = 'tollgate',charset='utf8')
        flag = False
        output = "Error in recharging account" 
        with con:
            cur = con.cursor()
            cur.execute("select * FROM recharge")
            rows = cur.fetchall()
            for row in rows:
                if row[0] == uname and vehicle == row[1]:
                    db_connection = pymysql.connect(host='127.0.0.1',port = 3306,user = 'root', password = 'root', database = 'tollgate',charset='utf8')
                    db_cursor = db_connection.cursor()
                    student_sql_query = "update recharge set available_amount = '"+str(row[2] + float(amount))+"', transaction_status='Self Deposit', transaction_date="+str(today)+" where username='"+uname+"' and vehicle_no='"+vehicle+"'"
                    print(student_sql_query)    
                    db_cursor.execute(student_sql_query)
                    db_connection.commit()
                    output = 'Recharge Successful! New Balance : '+str(row[2] + float(amount))
                    flag = True
        if flag == False:
            db_connection = pymysql.connect(host='127.0.0.1',port = 3306,user = 'root', password = 'root', database = 'tollgate',charset='utf8')
            db_cursor = db_connection.cursor()
            student_sql_query = "INSERT INTO recharge(username,vehicle_no,available_amount,transaction_status,transaction_date) VALUES('"+uname+"','"+vehicle+"','"+amount+"','Self Deposit','"+str(today)+"')"
            db_cursor.execute(student_sql_query)
            db_connection.commit()
            print(db_cursor.rowcount, "Record Inserted")
            if db_cursor.rowcount == 1:
                output = 'Account Balance Updated & Available Balance : '+str(amount)
        context= {'data':output}
        return render(request, 'RechargeAccount.html', context)
            

def SignupAction(request):
    if request.method == 'POST':
        username = request.POST.get('t1', False)
        password = request.POST.get('t2', False)
        contact = request.POST.get('t3', False)
        gender = request.POST.get('t4', False)
        email = request.POST.get('t5', False)
        address = request.POST.get('t6', False)
        vehicle = request.POST.get('t7', False)
        vehicle = vehicle.strip().upper()
        output = "none"
        con = pymysql.connect(host='127.0.0.1',port = 3306,user = 'root', password = 'root', database = 'tollgate',charset='utf8')
        with con:
            cur = con.cursor()
            cur.execute("select username FROM signup")
            rows = cur.fetchall()
            for row in rows:
                if row[0] == username:
                    output = username+" Username already exists"
                    break
        if output == 'none':
            db_connection = pymysql.connect(host='127.0.0.1',port = 3306,user = 'root', password = 'root', database = 'tollgate',charset='utf8')
            db_cursor = db_connection.cursor()
            student_sql_query = "INSERT INTO signup(username,password,contact_no,gender,email,address,vehicle_no) VALUES('"+username+"','"+password+"','"+contact+"','"+gender+"','"+email+"','"+address+"','"+vehicle+"')"
            db_cursor.execute(student_sql_query)
            db_connection.commit()
            print(db_cursor.rowcount, "Record Inserted")
            if db_cursor.rowcount == 1:
                output = 'Signup Process Completed'
        context= {'data':output}
        return render(request, 'Signup.html', context)
      


