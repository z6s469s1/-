import sys
import time
import os

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import cv2

import numpy as np
import pandas as pd

import train_model

from imutils.video import VideoStream
from imutils.video import FPS
import imutils
import pickle

import time

useNeuralStick=False
face_detection_model="frozen_inference_graph_layer5_removeConv13.pb"
frozen_inference_graph="graph_layer5_removeConv13.pbtxt"


orderingTable=[]
#element: dishName:[orderingAmount,orderingCharge,tableCase]
orderingDish={}

#若在點餐介面 點擊各點餐menu的 + 或 - 將訊號射給攝相機的thread 請她處理點餐事件
orderingSignal=0



def pushDish(dishName,dishPrice,tableCase):
        exist= dishName in orderingDish.keys()
               
        if exist==True:
                orderingDish[dishName][0]+=1
                orderingDish[dishName][1]=orderingDish[dishName][0]*dishPrice
                orderingDish[dishName][2]=tableCase
        else:
                orderingDish[dishName]=[1,dishPrice,tableCase]


def popDish(dishName,dishPrice):
        exist= dishName in orderingDish.keys()
        
        if exist==True:
                

                if orderingDish[dishName][0]>=2:
                        orderingDish[dishName][0]-=1
                        orderingDish[dishName][1]=orderingDish[dishName][0]*dishPrice
                else:
                        del orderingDish[dishName]

def restate_orderingDish():
        orderingDish.clear()

def reload_orderingTable():
        orderingTable.clear()

        orderingTable_mainDish=pd.read_excel('ordering_table/orderingTable_mainDish.xlsx',encoding = 'utf-8')
        orderingTable_dish=pd.read_excel('ordering_table/orderingTable_dish.xlsx',encoding = 'utf-8')
        orderingTable_dessert=pd.read_excel('ordering_table/orderingTable_dessert.xlsx',encoding = 'utf-8')
        orderingTable_drink=pd.read_excel('ordering_table/orderingTable_drink.xlsx',encoding = 'utf-8')

        orderingTable.append(orderingTable_mainDish)
        orderingTable.append(orderingTable_dish)
        orderingTable.append(orderingTable_dessert)
        orderingTable.append(orderingTable_drink)


