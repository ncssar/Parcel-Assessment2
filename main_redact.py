
###
##  Stuff to do:
##     add try around sts requests in case they timeout
##     save markers, track, savetrack in a file for session restart (possibly have a save_markers instead of a xfer flag 
##     add check for 'confirm' and notice, if status button pushed when not confirmed
##
###

### need AppTrack and LEmarkers folders to exist on map
import platform
######import android.telephony.TelephonyManager
#from jnius import autoclass
from kivy.app import App
from kivy.logger import Logger
from kivy.config import Config
from plyer import gps
from plyer import uniqueid
#from plyer.platforms.android import activity
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout      # not used
from kivy.uix.behaviors import ButtonBehavior   # not used
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton
from kivy.clock import Clock
from kivy.core.window import Window
from oscpy.server import OSCThreadServer
from sartopo_python import SartopoSession
from android.permissions import request_permissions, Permission, check_permission
import time
import os
import json
import certifi

activityport = 3001
serviceport  = 3000
SERVICE_NAME = u'{packagename}.Service{servicename}'.format(packagename=u'org.kivy.LEchk', servicename=u'Keepalive')
osc = OSCThreadServer()
#### Config.set('kivy','exit_on_escape','0')  # disables operation of escape button

##  see defines below in code
# ANDROID 
# SARTOPO 

symbol_dict = { 'icon-U8S4VB1E-24-0.5-0.5-ff': "(S)",  'icon-UMQ1GFHD-24-0.5-0.5-ff': "(NC)",
                'icon-4H3T1151-24-0.5-0.5-ff': "(E)"}
os.environ['SSL_CERT_FILE'] = certifi.where()
###  temporary here
####Context = autoclass('android.content.Context')

def main():

    app = GPSApp()
    #print("At main")
    Window.bind(on_request_close=GPSApp.check_close)
    app.run()
    


class GPSApp(App):
    chk_end_proc = 0

    def build(self):           ## called at start of program execution
        #

        plat = platform.architecture()
        print("ARCH1:%s"%str(plat))
        if "Win" in plat[1]:
           self.ANDROID = 0       ###  running on ANDROID or PC ???
        else:
           self.ANDROID = 1
           from android import AndroidService
           service = AndroidService('Keepalive', 'running')
           service.start('service started')
           #print("After service start")

        osc.listen(address='127.0.0.1', port=serviceport, default=True)
        osc.bind(b'/tracker_api', self.tracker_callback)
        #print("After osc bind")

        self.imt=imtext()     ## called to build UI
        self.imt.GPSPTR = self
        self.SARTOPO = 1  ## sets flag to include code to talk to sartopo
        #
        self.sts = None
        self.link = -1
        self.foldLEm = ""     # will hold ID of LEmarkers folder from sartopo map
        self.foldAT = ""
        self.ID = None
        self.imt.mURLx = ""
        self.imt.csignx = ""
        self.ActMapSet = 0
        #print('@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@%s'%self)
        
        self.ActMap_mapID = '1DE6'
        self.cnt = 0
        self.since = 0        # time of previous save to sartopo
        ###self.startTrack = 1
        self.getGPSloc = 1    # flag to save GPS loc to track on next tick 
        self.imt.confirm = 0
        self.Resume = -1      # -1, not set; 1, yes; 0, no
        self.xmess = "Resume session? (y/n):" 
        self.xmess2 = "Enter auth code:" 
        self.timerTick = 5
        self.TIMEOUT = 4      # sets update for server connection to TIMEOUT * timerTick
        self.timerCnt = self.TIMEOUT
        self.save_path = "LEchk_save.json"
        self.save_path2 = "LEchk_save2.json"
        self.code = ""
### check set auth
        self.auth = 0
        self.exist = 0 
        if os.path.isfile(self.save_path2):                      # file exists ?
            self.exist = 1
                #chk if auth set, if not chk auth
        else:   # init authorizaion
            self.idPhone = uniqueid.id
            self.imt.info.text = self.idPhone   # phone id     have user enter 6 digit cidr and hit enter to move forward
                                                #              that will set auth in file
            ##return(self.imt)   ##causes window to be displayed
           
### check for files to resume
        #print("B4 check file")
        if os.path.isfile(self.save_path) and self.exist == 1:  # file exists
            mtime = int(os.path.getmtime(self.save_path))       # mod time in seconds 
            curTime = int(time.time())
            #print("TIME:"+str(mtime)+":"+str(curTime))
            if (curTime - mtime) < 84600:    # within a day
               self.imt.info.text = self.xmess
            else:
               self.Resume = 0     # set to 0 indicating do not need to ask question
        else:
           self.Resume = 0
        self.accountName="ncssarnc@gmail.com"     ## obviscate  ## redact
