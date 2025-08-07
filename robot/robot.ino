#include <ArduinoJson.h>
#include <Servo.h>
#include <DHT.h>


const int echoPin = 23;
const int statusLED = 3;
const int trigPin = 22;

const int DHTPin = 2;

float humidity;
float temperature;
unsigned long lastReadTime = 0;


DHT dht(DHTPin, DHT21);


Servo xCamera;
Servo yCamera;

float getDistance()
{

  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  return (pulseIn(echoPin, HIGH) * 0.0343) / 2; // divided by 2 to take into account just going or coming back, not whole time.
}

void setup()
{
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  pinMode(statusLED, OUTPUT);

  xCamera.attach(8);
  yCamera.attach(9);
  xCamera.write(90);
  yCamera.write(90);

  pinMode(52, OUTPUT);
  pinMode(53, OUTPUT);
  pinMode(42, OUTPUT);
  pinMode(43, OUTPUT);
  pinMode(LED_BUILTIN, OUTPUT);

  dht.begin();
  // wait for the DHT to start itself as it takes 55 microseconds
  delayMicroseconds(100);

  Serial.begin(9600);

  int incoming = -1;
  while (incoming < 0)
  {
    incoming = Serial.read();
  }
  Serial.println(incoming);
}

void loop()
{
  StaticJsonDocument<200> data;

  DeserializationError err = deserializeJson(data, Serial);

  if (err)
  {
    digitalWrite(statusLED, HIGH);
    return;
  }

  if (data["header"] == "motor")
  {
    digitalWrite(52, data["right_first"]);
    digitalWrite(53, data["left_first"]);
    digitalWrite(42, data["right_second"]);
    digitalWrite(43, data["left_second"]);
    analogWrite(NULL, data["right_speed"]);
    analogWrite(NULL, data["left_speed"]);
    xCamera.write(data["camera_horizontal"]);
    yCamera.write(data["camera_vertical"]);
  }
  if (data["header"] == "sensor")
  {
    StaticJsonDocument<200> doc;
    if (millis() - lastReadTime > 5 * 1000){
      temperature = dht.readTemperature();
      humidity = dht.readHumidity();
      lastReadTime = millis();
    }
    doc["distance"] = getDistance();
    doc["temperature"] = temperature;
    doc["humidity"] = humidity;
    char jsonString[200];
    unsigned int length = serializeJson(doc, jsonString);

    Serial.println(jsonString);
  }
}
