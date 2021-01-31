
#
#   THIS ROUTINE runs on a ncssar server and periodically connects incremental track pieces
#     having the same name. then deletes the incremental pieces (this part is not working
#     for databases at sartopo.com
#

###
##  Stuff to do for kivy app on phone:
##     add try around sts requests in case they timeout
##     save markers, track, savetrack in a file for session restart (possibly have a save_markers instead of a xfer flag 
##     add check for 'confirm' and notice, if status button pushed when not confirmed
##
###

### need LEmarkers folder to exist on map
import platform
from kivy.app import App
from kivy.logger import Logger
##from plyer import gps
##from kivy.uix.label import Label
##from kivy.uix.button import Button
##from kivy.uix.gridlayout import GridLayout      # not used
##from kivy.uix.behaviors import ButtonBehavior   # not used
##from kivy.uix.floatlayout import FloatLayout
##from kivy.uix.textinput import TextInput
##from kivy.uix.togglebutton import ToggleButton
##from oscpy.server import OSCThreadServer
from sartopo_python import SartopoSession
import time
import os
import json
import certifi
from operator import itemgetter

serviceport = 3000
activityport = 3001
##osc = OSCThreadServer()

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

        ##osc.listen(address='127.0.0.1', port=activityport, default=True)  # listen UI port
        ##osc.bind(b'/ui_api', self.ui_callback)     
        #G#A##osc.send_message(b'/tracker_api', ['Okay##############################'.encode('utf8'), ], '127.0.0.1', serviceport) 
        print("in SERVICE after message")
                                                                                                              
        self.mURLx = ''
        self.SARTOPO = 1  ## sets flag to include code to talk to sartopo
        #
        self.saveTrack = []   # place to store already sent pieces of the track
        self.sts = None
        self.link = -1
        self.foldAT = ""
        self.ActMapID = '1DE6'
        self.sortTrack = {}   # define as dictionary
        self.ID = None
        self.getGPSloc = 1    # flag to save GPS loc to track on next tick 
        self.timerTick = 30
##        self.save_path = "LEservice_save.json"
### check for files to resume
##        if os.path.isfile(self.save_path):                    # file exists
##            mtime = int(os.path.getmtime(self.save_path))     # mod time in seconds 
##            curTime = int(time.time())
##            print("TIME:"+str(mtime)+":"+str(curTime))
##            if (curTime - mtime) < 84600:    # within a day
##               pass   #### if all of the above is Okay, look for message from UI to say 'resume'
##               print("resume time check in service")
               
        self.accountName="ncssarnc@gmail.com"     ## obviscate  ## redact
###   add in self.accountName="<acct>"
        print("Enter the map URL")
##############  get URL input       mURLx    
        if self.SARTOPO == 1:
           print("AT REQUEST service")
           self.stsfile = "sts.ini"   ## use more general path resolution
           ##self.stsfile = "/storage/emulated/0/kivy/sts.ini"   ## use more general path resolution
        print("B4 return")
        Logger.info("Called start service")
        print("at start in service")
        self.track = []      ## only intending to update the track in the service routine
        self.vals = [0, 1, 2, 3]    # just a holder when GPS not defined
        x = 0
        while 1:    ### stay a while
            self.on_timer(1)
            Logger.critical("In loop service")
            time.sleep(20) ##  self.timerTick)



    def on_timer(self, event):        ## called at timer tick
      Logger.critical("At timer service")  # str(self.track))   
      print("AT TIMER IN SERVICE"+str(event))