###   add in self.accountName="<acct>"
        if self.SARTOPO == 1:
           #print("AT REQUEST")
           if self.ANDROID == 1:
              request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.ACCESS_FINE_LOCATION, 
                                   Permission.ACCESS_COARSE_LOCATION, Permission.READ_PHONE_STATE])
           self.stsfile = "./sts.ini"    ## should use more general path resolution
           ###self.stsfile = "/storage/emulated/0/kivy/sts.ini"    ## should use more general path resolution
        return(self.imt)   ##causes window to be displayed

    ###def tracker_callback(self, message, *args):
    def tracker_callback(self, message):
        pass
        #print("got a message from the server:%s"% message.decode('utf8'))
        ##osc.send_message(b'/ui_api', ["AT UI callback<<<<<<<<<<<<<<<<<<<<<<<".encode('utf8'), ], '127.0.0.1', activityport)

    def on_start(self):              ## is on_start wrt start of this app?
        plat = platform.architecture()
        #print("ARCH2:%s"%str(plat))
        if "Win" in plat[1]:
           self.ANDROID = 0          ###  running on ANDROID or PC ???
        else:
           self.ANDROID = 1
        #Logger.info("Called start")
        #print("at start")
        self.markers = []
        self.vals = [0, 1, 2, 3]    # just a holder when GPS not defined
        Clock.schedule_interval(self.on_timer, self.timerTick)
        if self.ANDROID == 1:
            #print("ANDROID gps configure")
            gps.configure(
                on_location=self.on_location
            )
            gps.start()
        osc.send_message(b'/ui_api', ["THIS IS UI>>>>>>>>>>>>>>>>>>>>>>>>".encode('utf8'), ], '127.0.0.1', activityport)
        #print("Fart")   ##  printed in log


    def check_close(self, **kwargs):
        #print('AAA BBB CCC')
        if GPSApp.chk_end_proc == 0:
           GPSApp.chk_end_proc = 1
           return True
        else:
           osc.send_message(b'/ui_api', ["END_TASK".encode('utf8'), ], '127.0.0.1', activityport)
           return False

    def on_location(self, **kwargs):  ## called at GPS input
        #Logger.info("Called on_location")
        self.vals = []
        for key, val in kwargs.items():
           self.vals.append(val)
        ## #Logger.critical(str(self.markers))   
####  Could have a timer such that unless it has a tick, the point is dumped
####      Want to get the most recent when there is a Marker push
        #print("location")


    def on_timer(self, event):        ## called at timer tick
        #Logger.critical(str(self.markers))   
        Logger.critical(self.imt.mURLx)
        print("Timer called",self.imt.mURLx,self.imt.csignx)
        # run algorithm
        print("CODE, EXIST:"+str(self.code)+':'+str(self.exist))
        if self.code != "" and self.exist == 0:   # do this if code is non-zero and file does not exist
'''
section redacted
'''
                print('CODE:'+str(code2))
         # compare, say OK or reenter, set auth 
                if self.code == code2:
                    self.auth = 1
                    print('MATCH'+str(self.code))
                    with open(self.save_path2, 'w') as outfile:  ## opens, write, closes
                        json.dump([self.auth, 0, 0], outfile)    ## write
                    print('WRITEN'+str(self.auth))
                    self.imt.info.text = ""
                    self.exist = 1
                return 


        self.timerCnt += 1
        print("AFTER")
        if self.timerCnt < self.TIMEOUT:
           return       # wait to do the following
        self.timerCnt = 0        
### only get down here every timerTick * TIMEOUT seconds
#      save to file
        with open(self.save_path, 'w') as outfile:  ## opens, saves, closes
            json.dump([self.markers], outfile) ## save 

        self.url="sartopo.com/m/"+self.imt.mURLx     ## need to put after field filled-in`
        ##$ self.url="localhost:8080/m/K63"         ## need to put after field filled-in`
        parse=self.url.replace("http://","").replace("https://","").split("/")
        domainAndPort=parse[0]
        mapID=parse[-1]
        #print("At send message - timer in UI")
        osc.send_message(b'/ui_api', ["THIS IS UI at SARTOPO>>>>>>>>>>>>>>>>>>>>>>>>".encode('utf8'), ], '127.0.0.1', activityport)
        self.link = -1      # reset value for next check
        if self.SARTOPO == 1 and self.imt.confirm == 1:    # mURL and csign need to be set
