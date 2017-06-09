import pandas as pd
import geopandas as gpd
import datetime
import numpy as np
from shapely.geometry import Point, LineString
import shapely.wkt
import os
import json


def snapToBikelane(bikelaneDF,bufersDF,pointsDF):
    '''
    this function takes:
    - a point data set (accelerometer or photos)
    - a bikelane buffer geopandas
    - a bikelane geopandas
    and returns a new geopandas with :
    the bikelane ID where the point belongs to  
    the bikeline in geometry
    the new point snap to line in geomtry 
    '''
    #change projection for points, bike shp already in 3857
    pointsDF = pointsDF.to_crs(epsg=3857)
    bufersDF = bufersDF.to_crs(epsg=3857)
    bikelaneDF = bikelaneDF.to_crs(epsg=3857)

    #give the line of the bikelane to the bufersDF
    bufersDF['line'] = bikelaneDF.geometry
    
    #joint points with buffer
    joinData = gpd.sjoin(pointsDF, bufersDF, how="left", op='intersects')
    
    #get unique pointID TIMES MAY CHANGE IN THE NAME WARNING
    allThePoints = pointsDF.point_id.unique()
    
    #create empty lists where we store new data
    line = []
    bikelanesID = []
    
    #get point ID duplicated
    duplicates = joinData.point_id[joinData.point_id.duplicated()].unique()

    
    for i in range(len(allThePoints)):
        #check if the pointIndex is unique:
        if allThePoints[i] not in duplicates:
            #append line from joint to that index
            line.append(joinData.line.loc[joinData.point_id == allThePoints[i]].iloc[0])
            bikelanesID.append(joinData.ID_ORIGINA.loc[joinData.point_id == allThePoints[i]].iloc[0])

        else:
            #if not, append from the previous id
            line.append(joinData.line.loc[joinData.point_id == allThePoints[i-1]].iloc[0])
            bikelanesID.append(joinData.ID_ORIGINA.loc[joinData.point_id == allThePoints[i-1]].iloc[0])
    
    pointsDF['line'] = line
    pointsDF['bikelane_id'] = bikelanesID
    
    
    pointOnLine = []

    for i in range(pointsDF.shape[0]):
        try:
            newPoint = pointsDF.line.iloc[i].interpolate(pointsDF.line.iloc[i].project(pointsDF.geometry.iloc[i]))

        except AttributeError:
            newPoint = np.nan

        pointOnLine.append(newPoint)

    pointsDF['pointOnLine'] = pointOnLine   
    
    
    pointsDF = pointsDF.to_crs(epsg=3857)
    
    

    return pointsDF

def queryOSCapi(OSCid,X = True, Y = True, Z = True, output = 'csv', outputFile = 'data.csv', dataType = 'accelerometer'):
    '''
    This functions takes an ID from OSC
    the type of data to download: accelerometer or photos
    returns :
    - a dataframe with the V values for each gps coordinate point
    or
    - a dataframe with pictures names, gps coordinates and picture quality placeholder 
    '''
    
    #query the OSC API for the ID
    data = getOSCjson(OSCid=OSCid)
    
    
    try:
        data = data['osv']
        if dataType == 'accelerometer':
            
            #get the url for the file with accelerometer data
            url='http://openstreetcam.org/'+data['meta_data_filename']
            
            #read the accelerometer data with loadOSCdata function
            outputReturn = readAccelerometer(url, X = X, Y = Y, Z = Z, output = output, outputFile = outputFile)
            outputReturn['tripID'] = OSCid

        else:
            totalPhotos = len(data['photos'])


            pictureName = [data['photos'][i]['name'] for i in range(totalPhotos)]
            quality = np.repeat(np.nan,totalPhotos)
            latitude = [data['photos'][i]['lat'] for i in range(totalPhotos)]
            longitude = [data['photos'][i]['lng'] for i in range(totalPhotos)]
            timestamp = [data['photos'][i]['date_added'] for i in range(totalPhotos)]


            outputReturn = pd.DataFrame({'pictureName':pictureName,
                                                 'quality':quality,
                                                 'latitude':latitude,
                                                 'longitude':longitude,
                                        'timestamp':timestamp})
            
            outputReturn['pointID'] = outputReturn.index

            if not(os.path.exists("../data")):
                os.system('mkdir data')

            if not(os.path.exists('../data/' + str(OSCid))):
                os.system('mkdir ../data/' + str(OSCid))

            #download data
            for i in range(outputReturn.shape[0]):
                photoURL = outputReturn.pictureName[i][9:]
                oscURL = 'http://'+outputReturn.pictureName[0][0:8]+'.openstreetcam.org/'
                os.system('wget '+ oscURL + photoURL + ' -P ' + '../data/' + str(OSCid))
        
        #outputReturn['tripID'] = OSCid        
        
        return outputReturn
    
    except KeyError, e:
        print 'Got a KeyError - reason "%s"' % str(e)
        output = 'Got a KeyError - reason "%s"' % str(e)
        return output


