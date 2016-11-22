
#This program is the first attempt at having a drawing method in the program
#it registers the positions, reocords them then can play them back,
#the program woked on 10/19 but was very rough. Need to implement with improved stepper control

import cv2
import speech_recognition as sr
import pyaudio
import numpy as np
import serial
import serial.tools.list_ports
import time
import math
from Tkinter import *
import tkMessageBox
import tkFileDialog
import copy

class Application(Frame, object):

#++++++++++++++++++++++++++++++++
    #import tkMessageBox
    def __init__(self, master):
        super(Application, self).__init__(master)
        #global variables within the app

        #Arm Measurements and Physical Parameters     
        self.Ls         = 8.367               #length of upperarm in inches
        self.Le         = 5.25                # length for forearm in inches
        self.initialZ   = 3.2          # height of the column when at its 0 position

        self.frameHeight = 320
        self.frameWidth = 640

        self.X  = self.Ls + self.Le
        
        self.Y  = 0.0
        self.Z  = 0.0
        self.Xd = self.Ls + self.Le
        self.Yd = 0.0
        self.Zd = 0.0
        self.phi = 0      #the shoulder angle
        self.theta = 0     #the elbow angle

        self.gripPos = 160




        #define the arduino USB port
        self.ser = serial.Serial('/dev/ttyACM0', 9600, timeout = .1) # This port is defined in the lower right of arduino ide

        self.loopStartStop = False

        self.currentSequence = "motion_recording.txt"	#the file name of recording prei-intialized to the default
        self.currentDirectoy = "/"						#defines the working directory of the user

        self.pack()
        self.createMenu()
        self.createWidgets()
		#self.speech()
        
        self.after(1000, self.looper())
