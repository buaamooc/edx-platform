#coding=utf-8
#!/usr/bin/python
from xml.sax         import make_parser
from xml.sax.handler import ContentHandler
import lxml
from lxml import etree
import socket
import select
import sys
import os
import time
from threading import Thread
from django.http import HttpResponse
from django import forms
from django.views.decorators.csrf import csrf_exempt

from django.views.decorators.csrf import csrf_protect
from django.shortcuts import render_to_response, render 
class Web_Client:
		def __init__(self,server,port):
			self.socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
			self.socket.connect((server,port))
			self.input=self.socket.makefile('rb',0)
			self.output=self.socket.makefile('wb',0)

		def Getnumber(self):
			SendData='<Getnumber></Getnumber>'
			self.output.write((SendData+'\r\n').encode('utf-8'))
			GetData=self.input.readline().strip().decode('utf-8')
			print(GetData)
			if GetData:                                                                                                                 
				try:
					info=etree.XML(GetData)
				except:
					return('')
				else:
					return(info.text)

		def Apply(self,UserName):
			SendData='<Apply>'+UserName+'</Apply>'
			self.output.write((SendData+'\r\n').encode('utf-8'))
			GetData=self.input.readline().strip().decode('utf-8')
			print(GetData)
			if GetData:
				try:
					info=etree.XML(GetData)
				except:
					return('')
				else:
					if (info.tag=='Result') and (info[0].text=='Machine is not enough.'):
						return(info[0].text,info[1].text)
					elif info[0].text=='Successful':
						return(info[0].text,info[1].text,info[2].text)
					elif info[0].text=='Reconnect':
						return(info[0].text,info[1].text,info[2].text,info[3].text,info[4].text)


		def Run(self,my_name,f):
			result=self.FileLoad(f,1,my_name)
			if result:
				return(result)
			else:
				return(self.Wait())

		def Wait(self):
			GetData=self.input.readline().strip().decode('utf-8') 	#接收数据
			print(GetData)
			if GetData:
				try:
					info=etree.XML(GetData)	#分析指令（XML方式）
				except:
					return('Fail')
				else:
					if info.tag=='Working':
						SendData='<Connect></Connect>'
						self.output.write((SendData + '\r\n').encode('utf-8'))
						return()
					else:
						self.error(2)
			else:
				self.error(1)

		def CancelWait(self,my_index):	#取消等待
			SendData='<Cancel>'+'<Index>'+my_index+'</Index>'+'</Cancel>'
			self.output.write((SendData + '\r\n').encode('utf-8'))

		def Getdata(self,my_ip,my_port):
			SendData='<GetData>'+'<Ip>'+my_ip+'</Ip>'+'<Port>'+my_port+'</Port>'+'</GetData>'
			self.output.write((SendData + '\r\n').encode('utf-8'))
			GetData=self.input.readline().strip().decode('utf-8')
			print(GetData)
			if GetData:
				info=etree.XML(GetData)
				if info.tag=='Data':
					#print('GetData:'+info.text)
					return(info.text)	

		def Setdata(self,my_data,my_ip,my_port):
			SendData='<SetData>'+'<Data>'+my_data+'</Data>'+'<Ip>'+my_ip+'</Ip>'+'<Port>'+my_port+'</Port>'+'</SetData>'
			self.output.write((SendData + '\r\n').encode('utf-8'))

		def FileLoad(self,f,n,my_name):
			Length=str(f.size)
			HashCode='10'
			SendData='<Load><Length>'+Length+'</Length><Hashcode>'+HashCode+'</Hashcode>'+'<Name>'+my_name+'</Name>'+'<Filename>'+'pri325_method2.bit'+'</Filename>'+'</Load>'
			self.output.write((SendData + '\r\n').encode('utf-8'))	#发送数据
			GetData=self.input.readline().strip().decode('utf-8')
			print(GetData)
			if GetData:
				info=etree.XML(GetData)
				if info.tag=='StartLoad':
					for chunk in f.chunks():
						filedata=chunk
						self.socket.send(filedata)
					print("sending over...")
			GetData=self.input.readline().strip().decode('utf-8')
			print(GetData)
			if GetData:
				try:
					info=etree.XML(GetData)
				except:
					return('Fail')
				if (info.tag=='Receive'):
					if  (info[0].text=='Successful'):	#客户端→服务器发送完毕
						return('')
					else:
						self.FileLoad(f)
				else:
					self.error(2)
			else: 
				self.error(1)


		def UserHeart(self,my_name):
			SendData='<UserHeart>'+'<UserName>'+my_name+'</UserName>'+'</UserHeart>'
			self.output.write((SendData + '\r\n').encode('utf-8'))

		def Manage(self):	#管理系统
			SendData='<Manage></Manage>'
			self.output.write((SendData + '\r\n').encode('utf-8'))
			GetData=self.input.readline().strip().decode('utf-8')
			print(GetData)
			try:
				info=etree.XML(GetData)
			except:
				return('')
			return(info.text)

		def Order(self):	#预约系统
			SendData='<Order></Order>'
			self.output.write((SendData + '\r\n').encode('utf-8'))
			GetData=self.input.readline().strip().decode('utf-8')
			print(GetData)
			try:
				info=etree.XML(GetData)
			except:
				return('')
			return(info.text)

		def Grade(self):	#评分系统
			SendData='<Grade></Grade>'
			self.output.write((SendData + '\r\n').encode('utf-8'))
			GetData=self.input.readline().strip().decode('utf-8')
			info=etree.XML(GetData)
			print(GetData)
			return(info.text)

		def GradeData(self,my_name):	#获取复现用户行为的数据
			SendData='<GradeData>'+my_name+'</GradeData>'
			self.output.write((SendData + '\r\n').encode('utf-8'))
			GetData=self.input.readline().strip().decode('utf-8')
			info=etree.XML(GetData)
			print(GetData)
			return(info.text)

		def Test(self,my_ip,my_port,my_name,f):	#自动评测系统
			SendData='<Test>'+my_name+'</Test>'
			self.output.write((SendData + '\r\n').encode('utf-8'))
			GetData=self.input.readline().strip().decode('utf-8') #服务器发来的测试结果数据		
			print(GetData)
			try:
				info=etree.XML(GetData)
			except:
				pass
			else:
				if info.tag=='TestResult':
					self.Break(my_name)
					#SendData='<TestFinish>'+my_name+'</TestFinish>'
					#self.output.write((SendData + '\r\n').encode('utf-8'))
				return(info.text)


		def Break(self,my_name):
			SendData='<Break>'+'<Name>'+my_name+'</Name>'+'</Break>'
			self.output.write((SendData + '\r\n').encode('utf-8'))
			GetData=self.input.readline().strip().decode('utf-8')
			print(GetData)
			if GetData:
				try:
					info=etree.XML(GetData)
				except:
					pass
				else:
					if (info.tag=='Broken'):
						SendData='<Broken></Broken>'
						self.output.write((SendData + '\r\n').encode('utf-8'))



		def Close(self):
			self.socket.close()

		def error(self,i):
			pass