def getOSCjson(OSCid):
    '''
    This function takes a OSC track id and 
    returns a json file load in a Python dict 
    '''
    
    query = "curl 'http://openstreetcam.org/details' -H 'Referer: http://openstreetcam.org/details/" + str(OSCid) + "/0' -H 'X-Requested-With: XMLHttpRequest' -H 'Connection: keep-alive' --data 'id=" + str(OSCid) + "&platform=web' --compressed >> osc.json"
    os.system(query)

    #read json file
    with open('osc.json') as data_file:    
        data = json.load(data_file)

    os.system('rm osc.json')    
    
    return data


def readAccelerometer(textfile, X = True, Y = True, Z = True, output = 'csv', outputFile = 'data.csv'):
    '''
    This function takes a text file from OSC in the phone
    The axis we want to consider to compute the final vector (X, Y, Z)
    And the output formats and file
    and returns a dataframe with the V values for each gps coordinate point
    '''
    #read original data from file within track.txt.gz used by OSC to store sensor data
    data = pd.read_csv(textfile,sep=';',
                   skiprows=[0],
                   skipfooter=1,
                   usecols=[0,1,2,3,4,5,9,10,11,16,17,18],
                   header=None,
                   engine = 'python')

    #naming of columns 
    data.columns = ['timestamp','long','lat','elevation','horizontal_accu',
         'GPSspeed','accelerationX','accelerationY','accelerationZ',
         'gravityX','gravityY','gravityZ'] 
    
    #conversion into timestamp
    #dates = []
    #for i in range(data.shape[0]):
    #    try:
    #        dates.append(datetime.datetime.fromtimestamp(data['timestamp'].iloc[i]))
    #    except :
    #        print 'Error with row:', i
    #data['timestamp'] = dates        
    
    #remove all empty rows except timestamp
    emtpy = data.iloc[:,1:].isnull().sum(axis=1) == data.shape[1]-1
    data = data.loc[~emtpy,:]
    data.index=range(data.shape[0])
    
    data = data.loc[:,['timestamp','long','lat','accelerationX','accelerationY','accelerationZ']]
    data.dropna(axis=0,how='all',subset = ['long','lat','accelerationX','accelerationY','accelerationZ'],inplace=True)
    
    #create the geography
    gpsDataPoints =  data.loc[~ (data['long'].isnull()),['timestamp','long','lat']]
    gpsDataPoints['pointIndex'] = gpsDataPoints.index
    
    geometry = []
    for i in range(len(gpsDataPoints.index)):
        if i == (len(gpsDataPoints.index)-1):
            line = np.nan
        else:
            #get start and end points for each line
            startPoint = Point(gpsDataPoints['long'].loc[gpsDataPoints.index[i]], gpsDataPoints['lat'].loc[gpsDataPoints.index[i]])
            endPoint = Point(gpsDataPoints['long'].loc[gpsDataPoints.index[i+1]], gpsDataPoints['lat'].loc[gpsDataPoints.index[i+1]])
            #convert to shapely wkt
            line = LineString([startPoint,endPoint]).wkt
            geometry.append(shapely.wkt.loads(line).centroid)
    
    gpsDataPoints = gpsDataPoints.iloc[:-1]
    crs = {'init': 'epsg:4326'}
    gpsDataPoints = gpd.GeoDataFrame(gpsDataPoints, crs=crs, geometry=geometry)
    
    #Asign to data the index of the points with GPS data
    data.drop(['timestamp'],axis=1,inplace=True)
    data = data.merge(gpsDataPoints.drop(['timestamp','geometry'],axis=1),how='left')
    data['pointIndex'] = data['pointIndex'].fillna(method='ffill')
    
    #shift data lag 1 to take the vector of the difference in axis XYZ
    dataShifted = data.shift(1)
    dataShifted.drop(['long','lat','pointIndex'],axis=1,inplace=True)
    dataShifted.columns = ['accelerationXShift','accelerationYShift','accelerationZShift']
    
    #concatenate datasets
    data = pd.concat([data,dataShifted],axis=1)
    data.drop(['long','lat'],axis=1,inplace=True)
    data.dropna(axis=0,how='any',inplace=True)
    
    #compute vector
    
    data['V'] = np.sqrt((data.accelerationX-data.accelerationXShift) ** 2 * X + \
    (data.accelerationY-data.accelerationYShift) ** 2 * Y + \
    (data.accelerationZ-data.accelerationZShift) ** 2 * Z) 
    
    #get the sum of every lag BY line defined by the starting point (with GPS data)
    vectorInformation = data.loc[:,['pointIndex','V']].groupby(by=['pointIndex']).sum()
    vectorInformation.reset_index(inplace=True)
    gpsDataPoints = gpsDataPoints.merge(vectorInformation)
    
    #gpsDataPoints.timestamp = gpsDataPoints.timestamp.map(lambda x: str(x))
    
    if output == 'csv':
        gpsDataPoints.to_csv(outputFile)
    elif output == 'shp':
        gpsDataPoints.to_file(outputFile)
    else:
        raise NameError('You can only export to csv or shp files')
    
    return gpsDataPoints