#++++++++++++++++++++++++++++++++




    def createMenu(self):
        self.menubar = Menu(self)

		#file saving options
        #self.filemenu = Menu(self.menubar, tearoff = 0)

        self.filemenu = Menu(self.menubar, tearoff=0)
        self.filemenu.add_command(label="Open", command= self.openFile)
        self.filemenu.add_command(label= "New Sequence", command=self.newFile)

        self.filemenu.add_command(label="Save Sequence As", command=self.saveFileAs)
        self.filemenu.add_separator()
        self.filemenu.add_command(label="Exit", command=self.quit)
        self.menubar.add_cascade(label="File", menu=self.filemenu)

        self.interfacemenu = Menu(self.menubar, tearoff = 0)
        self.interfacemenu.add_command(label="Speech Control", command = self.listenCommand)
        self.menubar.add_cascade(label="Control Methods", menu=self.interfacemenu)

        # display the menu
        root.config(menu=self.menubar)
        
    def createWidgets(self):
        print "In create widgets"
        #XY Arc
        self.myCanvas = Canvas(self, height = self.frameHeight, width = self.frameWidth)
        self.myCanvas.bind("<Button-1>", self.newXYPos)
        self.myCanvas.bind("<B1-Motion>", self.drawing)
        coord = 0,0,self.frameWidth, self.frameWidth
        self.workspaceArc = self.myCanvas.create_arc(coord, start = 0, extent = 180, fill = "red", tags = "workspace")
        self.myCanvas.grid(row = 0, column = 0)

        #Holder frame for Height and Gripper
        self.heightAndGripFrame = Frame(self)
        self.heightAndGripFrame.grid(row = 0, column = 1)
        
        #Height
        self.heightLabel = Label(self.heightAndGripFrame, text = "Height (in)", width = 15)
        self.heightScroll = Scale(self.heightAndGripFrame, from_= 10, to = 0, resolution = 0.01, showvalue = 1, sliderlength = 20, length = 300, command = self.newZPos)
        self.heightLabel.grid(row = 0, column = 0)
        self.heightScroll.grid(row = 1, column = 0)

        #GRipper
        self.gripperLabel = Label(self.heightAndGripFrame, text="Gripper", width = 15)
        self.gripperScroll = Scale(self.heightAndGripFrame, from_= 50, to = 160, showvalue = 1, sliderlength = 50, length = 300, command = self.newGrip)
        self.gripperLabel.grid(row = 0, column = 1)
        self.gripperScroll.grid(row = 1, column = 1)
        self.gripperScroll.set(130)

        #TExt Update of Location
        self.posFrame = Frame(self)  #the frame to hold the 3 text fields
        self.posFrame.grid(row = 1, column = 1)
        #LAbels
        self.xName = Label(self.posFrame, text = 'X Position', width = 10)
        self.yName = Label(self.posFrame, text = 'Y Position', width = 10) 
        self.zName = Label(self.posFrame, text = 'Z Position', width = 10)
        self.xName.grid(row=0, column = 0)
        self.yName.grid(row=1, column = 0)
        self.zName.grid(row=2, column = 0)
        #Outputs                    
        self.xLabel = Label(self.posFrame, text = '', background = "white", width = 15)
        self.yLabel = Label(self.posFrame, text = '', background = "white",width = 15) 
        self.zLabel = Label(self.posFrame, text = '', background = "white", width = 15)
        self.xLabel.grid(row=0, column = 1)
        self.yLabel.grid(row=1, column = 1)
        self.zLabel.grid(row=2, column = 1)

        #record buttons
        self.recordButtons = Frame(self)
        self.recordButtons.grid(row = 1, column = 0 )

        self.spacerLabel4 = Label(self.recordButtons,   padx = 100)
        self.spacerLabel4.grid(row = 1, column = 2 )

        self.recordButton = Button(self.recordButtons, font = ("ARIAL", 16),text = "Record Position", width = 20, command = self.recordArmPos)
        self.recordButton.grid(row = 2, column = 2 )

        self.spacerLabel9 = Label(self.recordButtons,  padx = 100)
        self.spacerLabel9.grid(row = 3, column = 2 )

        self.playButton = Button(self.recordButtons, font = ("ARIAL", 16), text = "Play Sequence", width = 20, command = self.playback)
        self.playButton.grid(row = 4, column = 2 )

        self.clearButton = Button(self.recordButtons, font = ("ARIAL", 16), text = "Clear Sequence", width = 20, command = self.clearFile)
        self.clearButton.grid(row = 5, column = 2 )

        self.spacerLabel5 = Label(self.recordButtons,  padx = 100)
        self.spacerLabel5.grid(row = 6, column = 2 )

        #Go Home Button
        self.homeButton = Button(self.recordButtons, font = ("ARIAL", 16), text= "Go Home", width = 20, command = self.goHome)
        self.homeButton.grid(row = 7, column = 2 )


        #++++++++Looping+++++++++++++++++++

        loopStartButton = Button(self.recordButtons, font = ("ARIAL", 16), text = "Start Loop", width = 20, command = self.startLooper)
        loopStartButton.grid(row = 8, column = 2 )
        loopStopButton = Button(self.recordButtons, font = ("ARIAL", 16), text = "Stop Loop", width = 20, command = self.stopLooper)
        loopStopButton.grid(row = 9, column = 2 )

	