####  insert conn to ActiveMapsList 1DE6 to save off this URL to enable combiner checking at the server
          if self.ActMapSet == 0:
            if "sartopo" in domainAndPort:
              self.sts=SartopoSession(domainAndPort=domainAndPort,mapID=self.ActMap_mapID,
                                         configpath=self.stsfile,
                                         account=self.accountName)
            else:
              self.sts=SartopoSession(domainAndPort=domainAndPort,mapID=self.ActMap_mapID)
            self.link=self.sts.apiVersion      ## if returns -1 do not have connection; if so call above
                                              #    again and recheck
            #Logger.info("API version:"+' '+str(self.link))                  
            if self.link == -1:  
              #Logger.info("No connection to server chk act map:%i"% self.Resume)
              return       # no connection 
            self.ActMapSet = 1
            folders = self.sts.getFeatures("Marker")
            #print("At folders:%s"%str(json.dumps(folders,indent=2)))
            fndMarker = 0
            for folder in folders:
              #print("FOLDER:%s"%folder)
              if folder["properties"]["class"] == "Marker":
                 #print("found folder"+str(folder))
                 if mapID == folder['properties']['title']:   # chk if marker for this map exist in act map db
                    fndMarker = 1
            if fndMarker == 0:
              result = self.sts.addMarker("39.27","-121.02",title=self.imt.mURLx) # add marker having URL NAME

          if "sartopo" in domainAndPort:    # check this map's URL
              self.sts=SartopoSession(domainAndPort=domainAndPort,mapID=mapID,
                                         configpath=self.stsfile,
                                         account=self.accountName)
          else:
              self.sts=SartopoSession(domainAndPort=domainAndPort,mapID=mapID)
          self.link=self.sts.apiVersion      ## if returns -1 do not have connection; if so call above
                                              #    again and recheck
          #Logger.info("API version:"+' '+str(self.link))                  
          if self.link == -1:  
            #Logger.info("No connection to server:%i"% self.Resume)
            if self.Resume != -1:              # wait for answer to Resume question
               self.imt.info.text = "No connection to server"
            self.imt.info.foreground_color = (1,0,0,1)
            return       # no connection 
        #####   got connection so put stuff on the map
          if self.foldLEm == "":                # get folder id (only once)
            folders = self.sts.getFeatures("Folder")
            fndFolder = 0
            for folder in folders:
              #print("FOLDER:%s"%folder)
              if folder["properties"]["title"] == "LEmarkers":
                self.foldLEm = folder["id"]
                fndFolder = 1
            if fndFolder == 0:
              self.sts.addFolder(label="LEmarkers")  # create the folder
          #Logger.info("Server connected")
          self.imt.info.text = "Server connected"
          self.imt.info.foreground_color = (0,1,0,1)
        ## sequence through markers (look for new ones; checkoff as sent)
          for mark in self.markers:
            if mark[4] == 0:
              #print("B4 marker call")
              result = self.sts.addMarker(mark[0],mark[1],title=self.imt.csignx,description=mark[3],symbol=mark[2],folderId=self.foldLEm) # add marker
              #print("AFT marker call")
              if result != None and result != -1:   ## implies xfer to server was completed, result is ID
                 mark[4] = 1          ## set as xfered

