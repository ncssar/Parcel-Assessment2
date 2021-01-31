
###
##  Stuff to do:
##     add try around sts requests in case they timeout
##     save markers, track, savetrack in a file for session restart (possibly have a save_markers instead of a xfer flag 
##     add check for 'confirm' and notice, if status button pushed when not confirmed
##
###

### need AppTrack and LEmarkers folders to exist on map
import platform
from kivy.app import App
from kivy.logger import Logger
from plyer import gps
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout      # not used
from kivy.uix.behaviors import ButtonBehavior   # not used
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton
from oscpy.server import OSCThreadServer
from sartopo_python import SartopoSession
import time
import os
import json
import certifi

serviceport = 3000
activityport = 3001
osc = OSCThreadServer()

##  see defines below in code
# ANDROID 
# SARTOPO 

symbol_dict = { 'icon-U8S4VB1E-24-0.5-0.5-ff': "(S)",  'icon-UMQ1GFHD-24-0.5-0.5-ff': "(NC)",
                'icon-4H3T1151-24-0.5-0.5-ff': "(E)"}
os.environ['SSL_CERT_FILE'] = certifi.where()

def main():

    app = GPSApp()
    print("At main in service routine")
    Logger.critical("TRACK service TOP")   
    app.run()

class GPSApp(App):
    def build(self):           ## called at start of program execution
        #

        plat = platform.architecture()
        print("ARCH:%s: SERVICE"%str(plat))
        if "Win" in plat[1]:
           self.ANDROID = 0       ###  running on ANDROID or PC ???
        else:
           self.ANDROID = 1

        osc.listen(address='127.0.0.1', port=activityport, default=True)  # listen UI port
        osc.bind(b'/ui_api', self.ui_callback)     
        ##A##osc.send_message(b'/tracker_api', ['Okay##############################'.encode('utf8'), ], '127.0.0.1', serviceport) 
        print("in SERVICE after message")
                                                                                                              
        self.mURLx = ''
        self.csignx = ''
        self.confirm = 0
        self.SARTOPO = 1  ## sets flag to include code to talk to sartopo
        #
        self.saveTrack = []   # place to store already sent pieces of the track
        self.sts = None
        self.link = -1
        self.kill = 0         # will be updated from UI
        self.foldAT = ""
        self.ID = None
        self.cnt = 0
        self.since = 0        # time of previous save to sartopo
        self.startTrack = 1
        self.getGPSloc = 1    # flag to save GPS loc to track on next tick 
        self.timerTick = 5
        self.TIMEOUT = 4       # sets update for server connection to TIMEOUT * timerTick
        self.timerCnt = self.TIMEOUT
        self.save_path = "LEservice_save.json"
### check for files to resume
        if os.path.isfile(self.save_path):                    # file exists
            mtime = int(os.path.getmtime(self.save_path))     # mod time in seconds 
            curTime = int(time.time())
            print("TIME:"+str(mtime)+":"+str(curTime))
            if (curTime - mtime) < 84600:    # within a day
               pass   #### if all of the above is Okay, look for message from UI to say 'resume'
               print("resume time check in service")
               
        self.accountName="ncssarnc@gmail.com"     ## obviscate  ## redact
###   add in self.accountName="<acct>"
        print("B4 sartopo")
        if self.SARTOPO == 1:
           print("AT REQUEST service")
           self.stsfile = "./sts.ini"   ## use more general path resolution
           ###self.stsfile = "/storage/emulated/0/kivy/sts.ini"   ## use more general path resolution
        print("B4 return")
        Logger.info("Called start service")
        print("at start in service")
        self.track = []      ## only intending to update the track in the service routine
        self.vals = [0, 1, 2, 3]    # just a holder when GPS not defined
        if self.ANDROID == 1:
            print("ANDROID gps configure in service")
            gps.configure(
                on_location=self.on_location
            )
            gps.start()
        print("Fart service")   ##  printed in log
        x = 0
        while (self.kill == 0):    ### stay a while
            time.sleep(1)
            if x > self.timerTick:
                self.on_timer(1)
                x = 0
            x += 1
            Logger.critical("In loop service")

    def ui_callback(self, message):
       dec_mess = message.decode('utf8').split(":")
       print("got a message from the userInterface:%s"% dec_mess)
       ##osc.send_message(b'/tracker_api', [self.mURLx.encode('utf8'), self.csignx.encode('utf8')], '127.0.0.1', serviceport)
       if dec_mess[0] == "URL_CSIGN":
           self.mURLx = dec_mess[1] 
           self.csignx = dec_mess[2] 
           self.confirm = int(dec_mess[3]) 
       elif dec_mess[0] == "END_TASK":
           self.kill = 1

    def on_location(self, **kwargs):  ## called at GPS input
        Logger.info("Called on_location SERVICE")
        self.vals = []
        for key, val in kwargs.items():
           self.vals.append(val)
        Logger.critical("TRACK:"+str(self.track))   