#++++++++++++++++++++++++++++++++

    def newZPos (self, event):
        print "In newZPos"
        self.Zd = self.heightScroll.get()
        self.Z = self.Zd
        #drive to the position
        self.move_it()

    def newGrip(self, event):
        print "in New GRip"
        self.gripPos = self.gripperScroll.get()
        self.move_it()

 #++++++++++++++++++++++++++++++++
       
    def newXYPos(self, event):
        print "In newXYPos"
        XPix = event.x
        YPix = event.y
        
        print XPix, YPix
        
        #Draw out the location
        toolThickness = 2
        #clear the canvas and then draw the new location
        self.myCanvas.delete("position")
        self.myCanvas.create_oval(event.x - toolThickness,
                                  event.y - toolThickness,
                                  event.x + toolThickness,
                                  event.y + toolThickness,
                                  fill = "blue",
                                  tags = "position")
                                  


        print "Current Pos: ", self.X, self.Y
        frameHeight = self.frameHeight
        frameWidth = self.frameWidth

        pix2inchX = (self.Ls + self.Le)/frameHeight            #workspace size in inches devided by pixels
        pix2inchY = ((self.Ls + self.Le)*2)/frameWidth


        #take the pixel location in the frame and convert it into a desired pos in the workspace
        Ypix = -(XPix - (frameWidth/2.0))       #check page 250 in desgn notebook for reasoning
        Xpix = -(YPix - (frameHeight))

        print "THE KINEMATICS"

        #the distance in inches in the camera frame
        self.Xd = Xpix * pix2inchX
        self.Yd = Ypix * pix2inchY              
        self.Zd = self.heightScroll.get()                                                   
        print "desired pos", '\t', self.Xd, '\t', self.Yd, '\t', self.Zd

        #determine the new joint angles of the arm using inverse kinematics
        #Inverse Kinematics
        d = math.sqrt((math.pow(self.Xd,2))+(math.pow(self.Yd,2)))
        print  "d = ", d
        #enter saftey to ensure that the desired pos is not outside the workspace
        if d < (self.Le+self.Ls):#) or (d > (Ls-Le)):
            #record(Xd,Yd,Zd)
            self.phi = math.degrees((math.atan2(self.Yd,self.Xd)) - (math.acos ( ((d**2)+(self.Ls**2)-(self.Le**2)) /(2*self.Ls*d)  ) ))  #prob in the acos #shoulder
            self.theta = math.degrees((math.acos(((d**2)-(self.Ls**2)-(self.Le**2))/(2*self.Ls*self.Le)))) #elbow
            print "phi and theta", '\t', self.phi, '\t', self.theta
            self.phi = round(self.phi, 1)
            self.theta = round(self.theta, 1)
            
            #drive to the position
            self.move_it()

            #determine the current position based on the angles from the kinematic values/ alternatively can just use the xd yd etc
            #as the current position to save computation. Though this is more reliable to make sure there are no rounding errors
            self.X = self.Ls*math.cos(math.radians(self.phi)) + ((self.Le)*(math.cos(math.radians(self.phi+self.theta))))
            self.Y =  self.Ls*math.sin(math.radians(self.phi)) + ((self.Le)*(math.sin(math.radians(self.phi+self.theta))))
            self.Z = self.Zd
            print "current pos", '\t', self.X, '\t', self.Y, '\t', self.Z

        self.updateTextPos()

           

#++++++++++++++++++++++++++++++++

    def drawing(self, event):
        print "In Drawing"
        XPix = event.x
        YPix = event.y
        
        print XPix, YPix                    
        print "Current Pos: ", self.X, self.Y
        frameHeight = self.frameHeight
        frameWidth = self.frameWidth

        pix2inchX = (self.Ls + self.Le)/frameHeight            #workspace size in inches devided by pixels
        pix2inchY = ((self.Ls + self.Le)*2)/frameWidth

        #take the pixel location in the frame and convert it into a desired pos in the workspace
        Ypix = -(XPix - (frameWidth/2.0))       #check page 250 in desgn notebook for reasoning
        Xpix = -(YPix - (frameHeight))

        print "THE KINEMATICS"
        #the distance in inches in the camera frame
        self.Xd = Xpix * pix2inchX
        self.Yd = Ypix * pix2inchY              
        self.Zd = self.heightScroll.get()                                                   
        print "desired pos", '\t', self.Xd, '\t', self.Yd, '\t', self.Zd

        #determine the new joint angles of the arm using inverse kinematics
        #Inverse Kinematics
        d = math.sqrt((math.pow(self.Xd,2))+(math.pow(self.Yd,2)))
        print  "d = ", d
        #enter saftey to ensure that the desired pos is not outside the workspace
        if d < (self.Le+self.Ls):#) or (d > (Ls-Le)):

            #record(Xd,Yd,Zd)
            self.phi = math.degrees((math.atan2(self.Yd,self.Xd)) - (math.acos ( ((d**2)+(self.Ls**2)-(self.Le**2)) /(2*self.Ls*d)  ) ))  #prob in the acos #shoulder
            self.theta = math.degrees((math.acos(((d**2)-(self.Ls**2)-(self.Le**2))/(2*self.Ls*self.Le)))) #elbow
            print "phi and theta", '\t', self.phi, '\t', self.theta