class imtext(FloatLayout):            ## builds the UI
    def __init__(self, **kwargs):
        super(imtext, self).__init__(**kwargs)
        self.GPSPTR = 0   # preset a value
        plat = platform.architecture()
        print("ARCH3:%s"%str(plat))
        if "Win" in plat[1]:
           self.ANDROID2 = 0       ###  running on ANDROID or PC ???
           scale = 0.3    
        else:
           self.ANDROID2 = 1
           scale = 1.0
        self.size=(700,2000)   # does not seem to set the initial size
        print("Here")
        self.add_widget(Label(text="Enter Map URL",size_hint=(0.1,0.2),pos=(100,scale*1550)))
        self.mURL = TextInput(text='', multiline=False,size_hint=(0.2,0.03),pos=(320,scale*1720))
        self.mURL.bind(on_text_validate=self.on_input)
        self.add_widget(self.mURL)

        self.add_widget(Label(text="Enter Callsign",size_hint=(0.1,0.2),pos=(100,scale*1400)))
        self.csign = TextInput(text='', multiline=False,size_hint=(0.2,0.03),pos=(320,scale*1580))
        self.csign.bind(on_text_validate=self.on_input2)
        self.add_widget(self.csign)

        self.info = TextInput(text='', multiline=False,size_hint=(0.5,0.03),pos=(220,scale*1300))
        self.info.bind(on_text_validate=self.on_input3)
        self.add_widget(self.info)

        self.confirmbtn = Button(text='Confirm',size_hint=(0.2,0.03),pos=(100,scale*1440))  # confirm entries to URL, CSIGN
        self.add_widget(self.confirmbtn)
        self.confirmbtn.bind(on_press=self.on_pressC)

        self.Sbtn = Button(text='S',size_hint=(None,None),size=(100,100),pos=(200,300),background_normal='./Sicon@2x.png')
        self.add_widget(self.Sbtn)
        self.Sbtn.bind(on_press=self.on_pressS)
        self.Ebtn = Button(text='E',size_hint=(None,None),size=(100,100),pos=(400,300),background_normal='./Eicon@2x.jpg')
        self.add_widget(self.Ebtn)
        self.Ebtn.bind(on_press=self.on_pressE)
        self.NCbtn = Button(size_hint=(None,None),size=(100,100),pos=(600,300),background_normal='./NCicon@2x.png')
        self.add_widget(self.NCbtn)
        self.NCbtn.bind(on_press=self.on_pressNC)


    def on_input(self, event):       ## when MAP URL entered
        pass               ### also init auth code entry
        if self.GPSPTR.exist == 0:   # in init auth mode, get 6 digit code
             self.GPSPTR.code = self.mURL.text
        print("URL:", self.mURL.text) 
        self.mURL.text = ""

    def on_input2(self, event):      ## when Callsign entered
        pass
        #print("CALL:", self.csign.text) 

    def on_input3(self, event):      ## when stuff entered into info field
        #print("INFO:", self.info.text) 
        if self.info.text != self.GPSPTR.xmess:
            if self.info.text[-1].lower() == "y":
                self.GPSPTR.Resume = 1
                #print("Yes - Resume session:"+self.info.text[-1].lower())
####  read saved url/callsign;  set the two fields; do auto confirm
                with open(self.GPSPTR.save_path2, 'r') as infile:  ## opens, read, closes
                    [self.GPSPTR.auth,self.mURLx, self.csignx] = json.load(infile) ## read
                self.mURL.text = self.mURLx
                self.csign.text = self.csignx
                self.confirm = 1
                mess = "URL_CSIGN:"+self.mURLx+":"+self.csignx+":"+str(self.confirm)
                osc.send_message(b'/ui_api', [mess.encode('utf8'),], '127.0.0.1', activityport)
            else:
                self.GPSPTR.Resume = 0
            self.info.text = ""    # clear entry

    def on_pressC(self, event):    ## Confirm
        #print("confirmpress:") 
        if self.mURL.text == "" or self.csign.text == "":
            self.info.text = "Must enter URL & Csign"
            return
        self.mURLx = self.mURL.text
        self.csignx = self.csign.text
        self.confirm = 1
####  save url and callsign to file for possible resume
#      save to file
        with open(self.GPSPTR.save_path2, 'w') as outfile:  ## opens, saves, closes
            json.dump([self.GPSPTR.auth,self.mURLx, self.csignx], outfile) ## save 
        self.GPSPTR.ActMapSet = 0                    # reset flag as map url may have changed
        mess = "URL_CSIGN:"+self.mURLx+":"+self.csignx+":"+str(self.confirm)
        osc.send_message(b'/ui_api', [mess.encode('utf8'),], '127.0.0.1', activityport)

    def on_pressS(self, event):
        #print("Spress:") 
        timex = int(time.time()*1000)  # time in millisec
        xfered = 0
        if self.confirm == 0:
            self.info.text = "Enter URL&Csign; Confirm"
            return
        self.info.text = "S pressed"
        self.GPSPTR.markers.append([self.GPSPTR.vals[0],self.GPSPTR.vals[1],'icon-U8S4VB1E-24-0.5-0.5-ff',timex,xfered])  ## S

    def on_pressE(self, event):
        #print("Epress:") 
        timex = int(time.time()*1000)  # time in millisec
        xfered = 0
        if self.confirm == 0:
            self.info.text = "Enter URL&Csign; Confirm"
            return
        self.info.text = "E pressed"
        self.GPSPTR.markers.append([self.GPSPTR.vals[0],self.GPSPTR.vals[1],'icon-4H3T1151-24-0.5-0.5-ff',timex,xfered])  ## E

    def on_pressNC(self, event):
        #print("NCpress:") 
        timex = int(time.time()*1000)  # time in millisec
        xfered = 0
        if self.confirm == 0:
            self.info.text = "Enter URL&Csign; Confirm"
            return
        self.info.text = "NC pressed"
        self.GPSPTR.markers.append([self.GPSPTR.vals[0],self.GPSPTR.vals[1],'icon-UMQ1GFHD-24-0.5-0.5-ff',timex,xfered])  ## NC

if __name__ == '__main__':
    main()
