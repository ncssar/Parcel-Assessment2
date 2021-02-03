
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
from shapely.geometry import Polygon
from shapely.geometry import Point
from shapely.geometry import LineString
from shapely.strtree import STRtree
from timezonefinder import TimezoneFinder
from datetime import datetime, timezone
import pytz
from shapely.ops import nearest_points
from shapely.geometry import shape
from shapely.geometry import mapping

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
    #print("At main in service routine")
    #Logger.critical("TRACK service TOP")   
    app.run()

class GPSApp(App):
    def build(self):           ## called at start of program execution
        #

        plat = platform.architecture()
        #print("ARCH:%s: SERVICE"%str(plat))
        if "Win" in plat[1]:
           self.ANDROID = 0       ###  running on ANDROID or PC ???
        else:
           self.ANDROID = 1

        ##osc.listen(address='127.0.0.1', port=activityport, default=True)  # listen UI port
        ##osc.bind(b'/ui_api', self.ui_callback)     
        #G#A##osc.send_message(b'/tracker_api', ['Okay##############################'.encode('utf8'), ], '127.0.0.1', serviceport) 
        #print("in SERVICE after message")
                                                                                                              
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
        self.mrkInfo = []                # populate with marker location, type, callsign, time
        self.mrkr = []                   # list for Shapely Point creation
        self.LES = []
        self.LESinfo = []
        self.loopGo = False
## location of marker
        self.mrktype = 'NC'                          # temporary - from markers found on the map
        self.mrkX = Point([-121.064745, 39.143876])  # temporary - from markers found on the map
        print("mrkX:",self.mrkX)
     #self.timem = 'date/time'                    # temporary - from real marker info found on map (was in indx)
        self.callsign = '1D23'                       # temporary - from callsign of closest LE found on the map
        fpdat = open('parcel_markers.txt','w')
        
##        self.save_path = "LEservice_save.json"
### check for files to resume
##        if os.path.isfile(self.save_path):                    # file exists
##            mtime = int(os.path.getmtime(self.save_path))     # mod time in seconds 
##            curTime = int(time.time())
##            #print("TIME:"+str(mtime)+":"+str(curTime))
##            if (curTime - mtime) < 84600:    # within a day
##               pass   #### if all of the above is Okay, look for message from UI to say 'resume'
##               #print("resume time check in service")
               
        self.accountName="ncssarnc@gmail.com"     ## obviscate  ## redact
###   add in self.accountName="<acct>"
        #print("Enter the map URL")
##############  get URL input       mURLx    
        if self.SARTOPO == 1:
           #print("AT REQUEST service")
           self.stsfile = "sts.ini"   ## use more general path resolution
           ##self.stsfile = "/storage/emulated/0/kivy/sts.ini"   ## use more general path resolution
        #print("B4 return")
        #Logger.info("Called start service")
        #print("at start in service")
        self.track = []      ## only intending to update the track in the service routine
        self.vals = [0, 1, 2, 3]    # just a holder when GPS not defined
        x = 0

####     
## run once, at beginning
####
     
        data = self.loadNCparcels()                    # load Nevada County parcels
        self.treeX, self.indx, stuff = self.createTree(data)   # create a shapely STRtree to search for parcels



        while 1:    ### stay a while
            self.on_timer(1)
            #Logger.critical("In loop service")
            time.sleep(20) ##  self.timerTick)



    def on_timer(self, event):        ## called at timer tick
      pass  
      #Logger.critical("At timer service")  # str(self.track))   
      #print("AT TIMER IN SERVICE"+str(event))

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
      #Logger.info("API version:"+' '+str(self.link))
           
      if self.link == -1:  
           #Logger.info("No connection to server from SERVER")
           return       # no connection 
## cycle thru markers in Act Maps db in the folder
      folders = self.sts.getFeatures("Marker")
      #print("At folders:%s"%str(json.dumps(folders,indent=2)))
      for folder in folders:
        self.foldAT = ""  
        #print("FOLDER:%s"%folder)
        if folder["properties"]["class"] == "Marker":
                 #print("found folder"+str(folder))
                 #self.foldAT = folder["id"]
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
           #Logger.info("API versionE:"+' '+str(self.link))
           
        if self.link == -1:  
           #Logger.info("No connection to server from SERVER")
           return       # no connection 