def Web(request):
	'''if request.user.is_authenticated():
		print(request.user.username)	#用户名
	else:
		print('no')'''
	#print(request.META['REMOTE_ADDR'])
	my_name=request.user.username
	method=request.GET["type"]
	hostname="10.2.3.43"
	port=2000
	#主界面
	if method=="Number":
		m=Web_Client(hostname,port)
		mydata=m.Getnumber()
		return HttpResponse(mydata+','+my_name)
	if method=='Name':
		m=Web_Client(hostname,port)
		return HttpResponse(request.user.username)
	elif method=="Apply":
		m=Web_Client(hostname,port)
		Result=m.Apply(request.user.username)
		print(Result)
		if Result[0]=="Machine is not enough.":
			Addr=Result[0]+'-'+Result[1]
			return HttpResponse(Addr)
		elif Result[0]=="Successful":
			Addr=Result[1]+'-'+Result[2]
			return HttpResponse(Addr)
		elif Result[0]=="Reconnect":
			Addr=Result[0]+'-'+Result[1]+'-'+Result[2]+'-'+Result[3]+'-'+Result[4]
			return HttpResponse(Addr)
	elif method=='Cancel':
		m=Web_Client(hostname,port)
		my_index=request.GET["index"]
		m.CancelWait(my_index)
		return HttpResponse("0")
	elif method=="GetData":
		m=Web_Client(hostname,port)
		my_ip=request.GET["ip"]
		my_port=request.GET["port"]
		mydata=m.Getdata(my_ip,my_port)
		return HttpResponse(mydata)
	elif method=="SetData":
		m=Web_Client(hostname,port)
		my_data=request.GET["data"]
		my_ip=request.GET["ip"]
		my_port=request.GET["port"]
		m.Setdata(my_data,my_ip,my_port)
		return HttpResponse("2")
	elif method=="Break":
		#m=Web_Client(hostname,port)
		#my_data='ffffffffffffffffffffffffffffffff'
		#m.Setdata(my_data,my_ip,my_port)	#断开设备之前，将FPGA板上的数据初始化
		k=Web_Client(hostname,port)
		k.Break(request.user.username)
		return HttpResponse("0")
	elif method=='UserHeart':
		m=Web_Client(hostname,port)
		my_name=request.GET["username"]
		m.UserHeart(my_name)
		return HttpResponse("0")
	elif method=='Manage':
		m=Web_Client(hostname,port)
		my_data=m.Manage()
		return HttpResponse(my_data)
	elif method=='Order':
		m=Web_Client(hostname,port)
		my_data=m.Order()
		return HttpResponse(my_data)
	elif method=='Grade':
		m=Web_Client(hostname,port)
		my_data=m.Grade()
		return HttpResponse(my_data)
	elif method=='GradeData':
		m=Web_Client(hostname,port)
		my_name=request.GET['name']
		my_data=m.GradeData(my_name)
		return HttpResponse(my_data)