###### can do the following any time the mURLx changes value when SARTOPO and confirm == 1

      self.mURLx =  "TEST"  ##"RV0D"
      self.url="sartopo.com/m/"+self.mURLx  # last "/" for change in parse split for ext
                 ## "/N166JPDK9NP44HST"     ## need to put after field filled-in`
      ##$ self.url="localhost:8080/m/K63"         ## need to put after field filled-in`
      parse=self.url.replace("http://","").replace("https://","").split("/")
      domainAndPort=parse[0]
      mapID=parse[-1]
  ###
  #
  #   loop thru markers in map 1DE6, set mapID and process
  #
  #
  ###
      if "sartopo.com" in domainAndPort:    ### look for Act Map pointers
              self.sts=SartopoSession(domainAndPort=domainAndPort,mapID=self.ActMapID,
                                         configpath=self.stsfile,
                                         account=self.accountName)
      else:
              self.sts=SartopoSession(domainAndPort=domainAndPort,mapID=self.ActMapID)
      self.link=self.sts.apiVersion      ## if returns -1 do not have connection; if so call above
                                              #    again and recheck
      Logger.info("API version:"+' '+str(self.link))
           
      if self.link == -1:  
           Logger.info("No connection to server from SERVER")
           return       # no connection 
      ## read marker folder
      folders = self.sts.getFeatures("Marker")
      print("At folders:%s"%str(json.dumps(folders,indent=2)))
      for folder in folders:
        print("FOLDER:%s"%folder)
        if folder["properties"]["class"] == "Marker":
                 print("found folder"+str(folder))
                 self.foldAT = folder["id"]
                 mapID = folder['properties']['title'] 
                 print('MAPID:'+mapID)
                 if mapID == "initialize":  ## this is marker used to create folder 
                     continue
        if 1 == 1:
           if "sartopo.com" in domainAndPort: 
              self.sts=SartopoSession(domainAndPort=domainAndPort,mapID=mapID,
                                         configpath=self.stsfile,
                                         account=self.accountName)
           else:
              self.sts=SartopoSession(domainAndPort=domainAndPort,mapID=mapID)
           self.link=self.sts.apiVersion      ## if returns -1 do not have connection; if so call above
                                              #    again and recheck
           Logger.info("API version:"+' '+str(self.link))
           
        if self.link == -1:  
           Logger.info("No connection to server from SERVER")
           return       # no connection 

#####   got connection so put stuff on the map

        if self.foldAT == "":   # get folder id (only once)
           folders = self.sts.getFeatures("Folder")
           print("At folders:%s"%str(json.dumps(folders,indent=2)))
           for folder in folders:
              print("FOLDER:%s"%folder)
              if folder["properties"]["title"] == "AppTrack":
                print("found folder"+str(folder))
                self.foldAT = folder["id"]
        Logger.info("Server connected")
        #
        #   How about making the track from pieces of LineString each time there is connection to the server
        #
        result = self.sts.getFeatures("Shape")  # get Shapes, then select some 
        ##print("Contents:"+json.dumps(result,indent=3))  ##xstr(json.loads(result)))
           ###  get tracks:
        if result != None and result != -1:         ## occurred Okay, result is ID
            print("B4 savetrack append")
            ##   select and group tracks
            for sel in result:    ## make dictionary of lists (of lists)
                if not "folderId" in sel["properties"]: continue     # skip, not in AppTrack
                if sel["properties"]["folderId"] != self.foldAT:   # only keep tracks in the AppTrack folder
                    continue
                trkName = sel['properties']['title']
                if trkName not in self.sortTrack:   # or dict.has_key(trkName)
                    self.sortTrack[trkName] = []
                self.sortTrack[trkName].append([sel['id'],sel['geometry']['coordinates']])    # add list to this dictionary leg
            ##   sort n time    
            print("sortTrack:"+json.dumps(self.sortTrack, indent=2))
            startTrack = 1
            for key, val in self.sortTrack.items():           # key is callsign
                print("KEY:"+key)
                sorted(val,key=lambda item: item[1][0][3])    # sort entries of each callsign by time
                #print("val:"+str(val))
            ##   combine pieces and reconstruct db entry, delete all other segments
                combo = []
                ids = []
                for sub in val:            #find each track(a callsign)
                    for itm in sub[1]:     #pickup the individual segments
                        combo.append(itm)    
                    ids.append(sub[0])        
            ## use first id for each callsign
      ##
      ####  present sartopo_python always creates a new shape id, so would want to
      ####    delete all of the previous pieces              
      ##              
                result = self.sts.addAppTrack(combo,cnt=len(combo),startTrack=1,title=key,description='', \
                                              existingId=ids[0],folderId=self.foldAT)  # new, get id
                print("RESULT:"+str(result))
            ##  then remove all other ids
                ####for idx in ids[1:]:
                for idx in ids[0:]:          ## for now remove all pieces in that a new combo shape is created
                
                    result = self.sts.delObject("shape",existingId=idx)
                ##result = self.sts.delObject("marker",existingId="56af676c-c227-4e73-a253-6089f000aefb")
                #result = self.sts.addIncTrack(1,[[-121.0,39.0,0,160000000000],],1,title='1D56',description='', \
                #        since=0,existingId="5f5b7715-4a3f-4a17-87f3-f25134a3ac87",folderId=self.foldAT)
                    print("RM ID:"+str(result))
        ###  AppTrack entries, from the caltopo app, get changed to the Shape folder when the session is saved


if __name__ == '__main__':
    main()