#(傳入圖片名稱 顯示圖片在menuBlock , 傳入數值決定使用哪種餐點種類的table)  
class menuBlock(QVBoxLayout):
        def __init__(self,imgPath,tableCase,_GUIcontroler):
                super(QVBoxLayout,self).__init__()
                self.parentProcess = _GUIcontroler
                self.parentProcess.entryOrderingFlag.connect(self.set_entryOrderingFlag)
                self.imgPath=imgPath
                self.tableCase=tableCase
                self.consumer=None
                self.setupUi()
                

        def setupUi(self):
                self.menuLabel=QLabel()
                self.menuLabel.setFont(QFont("Timers" , 18 ,  QFont.Bold))
                self.menuLabel.setText(self.imgPath+':'+"  "+str(orderingTable[self.tableCase]['price'][self.imgPath]))


                self.menuPicture = QLabel()
                self.menuPicture.setPixmap(self.getPixmap())

                self.amountTextLine = QLineEdit()
                #self.amountTextLine.setReadOnly(False)
                self.amountTextLine.setAlignment(Qt.AlignCenter)
                self.amountTextLine.setFont(QFont("Timers" , 18 ,  QFont.Bold))
                self.amountTextLine.setText("0")
                self.amountTextLine.setFixedSize(75,25)

                self.addBtn= QPushButton()
                self.addBtn.setText('+')
                self.addBtn.clicked.connect(self.addBtn_clicked)
                self.addBtn.setFixedSize(25,25)

                self.subBtn= QPushButton()
                self.subBtn.setText('-')
                self.subBtn.clicked.connect(self.subBtn_clicked)
                self.subBtn.setFixedSize(25,25)

                orderingInfo_layout=QHBoxLayout()
                orderingInfo_layout.addWidget(self.addBtn)
                orderingInfo_layout.addWidget(self.amountTextLine)
                orderingInfo_layout.addWidget(self.subBtn)

                layout = QVBoxLayout()

                layout.addWidget(self.menuLabel)
                layout.addWidget(self.menuPicture)
                layout.addLayout(orderingInfo_layout)

                self.addLayout(layout)

        
        #點餐按鈕 按下便更新consumer之orderingTable權重
        def addBtn_clicked(self):
                pushDish(self.imgPath,orderingTable[self.tableCase]['price'][self.imgPath],self.tableCase)
                self.amountTextLine.setText(str(orderingDish[self.imgPath][0]))
                
                global orderingSignal
                orderingSignal=1
        def subBtn_clicked(self):
                popDish(self.imgPath,orderingTable[self.tableCase]['price'][self.imgPath])

                exist=self.imgPath in orderingDish.keys()
                if exist==True:
                        self.amountTextLine.setText(str(orderingDish[self.imgPath][0]))
                else:
                        self.amountTextLine.setText("0")
                
                global orderingSignal
                orderingSignal=1
       
        #更換該menublock的餐點內容物(圖片及圖片上的餐點名稱)
        def changeMenu(self,imgPath):
                self.menuPicture.setPixmap(self.getPixmap(changeFlag=True,changePath=imgPath))
                self.imgPath=imgPath
                self.menuLabel.setText(imgPath+':'+"  "+str(orderingTable[self.tableCase]['price'][imgPath]))
                
                exist=self.imgPath in orderingDish.keys()
                if exist==True:
                        self.amountTextLine.setText(str(orderingDish[self.imgPath][0]))
                else:
                        self.amountTextLine.setText("0")

        #可選擇載入圖片的路徑是否和最一開始的初始化的圖片路徑一樣 若想載入其他圖片則須將changeFlag打開
        def getPixmap(self,changeFlag=False,changePath='000'):
                if changeFlag:
                        imgPath='dish_img/'+changePath+'.jpg'
                else:
                        imgPath='dish_img/'+self.imgPath+'.jpg'
                #如果用opencv讀取中文圖片會出錯 所需調整
                img = cv2.imdecode(np.fromfile(imgPath, dtype=np.uint8), -1)
                #img=cv2.resize(img,(250,200))

                height, width, bytesPerComponent = img.shape
                bytesPerLine = 3 * width
                cv2.cvtColor(img, cv2.COLOR_BGR2RGB, img)
                QImg = QImage(img.data, width, height, bytesPerLine, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(QImg)
                return pixmap

        def set_entryOrderingFlag(self, data):
                if data==1:
                        self.amountTextLine.setText("0")

class GUIcontroler(QWidget):
        registeredFlag = pyqtSignal(int)
        registeredName = pyqtSignal(str)

        entryOrderingFlag = pyqtSignal(int)

        def __init__(self):
                super(GUIcontroler, self).__init__()

                reload_orderingTable()  #初始化orderingTable

                self.setWindowTitle("Ordering System")
                
                self.startGUI = QWidget()
                self.orderingGUI = QWidget()
                self.registeredGUI = QWidget()
		
                self.init_startGUI()
                self.init_orderingGUI()
                self.init_registeredGUI()

                self.GUIstack=QStackedWidget(self)
                self.GUIstack.addWidget(self.startGUI)
                self.GUIstack.addWidget(self.orderingGUI)
                self.GUIstack.addWidget(self.registeredGUI) 

                self.GUIstack_display(0)

                self.webcan=webcam(self)
                self.webcan.consumerName.connect(self.orderingGUI_set_consumerName)
                self.webcan.detection_orderingSignal_flag.connect(self.orderingGUI_orderingEvent)
                self.webcan.ordering_webcam_img.connect(self.orderingGUI_webcamEvent)
                self.webcan.registered_webcam_img.connect(self.registeredGUI_webcamEvent)
                self.webcan.start()


                self.previousComsumer=""
        
        def GUIstack_display(self,i):
                self.GUIstack.setCurrentIndex(i)



        #####################################################################################################
        #                      Started Content GUI 
        #####################################################################################################
        
        def init_startGUI(self):
                label=QLabel()
                label.setAlignment(Qt.AlignCenter)
                label.setFont(QFont("Timers" , 28 ,  QFont.Bold))
                label.setText("歡迎使用VIP lab點餐系統")

                orderingBtn=QPushButton()
                orderingBtn.setFont(QFont("Timers" , 40 ,  QFont.Bold))
                orderingBtn.setText("點餐")
                orderingBtn.clicked.connect(self.startGUI_orderingBtn_clicked)
                orderingBtn.setFixedSize(400,200)

                registeredBtn=QPushButton()
                registeredBtn.setFont(QFont("Timers" , 40 ,  QFont.Bold))
                registeredBtn.setText("註冊")
                registeredBtn.clicked.connect(self.startGUI_registeredBtn_clicked)
                registeredBtn.setFixedSize(400,200)

                layoutMid=QHBoxLayout()
                layoutMid.addWidget(registeredBtn)
                layoutMid.addWidget(orderingBtn)




                layout = QGridLayout()
                layout.addWidget(label,0,1)
                layout.addLayout(layoutMid,1,1,Qt.AlignTop)
        

                self.startGUI.setLayout(layout)
        

        def startGUI_orderingBtn_clicked(self):
                self.entryOrderingFlag.emit(1)
                self.GUIstack_display(1)

        def startGUI_registeredBtn_clicked(self):
                self.entryOrderingFlag.emit(0)
                self.GUIstack_display(2)



        #####################################################################################################
        #                      Ordering GUI 
        #####################################################################################################
        def init_orderingGUI(self):
                self.orderingGUI_label=QLabel()
                self.orderingGUI_label.setAlignment(Qt.AlignCenter)
                self.orderingGUI_label.setFont(QFont("Timers" , 25 ,  QFont.Bold))
                self.orderingGUI_label.setText("   親愛的先生/小姐您好~歡迎光臨!")


                self.orderingGUI_webcam = QLabel()



                self.orderingGUI_restartBtn=QPushButton()
                self.orderingGUI_restartBtn.setFont(QFont("Timers" , 16 ,  QFont.Bold))
                self.orderingGUI_restartBtn.setText("返回上一頁")
                self.orderingGUI_restartBtn.clicked.connect(self.orderingGUI_restartBtn_clicked)
                self.orderingGUI_restartBtn.setFixedSize(150,100)


        




                self.orderingGUI_chargeTable=QTableWidget()
                self.orderingGUI_chargeTable.setFixedWidth(350)
                self.orderingGUI_chargeTable.setFont(QFont("Timers" , 16 ,  QFont.Bold))
                self.orderingGUI_chargeTable.setFrameShape(QFrame.NoFrame)  ##设置无表格的外框
                self.orderingGUI_chargeTable.setEditTriggers(QAbstractItemView.NoEditTriggers) #设置表格不可更改
                self.orderingGUI_chargeTable.setSelectionMode(QAbstractItemView.NoSelection)#不能选择
                self.orderingGUI_chargeTable.verticalHeader().setVisible(False)  #隱藏垂直的標頭 也就是col 0 的元素都隱藏
                #self.orderingGUI_chargeTable.horizontalHeader().setStretchLastSection(True)#设置第五列宽度自动调整，充满屏幕
                self.orderingGUI_chargeTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)#自動等宽
                
                
                self.orderingGUI_chargeTable.setColumnCount(3)
                self.orderingGUI_chargeTable.setHorizontalHeaderLabels(["品名","數量","價格"])


                self.orderingGUI_orderingBtn=QPushButton()
                self.orderingGUI_orderingBtn.setFont(QFont("Timers" , 16 ,  QFont.Bold))
                self.orderingGUI_orderingBtn.setText("確認點餐")
                self.orderingGUI_orderingBtn.clicked.connect(self.orderingGUI_orderingBtn_clicked)
                self.orderingGUI_orderingBtn.setFixedSize(150,100)


                charge_layout=QVBoxLayout()
                charge_layout.addWidget(self.orderingGUI_chargeTable)
                charge_layout.addWidget(self.orderingGUI_orderingBtn)


                

                #R_layout=QHBoxLayout()
                #R_layout.addLayout(charge_layout)
                #R_layout.addWidget(self.orderingGUI_webcam)
   

                

                
                #Vertical Container Widget        
                V_widget=QWidget()
                V_scroll_Layout=QVBoxLayout()
                H_scroll_Layout=[]

                self.orderingTableKey=[]

           

                self.menu_list=[]
                menuKind=["主餐:","菜餚:","甜點:","飲料:"]


                #Horizontal Layout of Container Widget
                for i in range(len(orderingTable)):
                        #Horizontal Container Widget        
                        H_widget = QWidget()

                        #讀取該店家有多少餐點項目
                        self.orderingTableKey.append(list(orderingTable[i].index))

                        temp=[]

                        #依照我們有的餐點項目數項 建置多少menu block 並加入倒Layout
                        H_widget_layout = QHBoxLayout()
                        for j in range(len(self.orderingTableKey[i])):
                                temp.append(menuBlock(self.orderingTableKey[i][j],i,self))
                                H_widget_layout.addLayout(temp[j])
                        H_widget.setLayout(H_widget_layout)     

                        self.menu_list.append(temp)

                        #Horizontal Scroll Area Properties
                        H_scroll = QScrollArea()
                        H_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                        H_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
                        H_scroll.setAutoFillBackground(True)
                        H_scroll.setWidgetResizable(True)
                        H_scroll.setFixedHeight(300)
                        H_scroll.setWidget(H_widget)
                        
        
                        #Horizontal Scroll Area Layer add 
                        H_scroll_Layout.append(QVBoxLayout())
                        H_scroll_Layout[i].addWidget(H_scroll)


                        kindLabel=QLabel()
                        kindLabel.setFont(QFont("Timers" , 28 ,  QFont.Bold))
                        kindLabel.setText(menuKind[i])

                        V_scroll_Layout.addWidget(kindLabel)
                        V_scroll_Layout.addLayout(H_scroll_Layout[i])
                        
                
                V_widget.setLayout(V_scroll_Layout)

                #Vertical Scroll Area Properties
                V_scroll = QScrollArea()
                V_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                V_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                V_scroll.setAutoFillBackground(True)
                V_scroll.setWidgetResizable(True)
                V_scroll.setWidget(V_widget)
                V_scroll.setFixedHeight(900)
                V_scroll.setFixedWidth(1000)

                #Vertical Scroll Area Layer add 
                V_Layout = QVBoxLayout()
                V_Layout.addWidget(V_scroll)

                menu_charge_layout=QHBoxLayout()
                menu_charge_layout.addLayout(V_Layout)
                menu_charge_layout.addLayout(charge_layout)



                layout = QGridLayout()
                layout.addWidget(self.orderingGUI_restartBtn,0,0,Qt.AlignLeft) 
                layout.addLayout(menu_charge_layout,1,0,1,1,Qt.AlignLeft)
                layout.addWidget(self.orderingGUI_label,0,2,Qt.AlignTop)
                layout.addWidget(self.orderingGUI_webcam ,1,2,Qt.AlignTop)



             


                self.orderingGUI.setLayout(layout)
        
        def orderingGUI_restartBtn_clicked(self):
                index=0
                for key in orderingDish:
                        self.orderingGUI_chargeTable.setItem(index,0, QTableWidgetItem(""))
                        self.orderingGUI_chargeTable.setItem(index,1, QTableWidgetItem(""))
                        self.orderingGUI_chargeTable.setItem(index,2, QTableWidgetItem(""))
                        index+=1

                self.entryOrderingFlag.emit(0)
                self.registeredFlag.emit(0)
                restate_orderingDish()
                self.GUIstack_display(0)

        def orderingGUI_orderingBtn_clicked(self):
                total=0
                for key in orderingDish.keys():       
                        total+=orderingDish[key][1]

                msg="您點餐的金額總共"+str(total)+"元，確認選擇餐點無誤並點餐？"
                orderingMessageBoxclicked = QMessageBox.question(self, 'message', msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

                if orderingMessageBoxclicked==QMessageBox.Yes :
                        for key in orderingDish.keys():       
                                dish=key
                                orderCount=orderingDish[key][0]
                                tableCase=orderingDish[key][2]
                                #print("dish::"+str(dish))
                                #print("ordercount:"+str(orderCount))
                                #print("tablecase:"+str(tableCase))
                                orderingTable[tableCase][self.previousComsumer][dish]+=orderCount

                        writePath=["orderingTable_mainDish.xlsx","orderingTable_dish.xlsx","orderingTable_dessert.xlsx","orderingTable_drink.xlsx"]
                        for i in range(len(writePath)):
                                orderingTable[i].to_excel("ordering_table/"+writePath[i], encoding='utf-8')
                
                        self.orderingGUI_restartBtn_clicked()
                        reload_orderingTable()
                        self.updateMenuOrder(self.previousComsumer)

                
           


        #先排序 該consumer之喜好食物之權重 在依照該排序去更該menu圖片
        def updateMenuOrder(self,name):
                newOrderlist=[]
                newOrder=[]
                for i in range(len(orderingTable)):
                        newOrderlist.append(orderingTable[i].sort_values(by=[name],ascending=False))
                        newOrder.append(list(newOrderlist[i].index))

                for i in range(len(self.menu_list)):
                        for j in range(len(self.menu_list[i])):
                                self.menu_list[i][j].changeMenu(newOrder[i][j])

        def orderingGUI_set_consumerName(self,data):
                #self.orderingGUI_label.setText("   親愛的"+data+"您好~歡迎光臨!")
                self.orderingGUI_label.setText("歡迎光臨"+data+"!")
                if self.previousComsumer!=data:
                        self.updateMenuOrder(data)

                self.previousComsumer=data

        def orderingGUI_orderingEvent(self,flag):
                if  flag==1:  #如果有人按下點餐+/-按鈕並射出信號告知此thread
                        #print(orderingDish)

                        for i in range(self.orderingGUI_chargeTable.rowCount()):
                                self.orderingGUI_chargeTable.removeRow(i)

                        self.orderingGUI_chargeTable.setRowCount(len(orderingDish))

                        index=0
                        for key in orderingDish:
                                self.orderingGUI_chargeTable.setItem(index,0, QTableWidgetItem(key))
                                self.orderingGUI_chargeTable.setItem(index,1, QTableWidgetItem(str(orderingDish[key][0])))
                                self.orderingGUI_chargeTable.setItem(index,2, QTableWidgetItem(str(orderingDish[key][1])))
                                index+=1

                        global orderingSignal
                        orderingSignal=0#使用完信號後把信號歸零        

        def orderingGUI_webcamEvent(self,frame):
                self.orderingGUI_webcam.setPixmap(self.getPixmap(frame))

        def getPixmap(self,frame):
                img=cv2.resize(frame,(500,400))
                height, width, bytesPerComponent = img.shape
                bytesPerLine = 3 * width
                cv2.cvtColor(img, cv2.COLOR_BGR2RGB, img)
                QImg = QImage(img.data, width, height, bytesPerLine, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(QImg)
                return pixmap

        #####################################################################################################
        #                      registered GUI 
        #####################################################################################################
       
        def init_registeredGUI(self):
                self.registeredGUI_L1=QLabel()
                self.registeredGUI_L1.setFont(QFont("Timers" , 28 ,  QFont.Bold))
                self.registeredGUI_L1.setAlignment(Qt.AlignCenter)
                self.registeredGUI_L1.setText("請輸入您的大名")

                dummyLabel=QLabel()
                dummyLabel.setFont(QFont("Timers" , 20 ,  QFont.Bold))
                dummyLabel.setAlignment(Qt.AlignCenter)
                dummyLabel.setText("    ")
          
                self.registeredGUI_textLine = QLineEdit()
                self.registeredGUI_textLine.setFont(QFont("Timers" , 28 ,  QFont.Bold))
                self.registeredGUI_textLine.setText("unknown")
                self.registeredGUI_textLine.setFixedSize(500,50)

                self.registeredGUI_sureBtn = QPushButton()
                self.registeredGUI_sureBtn.setFont(QFont("Timers" , 28 ,  QFont.Bold))
                self.registeredGUI_sureBtn.setText("確定")
                self.registeredGUI_sureBtn.clicked.connect(self.registeredGUI_sureBtn_clicked)
                self.registeredGUI_sureBtn.setFixedSize(200,100)

                self.registeredGUI_restartBtn=QPushButton()
                self.registeredGUI_restartBtn.setFont(QFont("Timers" , 16 ,  QFont.Bold))
                self.registeredGUI_restartBtn.setText("返回上一頁")
                self.registeredGUI_restartBtn.clicked.connect(self.registeredGUI_restartBtn_clicked)
                self.registeredGUI_restartBtn.setFixedSize(150,100)

                self.registeredGUI_webcam = QLabel()



                mid_layout=QVBoxLayout()
                mid_layout.addWidget(self.registeredGUI_L1)
                mid_layout.addWidget(self.registeredGUI_textLine)
                mid_layout.addWidget(dummyLabel)
                mid_layout.addWidget(self.registeredGUI_webcam)


                

                self.registeredGUI_layout = QGridLayout()
                #把個物件放到九宮格內並在各格內置中放置
                self.registeredGUI_layout.addWidget(self.registeredGUI_restartBtn,0,0,Qt.AlignLeft)
                self.registeredGUI_layout.addLayout(mid_layout,1,0,Qt.AlignCenter)
                self.registeredGUI_layout.addWidget(self.registeredGUI_sureBtn,2,0,Qt.AlignCenter)
              

                self.registeredGUI.setLayout(self.registeredGUI_layout)

        def registeredGUI_restartBtn_clicked(self):
                self.registeredGUI_L1.setText("請輸入您的大名")
                self.registeredGUI_textLine.setText("unknown")
                self.entryOrderingFlag.emit(0)
                self.registeredFlag.emit(0)
                self.GUIstack_display(0)
               
        def registeredGUI_sureBtn_clicked(self):
                if self.registeredGUI_textLine.text()=="unknown":
                        self.registeredGUI_L1.setText("您還沒輸入您的帳戶姓名")
                else:
                        self.registeredFlag.emit(1)
                        self.registeredName.emit(self.registeredGUI_textLine.text())

        def registeredGUI_webcamEvent(self,frame):
                self.registeredGUI_webcam.setPixmap(self.getPixmap(frame))

class webcam(QThread):
        consumerName = pyqtSignal(str)
        detection_orderingSignal_flag= pyqtSignal(int)
        ordering_webcam_img=pyqtSignal(object)
        registered_webcam_img=pyqtSignal(object)

        def __init__(self,_GUIcontroler):
                QThread.__init__(self)
                #註冊端 變數設定
                self.parentProcess = _GUIcontroler
                self.registeredFlag = 0   #註冊模式時 按下註冊按鈕後 變成1
                self.parentProcess.registeredFlag.connect(self.set_registeredFlag)
                self.registeredName = 0   #註冊模式時 使用者輸入的註冊姓名
                self.parentProcess.registeredName.connect(self.set_registeredName)
                #點餐端 變數設定
                self.entryOrderingFlag = 0 #1:表示已經進入點餐模式
                self.parentProcess.entryOrderingFlag.connect(self.set_entryOrderingFlag)
                self.orderingFlag=0       #代表可以開始辨識    0:表示剛剛從註冊端回來 可能有改變過模型 所以需要重新載入)
                                          #                   1:表示已經初始化過模型 可以開始辨識
                self.previousComsumer=""



        def run(self):

                print("[INFO] starting video stream...")
                vs = VideoStream(src=0).start()
                time.sleep(1.0)


                self.load_recognizeFaceModel()

                while (True):
                        frame = vs.read()
                        frame = imutils.resize(frame, width=600)
                        
                        
                        if self.registeredFlag==1:
                                self.registered(vs)
                                self.orderingFlag=0                             #為了讓load_recognizeFaceModel()只執行一次 

                        if self.entryOrderingFlag==1 and self.orderingFlag==0:  #如果你剛從註冊模式進入到點餐模式 則重新載入模型 
                                self.load_recognizeFaceModel()                  #並且將代表可以開始辨識的flag設成1
                                self.orderingFlag=1
                        
                        if self.entryOrderingFlag==1 and self.orderingFlag==1: #當orderingFlag=1 表示 模型已經更新 可以開始辨識
                                tStart = time.time()#計時開始
                                frame=self.recognizeFace(frame)
                                tEnd=time.time()#計時結束
                                print(tEnd-tStart)
                                
                                self.ordering_webcam_img.emit(frame)
                        else:
                                self.registered_webcam_img.emit(frame)

                        
                        self.detection_orderingEvent()

                        
                        
            
                     
                cv2.destroyAllWindows()
                vs.stop()

        
        def detection_orderingEvent(self):
                global orderingSignal   #提醒直譯器 orderingSignal是全域變數
                if  orderingSignal==1:  #如果有人按下點餐+/-按鈕並射出信號告知此thread
                        self.detection_orderingSignal_flag.emit(1)
                else:
                        self.detection_orderingSignal_flag.emit(0)
                      

        def registered(self,vs):
                

                data = pickle.loads(open("output/embeddings.pickle", "rb").read())
                
                                
                #若該使用者還未註冊過 則建立資料夾
                
                print("[INFO]registered people:")
                print(data["names"])
                print("Is "+self.parentProcess.registeredGUI_textLine.text()+" in dataset? "+str(self.parentProcess.registeredGUI_textLine.text() in data["names"]))

                if not (self.parentProcess.registeredGUI_textLine.text() in data["names"]):
                        self.parentProcess.registeredGUI_L1.setText("請上下左右搖晃您的臉頰")
                        i=0
                        dataset=[]
                        while i<30:
                                frame = vs.read()
                                frame = imutils.resize(frame, width=600)
                                dataset.append(frame)
                                self.registered_webcam_img.emit(frame)
                                time.sleep(0.2)
                                i += 1

                        self.registeredFlag=0

                        self.parentProcess.registeredGUI_L1.setText("人工智慧模型訓練中請稍後...")
                        img = cv2.imread("art/training.jpg")  #loading圖片
                        self.registered_webcam_img.emit(img)

                        self.extract_embeddings(dataset,self.registeredName)
                        train_model.training()

                        #將新的使用者增加到orderingTable 若該使用者註冊過則不多建立欄位到excel
                        _orderingTable_mainDish = pd.read_excel('ordering_table/orderingTable_mainDish.xlsx', encoding='utf-8')
                        _orderingTable_dish = pd.read_excel('ordering_table/orderingTable_dish.xlsx', encoding='utf-8')
                        _orderingTable_dessert = pd.read_excel('ordering_table/orderingTable_dessert.xlsx', encoding='utf-8')
                        _orderingTable_drink = pd.read_excel('ordering_table/orderingTable_drink.xlsx', encoding='utf-8')

                        if self.registeredName in _orderingTable_mainDish.columns:
                                print("該使用者已註冊過此系統")
                        else:
                                #將新的使用者 加入ordering table
                                _orderingTable_mainDish[self.registeredName]=_orderingTable_mainDish['unknown']*0
                                _orderingTable_mainDish.to_excel('ordering_table/orderingTable_mainDish.xlsx')

                                _orderingTable_dish[self.registeredName]=_orderingTable_dish['unknown']*0
                                _orderingTable_dish.to_excel('ordering_table/orderingTable_dish.xlsx')

                                _orderingTable_dessert[self.registeredName]=_orderingTable_dessert['unknown']*0
                                _orderingTable_dessert.to_excel('ordering_table/orderingTable_dessert.xlsx')
                                        
                                _orderingTable_drink[self.registeredName]=_orderingTable_drink['unknown']*0
                                _orderingTable_drink.to_excel('ordering_table/orderingTable_drink.xlsx')

                                #重新讀取 新的ordering table
                                reload_orderingTable()

                        self.parentProcess.registeredGUI_L1.setText("註冊完成!")
                else:
                        self.parentProcess.registeredGUI_L1.setText("重複註冊!")

                self.registeredFlag=0


        def extract_embeddings(self,dataset,userName):
                print("[INFO]extract embeddings...")
                knownEmbeddings = []

                for iface in range(len(dataset)):
                        print("[INFO] processing image "+str(iface+1)+"/"+str(len(dataset)))

                        image=dataset[iface]
                        image = imutils.resize(image, width=600)
                        (h, w) = image.shape[:2]
                        imageBlob = cv2.dnn.blobFromImage(cv2.resize(image, (300, 300)), 1.0, (300, 300),(104.0, 177.0, 123.0), swapRB=False, crop=False)
                        
                        self.detector.setInput(imageBlob)
                        detections = self.detector.forward()
                        
                        if len(detections) > 0:   #確保圖片中至少一個臉存在

                                    #若有複數臉從中挑選信心值最大的臉
                                    i = np.argmax(detections[0, 0, :, 2])
                                    confidence = detections[0, 0, i, 2]
                                    
                                    filter_confidence = 0.5

                                    if confidence > filter_confidence:#若信心值最大的臉高於filter_confidence才萃取特徵向量
                                            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                                            (startX, startY, endX, endY) = box.astype("int")
                                            face = image[startY:endY, startX:endX]
                                            (fH, fW) = face.shape[:2]
                                            
                                            if fW < 20 or fH < 20:
                                                    continue
                                                    
                                            faceBlob = cv2.dnn.blobFromImage(face, 1.0 / 255,(96, 96), (0, 0, 0), swapRB=True, crop=False)
                                            self.embedder.setInput(faceBlob)
                                            vec = self.embedder.forward()
                                            knownEmbeddings.append(vec.flatten())

                data = pickle.loads(open("output/embeddings.pickle", "rb").read())


                for i in knownEmbeddings:
                        data["embeddings"].append(i)
                        data["names"].append(userName)

                
                #print('data:\n{}'.format(data))
                f = open("output/embeddings.pickle", "wb")
                f.write(pickle.dumps(data))
                f.close()
                print("[INFO]completed")


        def set_registeredFlag(self, data):
                self.registeredFlag=data

        def set_registeredName(self, data):
                self.registeredName = data

        def load_recognizeFaceModel(self):
                # load our serialized face detector from disk
                print("[INFO] loading face detector...")
                protoPath = os.path.sep.join(["face_detection_model", frozen_inference_graph])
                modelPath = os.path.sep.join(["face_detection_model",face_detection_model])
                self.detector = cv2.dnn.readNetFromTensorflow(modelPath,protoPath)

                # load our serialized face embedding model from disk
                print("[INFO] loading face recognizer...")
                self.embedder = cv2.dnn.readNetFromTorch("openface_nn4.small2.v1.t7")


                if useNeuralStick:
                        print("[INFO]setting a neural stick is activated")
                        self.detector.setPreferableTarget(cv2.dnn.DNN_TARGET_MYRIAD)
                        self.embedder.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                

                # load the actual face recognition model along with the label encoder
                self.recognizer = pickle.loads(open("output/recognizer.pickle", "rb").read())
                self.le = pickle.loads(open("output/le.pickle", "rb").read())

        def recognizeFace(self,_frame):
                filter_confidence = 0.5
                frame = _frame
                name=""

                # resize the frame to have a width of 600 pixels (while
                # maintaining the aspect ratio), and then grab the image
                # dimensions
                frame = imutils.resize(frame, width=600)
                (h, w) = frame.shape[:2]

                # construct a blob from the image
                imageBlob = cv2.dnn.blobFromImage(
                cv2.resize(frame, (300, 300)), 1.0, (300, 300),
                (104.0, 177.0, 123.0), swapRB=False, crop=False)

                # apply OpenCV's deep learning-based face detector to localize
                # faces in the input image
                self.detector.setInput(imageBlob)
                detections = self.detector.forward()


                name_list=[]

                # loop over the detections
                for i in range(0, detections.shape[2]):
                        # extract the confidence (i.e., probability) associated with
                        # the prediction
                        confidence = detections[0, 0, i, 2]

                        # filter out weak detections
                        if confidence > filter_confidence:
                                # compute the (x, y)-coordinates of the bounding box for the face
                                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                                (startX, startY, endX, endY) = box.astype("int")

                                # extract the face ROI
                                face = frame[startY:endY, startX:endX]
                                (fH, fW) = face.shape[:2]

                                # ensure the face width and height are sufficiently large
                                if fW < 20 or fH < 20:
                                        continue

                                # construct a blob for the face ROI, then pass the blob
                                # through our face embedding model to obtain the 128-d
                                # quantification of the face
                                faceBlob = cv2.dnn.blobFromImage(face, 1.0 / 255, (96, 96), (0, 0, 0), swapRB=True, crop=False)
                                self.embedder.setInput(faceBlob)
                                vec = self.embedder.forward()

                                # perform classification to recognize the face
                                preds = self.recognizer.predict_proba(vec)[0]
                                j = np.argmax(preds)
                                proba = preds[j]
                                name = self.le.classes_[j]
                                name_list.append(name)

                                # draw the bounding box of the face along with the
                                # associated probability
                                text = "{}: {:.2f}%".format(name, proba * 100)
                                y = startY - 10 if startY - 10 > 10 else startY + 10
                                cv2.rectangle(frame, (startX, startY), (endX, endY),(0, 0, 255), 2)
                                cv2.putText(frame, text, (startX, y),cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 2)

                                
                if self.previousComsumer!=name and name!="" and not self.previousComsumer in name_list:
                        self.consumerName.emit(name)
                        self.previousComsumer=name


                return frame

        def set_entryOrderingFlag(self, data):
                self.entryOrderingFlag=data



if __name__ == "__main__":
    app = QApplication(sys.argv)
    MainWindow = GUIcontroler()
    MainWindow.showMaximized()

    sys.exit(app.exec_())

    