####  Could have a timer such that unless it has a tick, the point is dumped
####      Want to get the most recent when there is a Marker push
        if self.getGPSloc == 1:    # time to get another track point
                              #  note, markers are updated with higher resolution timing of the location
           self.track.append([self.vals[1],self.vals[0],0,int(time.time()*1000)])  #  add to LE track
           self.getGPSloc = 0      # reset 
        print("location in service")

    def on_timer(self, event):        ## called at timer tick
        Logger.critical("At timer service")  # str(self.track))   
        print("AT TIMER IN SERVICE"+str(event))
        self.getGPSloc = 1    # set flag to save gps location update to track
        self.timerCnt += 1
        if self.timerCnt < self.TIMEOUT:
           return       # wait to do the following
        self.timerCnt = 0        
### only get down here every timerTick * TIMEOUT seconds
#      save to file
        print("At message send in timer of service")
        ##A##osc.send_message(b'/tracker_api', ['OkayTimer##############################'.encode('utf8'), ], '127.0.0.1', serviceport) 
        time.sleep(0.5)   #  see if staying in this call helps with the above message sending
        with open(self.save_path, 'w') as outfile:  ## opens, saves, closes
            json.dump([self.track, self.saveTrack], outfile) ## save 

###### can do the following any time the mURLx changes value when SARTOPO and confirm == 1


        self.url="sartopo.com/m/"+self.mURLx     ## need to put after field filled-in`
        ##$ self.url="localhost:8080/m/K63"         ## need to put after field filled-in`
        parse=self.url.replace("http://","").replace("https://","").split("/")
        domainAndPort=parse[0]
        mapID=parse[-1]
        if self.SARTOPO == 1 and self.confirm == 1:    # mURL and csign need to be set
           if "sartopo" in domainAndPort:
              self.sts=SartopoSession(domainAndPort=domainAndPort,mapID=mapID,
                                         configpath=self.stsfile,
                                         account=self.accountName)
           else:
              self.sts=SartopoSession(domainAndPort=domainAndPort,mapID=mapID)
           self.link=self.sts.apiVersion      ## if returns -1 do not have connection; if so call above
                                              #    again and recheck
           Logger.info("API version server:"+' '+str(self.link))                  
        if self.link == -1:  
           Logger.info("No connection to server from SERVER")
           return       # no connection 
#####   got connection so put stuff on the map
        if self.foldAT == "":   # get folder id (only once)
           folders = self.sts.getFeatures("Folder")
           fndFolder = 0
           for folder in folders:
              print("FOLDER:%s"%folder)
              if folder["properties"]["title"] == "AppTrack":
                print("found folder at")
                self.foldAT = folder["id"]
                fndFolder = 1
           if fndFolder == 0:
              self.sts.addFolder(label="AppTrack")
        Logger.info("Server connected server")
        ## update the track
        #
        #   How about making the track from pieces of LineString each time there is connection to the server
        #
        if (len(self.track) < 6 and self.startTrack == 1) or len(self.track) < 2 :
            return             # wait for more points
        print("B4 track call service:"+str(self.startTrack))
        self.cnt = self.cnt + len(self.track)
        result = self.sts.addAppTrack(self.track,cnt=self.cnt,startTrack=1,title=self.csignx,description='', \
                     existingId=self.ID,folderId=self.foldAT)  # new, get id 
# do we want a parameter to the call to differentiate between normal tracks and AppTracks?
        print("AFT track call:"+str(result))
        if result != None and result != -1:         ## occurred Okay, result is ID
            if self.startTrack == 1:
                self.ID = result   # only get the result from the first call as later ID may be from another
                                   # feature that was processed in this group
                print("TRACK ID="+str(self.ID))
                self.startTrack = 0
            print("B4 savetrack append")
            self.saveTrack.append(self.track)  # save away
            print("AFT savetrack append")
            self.track = []    #  initialize to null to use caltopo incremental mode
            self.since = int(time.time()*1000)
        else:
            self.cnt = self.cnt - len(self.track)   # reset as did not xfer 
        ###  AppTrack entries get changed to Shape when the session is saved using caltopo app


if __name__ == '__main__':
    main()