def downloadData(OSCid, X = True, Y = True, Z = True, output = 'csv', outputFile = 'data.csv'):
    '''
    This function takes a text file from OSC in the phone
    The axis we want to consider to compute the final vector (X, Y, Z)
    And the output formats and file
    and returns a dataframe with the V values for each gps coordinate point
    '''
    
    
    apiOutput = getOSCjson(OSCid)
    apiOutput = apiOutput['osv']
    textfile='http://openstreetcam.org/'+apiOutput['meta_data_filename']

    #read original data from file within track.txt.gz used by OSC to store sensor data
    data = pd.read_csv(textfile,sep=';',
                   skiprows=[0],
                   skipfooter=1,
                   usecols=[0,1,2,9,10,11,15],
                   header=None,
                   engine = 'python')

    #naming of columns 
    data.columns = ['timestamp','long','lat','accelerationX','accelerationY','accelerationZ','point_id'] 
    
    
    #remove all empty rows except timestamp
    emtpy = data.iloc[:,1:].isnull().sum(axis=1) == data.shape[1]-1
    data = data.loc[~emtpy,:]
    data.index=range(data.shape[0])
    

    data.dropna(axis=0,how='all',
                subset = ['long','lat','accelerationX','accelerationY','accelerationZ','point_id'],
                inplace=True)
    
    
    #CREATE A PHOTOS DATAFRAME
    dataPhotos = data.loc[~data.point_id.isnull(),['timestamp','point_id']]
    data.drop(['point_id'],axis=1,inplace=True)
    

    #Create accelerometer dataframe
    #create the geography
    gpsDataPoints =  data.loc[~ (data['long'].isnull()),['timestamp','long','lat']]
    gpsDataPoints['pointIndex'] = gpsDataPoints.index
    
    geometry = []
    for i in range(len(gpsDataPoints.index)):
        if i == (len(gpsDataPoints.index)-1):
            line = np.nan
        else:
            #get start and end points for each line
            startPoint = Point(gpsDataPoints['long'].loc[gpsDataPoints.index[i]], gpsDataPoints['lat'].loc[gpsDataPoints.index[i]])
            endPoint = Point(gpsDataPoints['long'].loc[gpsDataPoints.index[i+1]], gpsDataPoints['lat'].loc[gpsDataPoints.index[i+1]])
            #convert to shapely wkt
            line = LineString([startPoint,endPoint]).wkt
            geometry.append(shapely.wkt.loads(line).centroid)
    
    gpsDataPoints = gpsDataPoints.iloc[:-1]
    crs = {'init': 'epsg:4326'}
    gpsDataPoints = gpd.GeoDataFrame(gpsDataPoints, crs=crs, geometry=geometry)
    
    #Asign to data the index of the points with GPS data
    data.drop(['timestamp'],axis=1,inplace=True)
    data = data.merge(gpsDataPoints.drop(['timestamp','geometry'],axis=1),how='left')
    data['pointIndex'] = data['pointIndex'].fillna(method='ffill')
    
    #shift data lag 1 to take the vector of the difference in axis XYZ
    dataShifted = data.shift(1)
    dataShifted.drop(['long','lat','pointIndex'],axis=1,inplace=True)
    dataShifted.columns = ['accelerationXShift','accelerationYShift','accelerationZShift']
    
    #concatenate datasets
    data = pd.concat([data,dataShifted],axis=1)
    data.drop(['long','lat'],axis=1,inplace=True)
    data.dropna(axis=0,how='any',inplace=True)
    
    #compute vector
    
    data['V'] = np.sqrt((data.accelerationX-data.accelerationXShift) ** 2 * X + \
    (data.accelerationY-data.accelerationYShift) ** 2 * Y + \
    (data.accelerationZ-data.accelerationZShift) ** 2 * Z) 
    
    #get the sum of every lag BY line defined by the starting point (with GPS data)
    vectorInformation = data.loc[:,['pointIndex','V']].groupby(by=['pointIndex']).sum()
    vectorInformation.reset_index(inplace=True)
    gpsDataPoints = gpsDataPoints.merge(vectorInformation)
    
    
    #Create photos dataframe
    photoPoints = []
    photoV = []
    pictureUrl = []
    cvLabels = []
    dates = []
    
    #for each photo, search accelerometer points data, and:
        ## compute the mean of the final accelerometer V vector for all the points between that photo and the next
        ## get the coordinate of the first point
        
    for i in range(dataPhotos.shape[0]):
        if i == (dataPhotos.shape[0]-1):
                dataAggregated = gpsDataPoints.loc[(gpsDataPoints.timestamp > dataPhotos.timestamp.iloc[i]),:]
        else:
            dataAggregated = gpsDataPoints.loc[(gpsDataPoints.timestamp > dataPhotos.timestamp.iloc[i]) & (gpsDataPoints.timestamp < dataPhotos.timestamp.iloc[i+1]),:]
        #get V and GPS data        
        photoV.append(dataAggregated.V.mean())
        photoPoints.append(dataAggregated.geometry.iloc[0])
        
        #conversion into timestamp
    
        dates.append(datetime.datetime.fromtimestamp(dataPhotos['timestamp'].iloc[i]))
        
        #get photo url and label
        pictureName = apiOutput['photos'][i]['name']
        
        oscURL = 'http://'+pictureName[0:8]+'.openstreetcam.org/'+pictureName[9:]
        
        pictureUrl.append(oscURL)
        cvLabel = queryCV(oscURL)
        
        cvLabels.append(cvLabel)     

    dataPhotos['v_value'] = photoV
    dataPhotos['geometry'] = photoPoints
    dataPhotos['image_url'] = pictureUrl
    dataPhotos['image_lab'] = cvLabels
    dataPhotos['timestamp'] = dates
    dataPhotos['trip_id'] = OSCid
    
    crs = {'init': 'epsg:4326'}

    dataPhotos = gpd.GeoDataFrame(dataPhotos, crs=crs, geometry = dataPhotos.geometry)
    #get photo url for each photo
    

    
    if output == 'csv':
        dataPhotos.to_csv(outputFile)
    elif output == 'shp':
        dataPhotos.to_file(outputFile)
    else:
        raise NameError('You can only export to csv or shp files')
    
    #return (gpsDataPoints,dataPhotos)
    return dataPhotos


