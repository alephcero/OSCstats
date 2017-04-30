# OSCstats
Project to read cellphone sensors using OSC and get stats

## Firts analysis of columns data:
- Columns A,B,C are data related to GPS
- D, E, F, G, H, I have same amaount of missing
- J, K dont have any data whatsoever
- L, M very few data
- N, O, P same missings than D,E,F,G,H,I
- Q, R dont have any data whatsoever

It appears that sensor data is stored in columns D, E, F, G, H, I, N, O, P. For I ould gather from the phone's specs sensors on the phone include Proximity sensor, Accelerometer, Ambient light sensor and Gyroscope. Next step would be to find in wich columns accelerometer data is stored.