#####   got connection so put stuff on the map

        if self.foldAT == "":   # get folder id (only once)
           folders = self.sts.getFeatures("Folder")
           #print("At folders:%s"%str(json.dumps(folders,indent=2)))
           for folder in folders:
              #print("FOLDER:%s"%folder)
              if folder["properties"]["title"] == "AppTrack":
                #print("found folder"+str(folder))
                self.foldAT = folder["id"]
        Logger.info("Server connected")
        #
        #   How about making the track from pieces of LineString each time there is connection to the server
        #
        result = self.sts.getFeatures("Shape")  # get Shapes, then select some
        ##print("ASDF:"+str(result)+"   "+str(len(result)))
        #W#print("Contents:"+json.dumps(result,indent=3))  ##xstr(json.loads(result)))
           ###  get tracks:
        if result != None and result != -1:         ## occurred Okay, result is ID
            #print("B4 savetrack append")
            self.sortTrack = {}                     # initialize for each map
            ##   select and group tracks
            for sel in result:    ## make dictionary of lists (of lists)
                if not "folderId" in sel["properties"]: continue     # skip, not in AppTrack
                if sel["properties"]["folderId"] != self.foldAT:   # only keep tracks in the AppTrack folder
                    continue
                trkName = sel['properties']['title']
                if trkName not in self.sortTrack:   # or dict.has_key(trkName)
                    self.sortTrack[trkName] = []
                self.sortTrack[trkName].append([sel['id'],sel['geometry']['coordinates']])    # add list to this dictionary leg
            ##   sort by time    
            #print("sortTrack:"+json.dumps(self.sortTrack, indent=2))
            if self.sortTrack != {}:      
              startTrack = 1
              for key, val in self.sortTrack.items():           # key is callsign
                print("Process KEY:"+key+" / num sections:"+str(len(val)))
                if len(val) < 2: continue  #  skip if only 1 section
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
                #print("RESULT:"+str(result))
            ##  then remove all other ids
                ####for idx in ids[1:]:
                for idx in ids[0:]:          ## for now remove all pieces in that a new combo shape is created
                
                    result = self.sts.delObject("shape",existingId=idx)
                ##result = self.sts.delObject("marker",existingId="56af676c-c227-4e73-a253-6089f000aefb")
                #result = self.sts.addIncTrack(1,[[-121.0,39.0,0,160000000000],],1,title='1D56',description='', \
                #        since=0,existingId="5f5b7715-4a3f-4a17-87f3-f25134a3ac87",folderId=self.foldAT)
                    #print("RM ID:"+str(result))
        ###  AppTrack entries, from the caltopo app, get changed to the Shape folder when the session is saved

####
## run on timer - loop
####
        print("Starting Marker updates")
#        self.loopGo  = True        # start loop
#        while (self.loopGo):       # wait for timer   DO NOT NEED AS OUTER LOOP HAS TIMER
#          self.loopGo = False
        if (1):    # for indent
          self.readLEMarker()      # get LE Markers (repeatedly call for updates)
                 # probably use sartopo_python to access sartopo.com
                 
                 ## run for each Marker found
                 # store marker info so as to process each once
##
####  for each marker find parcel - loop
##
          icnt = -1          
          for mptr in range(len(self.mrkr)):
            icnt = icnt + 1 
            result = self.findLocalParcels(self.treeX, mptr)       # find set of parcels close to Marker (faster)
            parMrk, resFnd = self.findParcel(result, mptr)    # find the parcel containing the marker
                 #  if none found, possibly locate the closest and use it
            self.mrkInfo[icnt][2] = self.indx[id(resFnd)][1]  # set the ADDRESS              
        
            idx = self.mrkInfo[icnt][5]
            titl = self.mrkInfo[icnt][6]     ## is the callsign
            desc = self.mrkInfo[icnt][2]+'/'+str(self.mrkInfo[icnt][3])[0:19]  #address and date
            lat = self.mrkInfo[icnt][0][0][1]
            long = self.mrkInfo[icnt][0][0][0]
            msym = self.mrkInfo[icnt][1]
                   #   fill in description:  address/ time
            print("ID:", idx,titl,'[',desc,']',msym,lat,long)
                   # add arguments:  lat, long, (title, description, color, symbol, rotation, folderId, existingId) 
                   ### might want to add: updated
                   ### doing update
            self.sts.addMarker(lat,long,title=titl,description=desc,symbol=msym,existingId=idx, \
                            folderId=self.idLEmark)   #replace marker in orig folder


    def loadNCparcels(self):
   ##  load Nevada County parcel data
      with open("c:\\users\\steve\\downloads\\parcel_situs_address.geojson") as fi:  # get all NC parcels
        data = json.load(fi)
      print('Length of data:',len(data))
      return(data)
     
    def readLEMarker(self):
   ## load tracks, specifically AppTrack for LE paths
   ## Use Timer to recheck AppTrack every so often from map at sartopo.com
   
 #$    with open("c:\\users\\steve\\downloads\\Map_Items.json") as fi2:  # get all NC parcels
 #$      tracks = geojson.load(fi2)

      items = self.sts.getFeatures(None)
      timestamp = items['result']['timestamp']    # time when data is collected
      print('Length of items:',len(items),"\n",items,timestamp)

      for ix in items['result']['state']['features']:  #get id of LEmarkers folder
        if ix['properties']['title'] == "LEmarkers":
          self.idLEmark = ix['id']

   #
