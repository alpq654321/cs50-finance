import os

import sqlite3
import hashlib
import matplotlib.pyplot as plt
from pylab import *              
from flask import Flask, flash, redirect, render_template, request, session, url_for, jsonify
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd
# configure application
app = Flask(__name__)

num = 0
# ensure responses aren't cached
if app.config["DEBUG"]:
	@app.after_request
	def after_request(response):
		response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
		response.headers["Expires"] = 0
		response.headers["Pragma"] = "no-cache"
		return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = sqlite3.connect('finance.db')  #用户库
db2 = sqlite3.connect('info.db') #信息库

@app.route("/")
@login_required
def index(): #初始界面模块
	data = db2.execute("select id, shares, symbol from tbhave")  #得到所有的股票
	total_cash = 0
	for i in data:  #得到初始界面的所有股票当前状态
		if (i[0]==session["user_id"]):
			shares = i[1]
			symbol = i[2]
			stock = lookup(symbol)  #得到股票目前的状态
			total = shares * stock["price"]  
			total_cash += total
			db2.execute("update tbhave set price='" + usd(stock["price"])+"',total='"+usd(total)+"' where id='"+str(i[0])+"' and symbol='"+symbol+"'")
	Last_cash = db.execute('''select id,cash from users''') #得到还剩下的钱
	for i in Last_cash:
		if i[0]==session["user_id"]:
			Last_cash=i[1]
			break
	total_cash += Last_cash  #得到总价钱
	has = db2.execute("select id, symbol, name, shares, price, total from tbhave")
	rt = ""
	for i in has:  #输入进表格中
		if (i[0]==session["user_id"]):
			rt+='''
      <tr>
        <td>'''+str(i[1])+'''</td>
        <td>'''+str(i[2])+'''</td>
        <td>'''+str(i[3])+'''</td> 
        <td>'''+str(i[4])+'''</td>
        <td>'''+str(i[5])+'''</td>
      </tr>
    '''
	db2.commit();
	return render_template("index.html", stock=rt,cash=usd(Last_cash), total= usd(total_cash))

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy(): #购买模块
	if request.method == "GET":
		return render_template("buy.html")
	else:
		stock = lookup(request.form.get("symbol")) #查看是否有这个股票
		if not stock:
			return apology("Invalid symbol")
		try:
			shares = int(request.form.get("shares")) #查询输入的是否是一个正整数
			if shares < 0:
				return apology("You should input a positive integer")
		except: #如果连整数都不是发现异常
			return apology("You should input an integer")
		#上面这段和sell是一模一样的
		money = 0  #得到当前所拥有的钱
		data = db.execute("select id, cash from users")
		for i in data:
			if (i[0]==session["user_id"]):
				money = i[1]
		
		if float(money) < stock["price"] * shares: #如果钱已经不够了
			return apology("Not enough money")
		#买入成功
		db2.execute('''insert into tbhis
					(id,symbol,shares,price)
					values({},'{}',{},'{}')'''.format(session["user_id"],request.form.get("symbol"),int(request.form.get("shares")),usd(stock["price"])))
		db2.commit() #更新历史信息
		
		sum = stock["price"] * float(shares)
		db.execute('''update users set cash = cash - '''+str(sum)+''' where id = '''+str(session["user_id"]))
		db.commit() #更新剩余钱数
		
		data = db2.execute("select id, symbol, shares from tbhave") #更新还剩多少股票
		FLAG = 0 #FLAG表示这个股票是否早已在数据库中
		for i in data:
			if i[0]==session["user_id"] and i[1] == request.form.get("symbol"):
				FLAG = 1
				db2.execute("update tbhave set shares = shares + "+str(request.form.get("shares"))+ " where id = "+str(session["user_id"])+ " and symbol = '"+ request.form.get("symbol") + "'")
				db2.commit()
		
		if FLAG == 0: #发现没有
			db2.execute('''insert into tbhave
					(id,symbol,shares,name)
					values({},'{}',{},'{}')'''.format(session["user_id"],request.form.get("symbol"),int(request.form.get("shares")),stock["name"]))
		db2.commit()
		return redirect(url_for("index"))
		

@app.route("/history") #历史状态模块
@login_required
def history():
	his = db2.execute("select id, symbol, shares, price, transacted from tbhis")  #得到历史信息
	rt = ""
	for i in his: #以表格形式扔进html里
		if (i[0]==session["user_id"]):
			rt+='''<tr>
				<td>'''+str(i[1])+'''</td>
				<td>'''+str(i[2])+'''</td>
				<td>'''+str(i[3])+'''</td> 
				<td>'''+str(i[4])+'''</td>
			  </tr>
			  '''
	return render_template("history.html", histories=rt)

