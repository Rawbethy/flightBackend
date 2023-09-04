import pandas as pd
import pickle

airports = pd.read_csv('./airlines.txt', sep=':', names=['ICAO', 'IATA', 'airportName', 'City', 'Country', 'latDeg', 'latMin', 'latSec', 'latDir', 'lonDeg', 'lonMin', 'lonSec', 'lonDir', 'altitude', 'latDec', 'lonDec'])
airportsFiltered = airports[['IATA', 'airportName', 'City']]
notIncluded = 'nan'
indices = []
for i in range(airportsFiltered.shape[0]):
    if str(airportsFiltered['IATA'][i]) != notIncluded and str(airportsFiltered['airportName'][i]) != notIncluded:
        indices.append(i)
newAirports = airportsFiltered.loc[indices].reset_index().drop('index', axis=1)

portDict = {}
for i in range(len(newAirports)):
    city = newAirports['City'][i]
    code = newAirports['IATA'][i]
    portName = newAirports['airportName'][i]
    if city not in portDict:
        portDict[city] = [[code, portName]]
    else:
        portDict[city].append([code, portName])

with open('airportDict.pk1', 'wb') as fp:
    pickle.dump(portDict, fp)

with open('airportDF.pk1', 'wb') as fp:
    pickle.dump(newAirports, fp)