####
   #####  probably do not want to create LES stuff here
     #LES = []         
     #LESinfo = []
      for ix in items['result']['state']['features']:
        if 'geometry' not in ix.keys() or 'folderId' not in ix['properties'].keys():
          continue
        # title is the callsign, class s/b Marker geometry-type is type of Point
        # geometry-coordinates are long,lat(deg-decimal),elev(m),time(epoch-gmt)msec
        
        
         ##### only process Points as these are markers            ## point
        if ix['geometry']['type'] == 'Point' and ix['properties']['class'] == 'Marker' and \
            ix['properties']['folderId'] == self.idLEmark:
          coordxy = [ix['geometry']['coordinates']]     # from app, this includes long, lat, elev (m), epoch
          print("#3", coordxy)
            
          timesx = ix['properties']['updated']        # epoch at gmt/UTC
          if timesx == 0:                             # if updated is not filled-in
            timesx = timestamp
          latx = coordxy[0][1]                        # use any coord long/lat
          longx = coordxy[0][0]
          print("timesx",timesx,"##",latx,"##",longx,"##")
          tf = TimezoneFinder()                       # get timezone name
          tza = tf.timezone_at(lng=longx,lat=latx)
          utc_dt = datetime.fromtimestamp(timesx/1e3) # convert epoch (msec) str to datetime format (sec)
          tz = pytz.timezone(tza)                     # convert tz name to utc offset
          dt = utc_dt.astimezone(tz)                  # convert time utc to this timezone
          print('timestamp:',timesx,';',tza,';',dt)
          makeCoord = []
          for xx in coordxy:                          # extract coord to make LineString for Shapely
             makeCoord.append([xx[0], xx[1]]) 
          print("COORDS:",makeCoord)
##
#### only add if did not exist, OR update
##
         #### find markers, store; check, add new to list
         #       use existance of description as flag that marker already processed
         
          ifnd = 0
          for li in self.mrkInfo:        # search for pre-existance
            if li[4] == "":             # description is blank prior to processing
               ifnd = 1
               print('Marker exists',ix['properties'])
               break
          if ifnd == 0:     
            self.mrkr.append(Point(makeCoord[0]))     ###  create version for Shapely
            idx = ix['id']
            titl = ix['properties']['title']                
            self.mrkInfo.append([coordxy, ix['properties']['marker-symbol'],
                                 "addr_holder", dt, "holder_for_callsign",idx,titl])
                                                     ## need symbol & assoc'd callsign - how to get??
            print("Marker:",self.mrkInfo,":",[list(self.mrkr[i].coords) for i in range(len(self.mrkr))])
              
        
    def createTree(self,data):
      stuff = []
      addr = []
      for dat in data['features']:  ##  read all parcels in County, add to STRtree
           
   ###
   #  there are some entries with multiple polygons called Polygon
   #  there are some with multiple called MultiPolygon, these have an additional encloser of []
   ###
       #print("##########  LEN is:  ",len(dat['geometry']['coordinates']))
        addr.append(dat['properties']['ADDRESS'])
        if dat['geometry']['type'] == "MultiPolygon" : 
           #print("\n    TYPE:",dat['geometry']['type'])
           # LinearRing
           stuff.append(Polygon(dat['geometry']['coordinates'][0][0]))   # only p/u first polygon
        else:
           #print("\n    TYPE2:",dat['geometry']['type'])
           stuff.append(Polygon(dat['geometry']['coordinates'][0]))
   
      self.treeX=STRtree(stuff)  # add parcels into STRtree
   ## create corresponding dictionary of parcel id's, address', marker-placed,
   ##  time and callsign of LE
      indx=dict((id(pt),[i, addr[i], self.mrktype, self.callsign]) for i, pt in enumerate(stuff))
      return(self.treeX, indx, stuff)
   
    def findLocalParcels(self, treeX, mptr):
       mark = self.mrkr[mptr]
       ## find properties around marker to reduce search by using a buffer
       result = treeX.query(mark.buffer(0.001))
       ##print("RESULT:",*result)
       return(result)
   
    def findParcel(self,result, mptr):   ## that has Marker contained within
   #    parcel (in result) that mrkX is contained within
      mark = self.mrkr[mptr]
      parMrk = False
      resFnd = 0
      for res in result:
        parMrk = res.contains(mark)   # parMrk is true for mrkX in parcel
       ##print("Looking for parcel match",mark,":",parMrk,":",self.mrkr[mptr])
        resFnd = res                  # resFnd is the parcel record of the parcel with the Marker
        if parMrk == True: break
      if parMrk:  
        print("PARCEL MARKER:",parMrk, resFnd, "\nID=", id(resFnd))
        print("    Addr is ",self.indx[id(resFnd)][1])
      else:
        print("ERROR: Marker not in any parcel")      
      return(parMrk, resFnd)    # parMrk is true if result is found



if __name__ == '__main__':
    main()