@csrf_exempt
def UpCode(request):
	method=request.GET["type"]
	hostname="10.2.3.43"
	port=2000
	#f =handle_uploaded_file(request.FILES['Filedata'])
	#return HttpResponse("hjk")
	my_name=request.user.username
	#print(f.path)
	if method=="Connect":
		f=request.FILES['Filedata']
		#print("文件信息")
		#print(f)		#文件名
		m=Web_Client(hostname,port)
		my_ip=request.GET["ip"]
		my_port=request.GET["port"]
		Address=m.Run(my_name,f)
		return HttpResponse("1")
	elif method=='Test':
		f=request.FILES['test_file']
		m=Web_Client(hostname,port)
		my_ip=request.GET["ip"]
		my_port=request.GET["port"]
		k1=m.Apply(my_name)
		if k1[0]=="Successful":			#有空闲设备用来测试
			m=Web_Client(hostname,port)
			k2=m.Run(my_name,f)
			m=Web_Client(hostname,port)
			data=m.Test(my_ip,my_port,my_name,f)
			return HttpResponse(data)
		else:		#无空闲设备
			return HttpResponse('Machine is not enough.')

def handle_uploaded_file(f):
    with open(f.name, 'wb+') as info:
        for chunk in f.chunks():
			print(chunk)
			info.write(chunk)
    return f
class UploadFileForm(forms.Form):
	title = forms.CharField(max_length=50)
	file = forms.FileField()

def working(request):
	print("asdfasdfsafdsafsdfsaasdfsadfsadfsadfsadfsdfasfsafdsfdsfadasfdfsdfasdsfd")
	method=request.GET["type"]
	if method=="GetData":
		return HttpResponse("0")
	elif method=="SetData":
		k=request.GET["data"]
		print(k)
		return HttpResponse("1")