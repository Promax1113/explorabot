#include <ArduinoJson.h>
#include <Servo.h>
#include <DHT.h>


const int echoPin = 2;
const int trigPin = 3;

const int DHTPin = 45;

int voltageReaderPin = A0;
int voltageReaderValue;

float humidity;
float temperature;
unsigned long lastReadTime = 0;
unsigned long lastBatReadTime = millis();

DHT dht(DHTPin, DHT21);

// Motors
int rightEnable = 10;
int rightFirst = 8;
int rightSecond = 9;
int leftEnable = 6;
int leftFirst = 4;
int leftSecond = 5;

// Relays
int motorRelayPin = 22;
int servoRelayPin = 23;
int lightsRelayPin = 24;

float battery;

Servo xCamera;
Servo yCamera;

float getBatteryPercentage(){
  voltageReaderValue = analogRead(voltageReaderPin);
  float result = fmap(voltageReaderValue, 0, 1023, 0.0, 25);
  return result;
}

float fmap(float x, float in_min, float in_max, float out_min, float out_max)
{
  return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
}

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
  
  pinMode(motorRelayPin, OUTPUT);
  pinMode(servoRelayPin, OUTPUT);
  pinMode(lightsRelayPin, OUTPUT);

  digitalWrite(motorRelayPin, LOW);
  digitalWrite(servoRelayPin, LOW);
  digitalWrite(lightsRelayPin, LOW);


  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  pinMode(statusLED, OUTPUT);

  xCamera.attach(12);
  yCamera.attach(11);
  xCamera.write(90);
  yCamera.write(90);

  humidity = dht.readHumidity()
  temperature = dht.readTemperature()

  battery = getBatteryPercentage();

  dht.begin();
  // wait for the DHT to start itself as it takes 55 microseconds
  delayMicroseconds(100);

  Serial.begin(9600);

  //while (Serial.available() == 0);

  //int incoming = Serial.read();

  //delay(1500);
  //Serial.println(incoming);

}

void loop()
{
  StaticJsonDocument<200> data;


  if (millis() - lastBatReadTime > 30 * 1000)
    {
     battery = getBatteryPercentage();

 
      lastBatReadTime = millis();
    } 

  DeserializationError err = deserializeJson(data, Serial);

  if (err)
  {

    return;
  }
  if (data["header"] == "motor")
  {
    digitalWrite(rightFirst, data["right_first"]);
    digitalWrite(leftFirst, data["left_first"]);
    digitalWrite(rightSecond, data["right_second"]);
    digitalWrite(leftSecond, data["left_second"]);
    analogWrite(rightEnable, data["right_speed"]);
    analogWrite(leftEnable, data["left_speed"]);
    xCamera.write(data["camera_horizontal"]);
    yCamera.write(data["camera_vertical"]);
  }
  if (data["header"] == "battery"){
    Serial.println(getBatteryPercentage());
  }
  if (data["header"] == "sensor")
  {
    StaticJsonDocument<200> doc;
    if (millis() - lastReadTime > 5 * 1000)
    {
      temperature = dht.readTemperature();
      humidity = dht.readHumidity();
      lastReadTime = millis();
    } 
    doc["distance"] = getDistance();
    doc["temperature"] = temperature;
    doc["humidity"] = humidity;
    doc["battery"] = battery;
    char jsonString[200];
    unsigned int length = serializeJson(doc, jsonString);

    Serial.println(jsonString);
  }
}
