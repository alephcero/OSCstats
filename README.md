# OSCstats
Project to read cellphone sensors using OSC and get stats to measure how *fluid* is the bike-lane. Sudden braking to avoid a pothole or any other interruption in the bike-lane, a swiftly turn in the handle (where the sensor was located) to avoid potholes or other obstacles will affect X and Y axis. Finally, passing through an actual pothole will be measured in the Z axis.

## Original data
The data from OSC is stored in a txt file in:

*local/android/data/com.telenav.streetvie.../files/OSV*

## Reading the data

The function *loadOSCdata()* will load data from that file and returns a GeoPandas DataFrame or CSV. 

The function *queryOSCapi()* will load data from the API given an tripID from OSC and returns a GeoPandas DataFrame or CSV

`loadOSCdata.queryOSCapi(OSCid = 219598,X = True, Y = True, Z = True, output = 'csv', outputFile = 'data.csv')`

## Output

The final output is a polyline with the resulting vector of the 3 axis (X,Y,Z) from the accelerometer as an attribute.

We calculated the final vector following [this guide](http://www.starlino.com/imu_guide.html)

![Final output in QGIS](img/firstTest.png)

## Columns data:
[Source](https://github.com/openstreetcam/openstreetview.org/issues/109)
* timestamp
* lon
* lat
* elevation 
* horizontal_accu
* GPSspeed
* yaw
* pitch
* roll
* accelerationX
* accelerationY
* accelerationZ
* pressure
* compas
* vIndex
* tFIndex
* gravityX
* gravityY
* gravityZ
* OBD2Speed
* vertical_accu


