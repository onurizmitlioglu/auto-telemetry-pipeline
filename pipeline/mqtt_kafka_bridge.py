import os
import paho.mqtt.client as mqtt
from kafka import KafkaProducer

MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_TOPIC = "vehicles/+/telemetry"
KAFKA_SERVER = os.getenv("KAFKA_SERVER", "redpanda:9092")
KAFKA_TOPIC = "can-raw"

producer = KafkaProducer(bootstrap_servers=[KAFKA_SERVER])

def on_message(client, userdata, message):
    try:
        producer.send(KAFKA_TOPIC, value=message.payload)
        producer.flush()
    except Exception as e:
        print(f"Bridge error: {e}")

mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)

mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, 1883, 60)
mqtt_client.subscribe(MQTT_TOPIC)

print("MQTT-Kafka Bridge active, data is being transferred...")
mqtt_client.loop_forever()