#+++++++++++++Consider removing this and just having limited floats
            self.phi = round(self.phi, 1)
            self.theta = round(self.theta, 1)

            #determine the current position based on the angles from the kinematic values/ alternatively can just use the xd yd etc
            #as the current position to save computation. Though this is more reliable to make sure there are no rounding errors
            self.X = self.Ls*math.cos(math.radians(self.phi)) + ((self.Le)*(math.cos(math.radians(self.phi+self.theta))))
            self.Y =  self.Ls*math.sin(math.radians(self.phi)) + ((self.Le)*(math.sin(math.radians(self.phi+self.theta))))
            self.Z = self.Zd
            print "current pos", '\t', self.X, '\t', self.Y, '\t', self.Z
            
            #record the position
            self.recordArmPos()
            
            #Draw out the location
            toolThickness = 2
            #clear the canvas and then draw the new location
            #self.myCanvas.delete("position")
            self.myCanvas.create_oval(event.x - toolThickness,
                                      event.y - toolThickness,
                                      event.x + toolThickness,
                                      event.y + toolThickness,
                                      fill = "black",
                                      tags = "positions")
            self.updateTextPos()
            
#++++++++++++++++++++++++++++++++
            
    def move_it(self):
        print "In Moveit"
        #this function sends the command of joint angles to the arduino to move the servos to the desired positions in real time with the GUI
        
        #self.ser.flushInput()
        #self.ser.flushOutput()

        command = str(self.phi) + ',' + str(self.Zd) + ',' + str(self.theta) + ',' + str(self.gripPos)+ '\n'        #here is the problem grip pos has a \n line in it when it is red
        print "------------------Sent to Arduino---------------------"
        print command
        self.ser.write(command)

        #wait until a repsonse if found from the arduino
        OK = 'no'
        while (OK != 'd'):
            #print "+\t++++\t++\t+"
            OK = self.ser.read(1)
        print "moving ahead"
        self.updateTextPos()

#++++++++++++++++++++++Function Definitions++++++++++++++

    def updateTextPos(self):
        print "In update text"
        self.xLabel.configure(text = round(self.X, 2))
        self.yLabel.configure(text =  round(self.Y, 2))
        self.zLabel.configure(text = round(self.Z, 2))

    def recordArmPos(self):
        print "In record arm pos"
        #This function records the current positions of the GUI and places them in a TXT file in the same directory as this program
        recordFile = open(self.currentSequence, 'a')
        recordFile.write(str(self.phi) + ',' + str(self.Zd) +   ',' + str(self.theta)+ ',' + str(self.gripPos) + '\n')

        #print (self.currentSequence)
        #recordFile.write(readPosCommand)
        recordFile.close()