@app.route("/login", methods=["GET", "POST"])
def login(): #登录模块
	session.clear() #清除历史信息
	if request.method == "POST": #收到信息
		if not request.form.get("username"):  #如果没有输入用户名
			return apology("Please input your username")  
		elif not request.form.get("password"): #如果没有输入密码
			return apology("Please input your password")
		FLAG = 1  #用于判断是否存在有当前用户并且密码是否是对的
		ID = 0  #用于记录ID
		username = request.form.get("username")
		hash = request.form.get("password")
		
		md5 = hashlib.md5() #利用md5对密码进行加密
		md5.update(bytes(hash,encoding='utf-8'))
		hash = md5.hexdigest()
		
		data = db.execute("select username,hash,id from users")
		for i in data:
			if i[0]==username and i[1]==hash:  #如果在数据库中找到了
				FLAG = 0
				ID = i[2]  
		if FLAG == 1:  #如果没有找到
			return apology("invalid username and/or password")
		session["user_id"] = ID  #利用session记录下当前用户的ID
		return redirect(url_for("index"))  #返回到初始界面
	else:
		return render_template("login.html")  #如果没收到任何信息，仍然是登录界面

@app.route("/logout")
def logout(): #退出登录模块
	session.clear()
	return redirect(url_for("login"))

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote(): #查询模块
	if request.method == "POST": #提交申请
		info = lookup(request.form.get("symbol"))
		if not info:
			return apology("Invalid symbol")
		x=[]
		y=[]
		for i in range(0,100):
			x.append(i)
			y.append(info["pic"][99-i])
		frame = plt.gca()
		frame.axes.get_xaxis().set_visible(False)
		plt.plot(x, y, marker='o', mec='r', mfc='w')
		plt.legend() 
		plt.margins(0)
		plt.subplots_adjust(bottom=0.15)
		plt.ylabel("$ (/share)") #Y轴标签
		plt.title("price chart (from far to near)") #标题
		global num
		num += 1
		plt.savefig("static/test"+str(num)+".png")
		plt.close('all')
		return render_template("quoted.html", name=info["name"], symbol=info["symbol"], price=info["price"], id = "test"+str(num)+".png")  #已查完
	else:
		return render_template("quote.html")  
	

@app.route("/register", methods=["GET", "POST"])
def register(): #注册模块
	"""Register user."""
	if request.method == "POST":
		if not request.form.get("username"):   #与登录时一样，判断是否输入了用户名密码，并判断输入的两次密码是否一致
			return apology("Please input your username")
		elif not request.form.get("password"):
			return apology("Please input your password")
		elif len(request.form.get("password"))<6:
			return apology("The length of your password must be more than six")
		elif request.form.get("password") != request.form.get("passwordagain"):
			return apology("The two passwords are different")
		username = request.form.get("username")  
		hash = request.form.get("password")
		
		md5 = hashlib.md5() #利用md5对密码进行加密
		md5.update(bytes(hash,encoding='utf-8'))
		hash = md5.hexdigest()
		
		FLAG = 0  #用FLAG记录是否曾经出现过该用户，MAX表示ID的最大标识
		MAX = 0
		data = db.execute("select id, username from users")
		for i in data:
			if i[1]==username:
				FLAG = 1
			if i[0]>MAX:
				MAX=i[0]
		if FLAG == 1:
			return apology("The username has already exists")
		#表示可以注册，插入进数据库中，ID设为MAX+1
		db.execute('''insert into users
					(id,username,hash,cash)
					values({},'{}','{}',{})'''.format(MAX+1,username,hash,10000.00))
		db.commit()
		session["user_id"] = MAX+1
		return redirect(url_for("index"))
	else:
		return render_template("register.html")                

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell(): #出售模块
	if request.method == "GET":
		return render_template("sell.html")
	else:
		stock = lookup(request.form.get("symbol")) #检查是否有这个股票
		if not stock:
			return apology("Invalid symbol")
		try:  #尝试是否是正数，如果不是异常进入except
			shares = int(request.form.get("shares"))  #检查输入的数是否是正整数
			if shares < 0:
				return apology("You should input a positive integer")
		except:
			return apology("You should input an integer")
		
		data = db2.execute("select id, symbol, shares from tbhave")
		FLAG = 0 #是否满足条件
		for i in data:
			if i[0] == session["user_id"] and i[1] == request.form.get("symbol") and i[2] >= int(request.form.get("shares")):
				FLAG = 1
		if FLAG == 0:
			return apology("Not enough shares")
		
		db2.execute('''insert into tbhis
					(id,symbol,shares,price)
					values({},'{}',{},'{}')'''.format(session["user_id"],request.form.get("symbol"),-int(request.form.get("shares")),usd(stock["price"])))
		db2.commit() #更新历史信息
		
		sum = stock["price"] * float(shares)
		db.execute('''update users set cash = cash + '''+str(sum)+''' where id = '''+str(session["user_id"]))
		db.commit() #更新剩余钱数
		
		data = db2.execute("select id, symbol, shares from tbhave") #更新还剩多少股票
		for i in data:
			if i[0]==session["user_id"] and i[1] == request.form.get("symbol"):
				db2.execute("update tbhave set shares = shares - "+str(request.form.get("shares"))+ " where id = "+str(session["user_id"])+ " and symbol = '"+ request.form.get("symbol") + "'")
				db2.commit()
		
		db2.execute("delete from tbhave where shares=0") #清理卖光的股票
		db2.commit()
		return redirect(url_for("index"))
		

@app.route("/ad", methods=["GET", "POST"])
@login_required
def ad(): #查询模块
	return render_template("ad.html")  

@app.route("/add",methods=['POST']) #账户金钱+1
def add():
	db.execute("update users set cash = cash + 1 where id="+str(session["user_id"]))
	db.commit()
	return jsonify("ojbk")
	