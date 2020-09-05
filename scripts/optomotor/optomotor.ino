/* Program using Adafruit TLC5947 to control up to 24 components with pwm.
 *  Usage:
 *  
 * P CHANNEL DURATION(ms) [INTENSITY](0-1000)
 * 
 * CHANNEL is a componenet from 0 to 23.
 * DURATION defines how long this compoenet is to be activated for (in ms)
 * INTENSITY is the duty cycle of the PWM  (optional, from 0 to 1000)
 * 
 * example:
 * P 2 1000
 * P 0 1000 500
*/

// https://github.com/PaulStoffregen/SoftwareSerial - also available in the arduino libraries repo
#include <SoftwareSerial.h>

// https://github.com/kroimon/Arduino-SerialCommand - not in the repo
#include <SerialCommand.h>

// https://github.com/adafruit/Adafruit_TLC5947
#include <Adafruit_TLC5947.h>


#define BAUD 115200
#define N_OUTPUTS 24

// a set of timers measuring how long a given output should remain on for
int timers[N_OUTPUTS] = {0};
// stores the PWM of each output
unsigned int pwms[N_OUTPUTS];

unsigned long t0 = 0;
unsigned long t1 = 0;

SerialCommand SCmd;

/* ======================== TLC 5947 ======================== */
#define NUM_TLC5974 1

#define MAX_PWM 4095   
#define MIN_PWM 0   

// Define Pinouts from Arduino to SPI pins on LED Driver Board
#define TLC_DATA_PIN 3
#define TLC_CLOCK_PIN 4
#define TLC_LATCH_PIN   6
//#define oe  -1  // set to -1 to not use the enable pin (its optional)

Adafruit_TLC5947 tlc = Adafruit_TLC5947(NUM_TLC5974, 
                                        TLC_CLOCK_PIN,
                                        TLC_DATA_PIN,
                                        TLC_LATCH_PIN);

/* ======================== Push button======================== */

#define PUSH_BUTTON_PIN 12
// how long (in ms) the push buton should be hold for before demo is run
#define PUSH_BUTTON_THR 5000
// a timer that records how long push button is pressed for
int push_button_timer = 0; 




void setup() {
  Serial.begin(BAUD);
  SCmd.addCommand("P",sendPWMSerial);  
  SCmd.addCommand("D",demo);  
  SCmd.addCommand("H",help);
  //SCmd.setDefaultHandler(help);  
  
  tlc.begin();
  
  for (unsigned int i = 0; i != N_OUTPUTS; ++i){
    pwms[i] = 0;
    timers[i] = 0;
    tlc.setPWM(i, pwms[i]);
  }
  tlc.write();

  pinMode(PUSH_BUTTON_PIN, INPUT);
}

void help(){
  Serial.println("P CHANNEL DURATION(ms) [INTENSITY](0-1000)");
  }
  
void loop() { 
  SCmd.readSerial(); 
  delay(50);
  t0 = t1;
  t1 = millis();
  
  //fixme overflow of time!
  // i.e. if t0 > t1
  unsigned int tick =  t1 - t0;

  for (unsigned int i = 0; i != N_OUTPUTS; ++i){
    if(timers[i] != 0){
       timers[i] -= tick;
       if(timers[i] <0){
        timers[i] = 0;
        pwms[i] = 0;
      }
    }
  }
  //push_button_timer = 0;
  //Serial.println(digitalRead(PUSH_BUTTON_PIN) == LOW);
  //Serial.println(tick);
  if(digitalRead(PUSH_BUTTON_PIN) == LOW){
    if(push_button_timer > PUSH_BUTTON_THR)
        demo();
    push_button_timer = 0;
  }
    
  else{
    push_button_timer += tick;
  }

  for (unsigned int i = 0; i != N_OUTPUTS; ++i){
    tlc.setPWM(i, pwms[i]);
  }
  /*
  Serial.print(timers[1]);
  Serial.print(", ");
  Serial.println(pwms[1]);
  */
  tlc.write();
}


void sendPWM(unsigned int idx, unsigned int duration, unsigned int duty_cycle = MAX_PWM){
  timers[idx] = duration; // in ms
  pwms[idx] = duty_cycle; // in ms
}

void demo(){
  Serial.println("DEMO");
  for (unsigned int i = 0; i != N_OUTPUTS; ++i){
    tlc.setPWM(i,MAX_PWM);
    tlc.write();
    delay(500);
    tlc.setPWM(i,MIN_PWM);
    tlc.write();
  }
}

void sendPWMSerial(){
  char *arg;
  arg = SCmd.next();  
  unsigned int motor_id = 0;
  unsigned int duration = 0;
  unsigned int duty_cycle = MAX_PWM;
  unsigned int power = 0;
  
  if (arg != NULL) 
    motor_id = atoi(arg) ;
  else
   return; 
   
  arg = SCmd.next();   
  if (arg != NULL)
    duration = atoi(arg) ;
  else
    return;
  
  arg = SCmd.next();   
  if (arg != NULL){
    power = atoi(arg);
    duty_cycle = ((uint32_t)  power * (uint32_t) MAX_PWM)/1000;;
  }
  sendPWM(motor_id, duration, duty_cycle);
  }