##    def recordPause(self):
##        #This function records the current positions of the GUI and places them in a TXT file in the same directory as this program
##        pauseCommand = "pause" + '\n'
##        recordFile = open(selfcurrentSequence, 'a')
##        recordFile.write(pauseCommand)
##        recordFile.close()    

    def playback(self):
       print "In palyback"
       #This function reads the record file created in recordArmPos() and send the commands to the arm so that a sequence may be repeated.
       theRecordFile = open(self.currentSequence, 'r')
       allLines = theRecordFile.readlines()
       theRecordFile.close()
       print allLines
       for line in allLines:
           recordedCommand = line
           print"+++++++++Recorded Command++++++++++"
           print recordedCommand
           print"++++++++++++++++++++"
           #send the command to the arduino using another function
           parsedCommand = recordedCommand.split(',')
           self.phi = parsedCommand[0]
           self.Zd = parsedCommand[1]
           self.theta = parsedCommand[2]
           self.gripPos = parsedCommand[3].split('\n')              #change the variable name later
           self.gripPos = self.gripPos[0]
           print "gripPos = ", self.gripPos

           self.move_it()
           #self.sendRecordedCommand(self, recordedCommand)
       print ('Done')
       #self.heightScroll.set(self.Zd)
       #self.gripperScroll.set(self.gripPos)
  
    def listenCommand(self):
		
        r= sr.Recognizer()

        while True:
            with sr.Microphone() as source:
                print ("Say Something")
                audio = r.listen(source)



            try:
                spokeCommand = r.recognize_google(audio)
                print ("read" + spokeCommand)
            except sr.UnknownValueError:
                print ("Problem founder")
            except sr.RequestError as e:
                print ("Error 2")


            #Y
            if spokeCommand == 'right':
                #move +y
                self.Yd = self.Y + 3
                self.inverseKinematics()
			
            if spokeCommand == 'left':
                #move -y
                self.Yd = self.Y - 3
                self.inverseKinematics()

            #X
            if spokeCommand == 'front':
                #move +x
                self.Xd = self.X + 3
                self.inverseKinematics()
            if spokeCommand == 'back':
                #move -x
                self.Xd = self.X - 3
                self.inverseKinematics()

            #Z
            if spokeCommand == 'up':
                #move +x
                self.Xd = self.X + 1
                self.inverseKinematics()
            if spokeCommand == 'down':
                #move -x
                self.Xd = self.X - 1
                self.inverseKinematics()

            
            #GRripper
            if spokeCommand == 'clockwise':
                #move +y
                self.gripPos = self.gripPos - 30
                if self.gripPos < 180:
                    self.move_it()
            if spokeCommand == 'counterclockwise':
                
                self.gripPos = self.gripPos + 30
                if self.gripPos > 0:
                    self.move_it()
            if spokeCommand == 'close':
                #move close gripper slightly
                #move +y
                self.gripPos = self.gripPos - 30
                if self.gripPos < 180:
                    self.move_it()
            if spokeCommand == 'open':
                #move release gripper slightly
                #move +y
                self.gripPos = self.gripPos + 30
                if self.gripPos > 0:
                    self.move_it()

            if spokeCommand == 'record'
                self.recordArmPos()

            if spokeCommand == 'record'
                self.playback()

            if spokeCommand == 'kill':
                break


    def inverseKinematics(self):

        print "desired pos", '\t', self.Xd, '\t', self.Yd, '\t', self.Zd

        #determine the new joint angles of the arm using inverse kinematics
        #Inverse Kinematics
        d = math.sqrt((math.pow(self.Xd,2))+(math.pow(self.Yd,2)))
        print  "d = ", d
        #enter saftey to ensure that the desired pos is not outside the workspace
        if d < (self.Le+self.Ls):#) or (d > (Ls-Le)):
            self.phi = math.degrees((math.atan2(self.Yd,self.Xd)) - (math.acos ( ((d**2)+(self.Ls**2)-(self.Le**2)) /(2*self.Ls*d)  ) ))  #prob in the acos #shoulder
            self.theta = math.degrees((math.acos(((d**2)-(self.Ls**2)-(self.Le**2))/(2*self.Ls*self.Le)))) #elbow
            print "phi and theta", '\t', self.phi, '\t', self.theta
            self.phi = round(self.phi, 1)
            self.theta = round(self.theta, 1)
                
            #drive to the position
            self.move_it()

            #determine the current position based on the angles from the kinematic values/ alternatively can just use the xd yd etc
            #as the current position to save computation. Though this is more reliable to make sure there are no rounding errors
            self.X = self.Ls*math.cos(math.radians(self.phi)) + ((self.Le)*(math.cos(math.radians(self.phi+self.theta))))
            self.Y =  self.Ls*math.sin(math.radians(self.phi)) + ((self.Le)*(math.sin(math.radians(self.phi+self.theta))))
            self.Z = self.Zd
            print "current pos", '\t', self.X, '\t', self.Y, '\t', self.Z

            self.updateTextPos()	
		     

                              
    def goHome(self):
        print "In GoHome"
        #This function returns the robot to its initial positions and changed the GUI positions to match
        self.X  = 13.62
        self.Y  = 0.0
        self.Z  = 0.0
        self.Xd = 13.62
        self.Yd = 0.0
        self.Zd = 0.0
        
        self.phi = 0      #the shoulder angle
        self.theta = 0     #the elbow angle        
        #homePos = str(0) + ',' + str(0.0) + ',' + str(0)+ '\n'
        
        self.heightScroll.set(0)
            
        self.move_it()
            
    def clearFile(self):
        print "In clearFile"
        #this clears the file for a new sequence
        self.myCanvas.delete("positions")
        open(self.currentSequence, 'w').close()
            
    def saveFileAs(self):
        #This function is called by the menubar
        #this function opens the current set of commands in the file motion_recording.txt and saves the contents to a new
        print "Saving a File I see"
        #global currentSequence			#aacess the gloabl value of the current sequence
            
            #open the current file and copy its contents
        file = open(self.currentSequence, 'r')   
        textoutput = file.readlines()
        file.close()
            
            #open the new files and insert the contents
        theNewFile = tkFileDialog.asksaveasfilename(initialfile='Untitled.txt',defaultextension=".txt",filetypes=[("All Files","*.*"),("Text Documents","*.txt")])

        file = open(theNewFile, 'w')
        file.writelines(textoutput)		#not the writelines. write does not enter the data correctly from readlines
        file.close()
            
            #update the working file
        self.currentSequence = theNewFile	#update the file that is being used universally

    def openFile(self):
        #this function sets the file that is being edited and recorded into
        #global currentSequence
        self.currentSequence = tkFileDialog.askopenfilename(initialdir = "/",title = "Select file",filetypes = (("txt files","*.txt"),("all files","*.*")))
        print (self.currentSequence)
            
    def newFile(self):
        #this function created a new .txt file to hold imput commands
        #global currentSequence
            
            #open a new fle 
        theNewFile = tkFileDialog.asksaveasfilename(initialfile='Untitled.txt',defaultextension=".txt",filetypes=[("All Files","*.*"),("Text Documents","*.txt")])	#names the file and sets the location
        file = open(theNewFile, 'a')   #creates the file
        file.close()
        
        self.currentSequence = theNewFile	#update the file that is being used universally

    def looper(self):
        print "In looper"
        #this function loops through a the current sequence repeatedly.
        #startStop is the boolean bit that stats looping
        if self.loopStartStop == 1:
            self.playback()
            print "IN Looper"
        self.after(1000, self.looper)	

    def startLooper(self):
        #self.loopStartStop
        self.loopStartStop = 1
        print "IN Looper2"

    def stopLooper(self):
        #self.loopStartStop	
        self.loopStartStop = 0
        print "IN Looper 3"
            



#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++






    def Zpix2inch(pixRadius):
        #this function converts the radius of the marker into a measured distance using a function determined by measured tasks.
        pixRatio = -3.0/50.0                        #assming linear realtionship of 3 inches causes a change of 50 pixels in the radius++will always be a negative slope
        yInt = 10                                   #the intercept for the linear function of the pixel ratio
        distInch = (pixRadius * pixRatio) + 10
        return distInch
        
##    def record(self):
##        file = open("recording.txt", 'a')
##        file.write(str(self.X)+','+str(self.Y)+','+str(self.Z)+'\n')
##        file.close


    








root =Tk()
root.title("ShopArm V1")
#insert file dialog here
app = Application(root)

root.mainloop()


