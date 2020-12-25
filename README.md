# Parcel-Assessment2
Android tool to capture the tracks and marker placements used to assess evacuations 

Presently there are a number of key clicks necessary to record the assessment of a
parcel as to occupancy and structural integrity when utilizing the caltopo mobile app. 
The intent of this project is to:

Simplify the naming of the tracks (AppTrack) of the person evaluating the parcels
Simplify the recording of the the status of each parcel (occupancy or structural integrity)
Create an interface with the caltopo app to utilize its location and map connectivity 
capabilites (update: Due to restrictions of interfacing with caltopo, this project creates 
and uploads all data to the desired map)
Usage:

Start the app
Specify the map to connect by providing the URL
Enter the name/callsign of the user
Set the category of the information to be applied 
(occupancy or structural), May add other groups
At each parcel click on the appropriate selection 
button (for example: S - staying in place; E - evacuated; 
NC - no contact)
App Generation: The project is kivy/android based. 
The apk is created using buildozer on WSL and deployed and 
debugged using Android studio on windows. It consists of a 
foreground UI and background service routine.

Status: 11/17/2020: Various parts of the project are functional 
        (UI, map access, GPS location). But they are not integrated together.
        12/24/2020: Broke the app into two pieces. A UI for user 
        interaction including placement of markers and a service routine 
        that runs in the background that continuously creates the
        track, periodically sending the coordinates to the server.
