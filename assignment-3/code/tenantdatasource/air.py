from kafka import KafkaProducer
import random
import time
import datetime
import requests

producer = KafkaProducer(bootstrap_servers=['localhost:29092'])

RATE_PER_SECOND = 1000

url = "https://data.sensor.community/airrohr/v1/filter/type=SDS011"


while True:

    current_time = datetime.datetime.now()
    print("Current time:", current_time)

    response = requests.get(url)

    if response.status_code == 200:
        sensorEvents = response.json()
        print(f'Number of sensor events: {len(sensorEvents)}')
        
        index = 0
        for sensorEvent in sensorEvents:
            index += 1
            timestamp = sensorEvent['timestamp']
            lat = sensorEvent['location']['latitude']
            lon = sensorEvent['location']['longitude']
            countryCode = sensorEvent['location']['country']
            sensorDataValues = sensorEvent['sensordatavalues']
            P1 = ''
            P2 = ''
            for sensorDataValue in sensorDataValues:
                if sensorDataValue['value_type'] == 'P1':
                    P1 = sensorDataValue['value']
                if sensorDataValue['value_type'] == 'P2':
                    P2 = sensorDataValue['value']
                    
            # error_rate = 0
            # sensorEventString = ''
            
            # if random.random() < error_rate:
            #     # error data
            #     sensorEventString = f'{timestamp},{lat},{lon},{countryCode},,'
            
            # else:
            #     # normal data
            #     sensorEventString = f'{timestamp},{lat},{lon},{countryCode},{P1},{P2}'
                
            sensorEventString = f'{timestamp},{lat},{lon},{countryCode},{P1},{P2}'
                
            print(f'sensorEventString-{index}: {sensorEventString}')
            producer.send('air', bytes(sensorEventString, encoding='utf-8'))
            time.sleep(1 / RATE_PER_SECOND)
        
    else:
        print("Error:", response.status_code)
        
    time.sleep(5 * 60)