def queryCV(pictureURL):
    query = '''curl 'https://southcentralus.api.cognitive.microsoft.com/customvision/v1.0/Prediction/16d2699a-3afd-4548-a7d3-2263abf5be63/url?iterationId=d6c29a8a-8001-49eb-b497-9f8b7109dfe7&application=quicktest' -H 'Origin: https://customvision.ai' -H 'Accept-Encoding: gzip, deflate, br' -H 'Accept-Language: en-US,en;q=0.8,es;q=0.6' -H 'Prediction-Key: '''+os.getenv('CVPREDICTIONKEY')+''' ' -H 'Content-Type: application/json;charset=UTF-8' -H 'Training-Key: '''+os.getenv('CVTRAININGKEY')+''' ' -H 'Accept: application/json, text/plain, */*' -H 'Referer: https://customvision.ai/projects/16d2699a-3afd-4548-a7d3-2263abf5be63' -H 'Connection: keep-alive' -H 'DNT: 1' --data-binary '{"Url":"'''+pictureURL+'''"}' --compressed >> photoLabel.json'''
    os.system(query)    
    with open('photoLabel.json') as data_file:    
        #print data_file
        data = json.load(data_file)
    os.system('rm photoLabel.json')
    
    highest = 0
    label = ''
    try:
        for i in range(len(data['Predictions'])):
            prob = data['Predictions'][i]['Probability']
            if  prob > highest:
                highest = prob
                label = data['Predictions'][i]['Tag']
            else:
                pass
    except KeyError:
        label = 'Error'
    
    return label