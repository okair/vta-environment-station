import requests
import json
from picamera import PiCamera
import bme280
import smbus2
from time import sleep
import time
import datetime
from fractions import Fraction
import telepot
from telepot.loop import MessageLoop
import sds011
import config

## Telegram
bot = telepot.Bot(config.telebot_secret)

## Time
currentTime = datetime.datetime.now()
now = datetime.datetime.now()
hour = now.strftime('%H')
print( int(hour,10) )

## SDS011 Sensor
sensor = sds011.SDS011("/dev/ttyUSB0", use_query_mode=True)
sensor.sleep( sleep=False )

pm25sum = 0
pm10sum = 0
time.sleep(15)

for x in range(0, 9):
    pm25, pm10 = sensor.query()
    pm25sum += pm25
    pm10sum += pm10
    print(pm10)
    print(pm10sum)

sensor.sleep()

pm10avg = pm10sum / 10
pm25avg = pm25sum / 10

## Weather Sensors
port = 1
address = 0x76
bus = smbus2.SMBus(port)

bme280.load_calibration_params(bus,address)

def sensor_read():
    bme280_data = bme280.sample(bus,address)
    sensor_read.humidity  = int(bme280_data.humidity)
    sensor_read.pressure  = round(bme280_data.pressure) / 10
    sensor_read.temperature = round(bme280_data.temperature, 2)
    print(sensor_read.humidity, sensor_read.pressure, sensor_read.temperature)
    sleep(1)

sensor_read()
print(sensor_read.temperature)

## Image Capture
camera = PiCamera()

if int(hour,0) > 21 < 5:
	camera.resolution = (1280, 720)
	camera.framerate = Fraction(1, 6)
	camera.shutter_speed = 10000000
	camera.iso = 1600
	camera.sensor_mode = 3

	sleep(30)
	camera.exposure_mode = 'off'

else:
	sleep(5)

## Get image and upload it to WP, save ID
camera.capture('/home/pi/Desktop/image2.jpg')
image = open( '/home/pi/Desktop/image2.jpg', 'rb').read()
mediaheaders = {
	'Authorization': 'Basic ' + config.wp_token,
	'Content-Type': 'image/jpeg',
	'Content-disposition': 'attachment; filename=image2.jpg'
}
media = requests.post('https://' + config.website + '/wp-json/wp/v2/media', headers=mediaheaders, data=image)
response = json.loads(media.text)
print(response['id'])

## Create Post with previous image ID and weather data
payload = {'content': 'Humidity: ' + str(sensor_read.humidity) + '% \n Temperature: ' + str(sensor_read.temperature) + ' C \n Pressure: ' + str(sensor_read.pressure) + ' kPa', 'status': 'publish', 'title': currentTime, 'featured_media': response['id']}
headers = { 'Authorization': 'Basic ' + config.wp_token, 'Content-Type': 'application/x-www-form-urlencoded'}
r = requests.post('https:/' + config.website + '/wp-json/wp/v2/posts',headers=headers,  data = payload)


## Send Temp and PM data to Thingspeak
r2 = requests.get( 'https://api.thingspeak.com/update?api_key=' + config.thingspeak_api +'&field2=' + str(sensor_read.temperature) + '&field3=' + str(sensor_read.humidity) + '&field4=' + str(sensor_read.pressure) + '&field5=' + str(round(pm25avg, 2)) + '&field6=' + str(round(pm10avg, 2)) )

print(r2.status_code)
if ( r2.status_code != 200 ):
	bot.sendMessage(83988429, 'Update Issue: ' + str(r2.status_code))

print(r2.content)
print(r.text)
