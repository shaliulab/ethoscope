 /* Uses an Arduino Micro on a custom PCB board to drive 3 Darlington arrays and control 20 digital ouputs
 * up to current usage of 500mA per output
 * Usage:
 *  
 * P CHANNEL DURATION(ms)
 * 
 * CHANNEL is an output from 0 to 19
 * DURATION defines how long this output is to be activated for (in ms)
 *  
 * example:
 * P 2 1000
 * P 0 1000
 * 
 * Sending the command "T" over the serial returns a dictionary that Python can use
 * to learn dynamically about the capabilities of the module
 * 
 * Last modified 8 Jul 2020 - giorgio@gilest.ro
 * 
 */

// Version of the sketch
const float VERSION = 1.0; 

#define PCBVERSION 11
// PCB version 1.0 or 1.1 - check your PCB

#define MODULE 0
// 0 -> SD
// 1 -> AGOSD
// 2 -> AGO

// https://github.com/kroimon/Arduino-SerialCommand
#include <SerialCommand.h>
SerialCommand SCmd;
#define BAUD 115200 // this is what the ethoscope expects! Do not change this.
#define N_OUTPUTS 20
// if you want concurrent interactions,
// set CONCURRENT to 1   (simultaneous)
// otherwise set it to 0 (sequence)
#define CONCURRENT 1

// static const uint8_t analog_pins[] = {A0,A1,A2,A3,A4,A5};

#if (PCBVERSION == 10) //Version 1.0 of the PCB
    static const uint8_t pins[] = {1,0,2,3,4,5,6,7,8,9,10,11,12,13,A0,A1,A2,A3,A4,A5};
//    static const uint8_t M_pins[] = {0,3,5,7,9,11,13,A1,A3,A5};
//    static const uint8_t V_pins[] = {1,2,4,6,8,10,12,A0,A2,A4};
#elif (PCBVERSION == 11) //Version 1.1 of the PCB
    static const uint8_t pins[] = {0,1,2,3,4,5,6,7,8,9,10,11,12,13,A0,A1,A2,A3,A4,A5};
//    static const uint8_t M_pins[] = {1,3,5,7,9,11,13,A1,A3,A5};
//    static const uint8_t V_pins[] = {0,2,4,6,8,10,12,A0,A2,A4};
#endif
    
#if (MODULE == 0)
    const String MODULE_NAME = "'N20 Sleep Deprivation Module'";
    const String MODULE_DESC = "'Rotates up to twenty N20 geared motors independently'";
#elif (MODULE == 1)
    const String MODULE_NAME = "'AGOSD Sleep Deprivation and Odour Arousal Module'";
    const String MODULE_DESC = "'Operates ten N20 geared motors and ten solenoid valves independently'";
#elif (MODULE == 2)
    const String MODULE_NAME = "'AGO Odour Arousal Module'";
    const String MODULE_DESC = "'Operates ten solenoid valves independently'";
#endif

int timers[N_OUTPUTS] = {0};
int react[N_OUTPUTS] = {0};
int train_on[N_OUTPUTS] = {0};
int train_off[N_OUTPUTS] = {0};
int state[N_OUTPUTS] = {0};
int train_on_start[N_OUTPUTS] = {0};
int train_off_start[N_OUTPUTS] = {0};
long unsigned last_timestamp[N_OUTPUTS] = {0};

unsigned long t0 = 0;
unsigned long t1 = 0;

void setup() {

  Serial.begin(BAUD);
  SCmd.addCommand("P", control);  
  SCmd.addCommand("D", demo);  
  SCmd.addCommand("H", help);
  SCmd.addCommand("T", teach);
  SCmd.addCommand("R", pulse_train);
  

  // Initialise all pins to output mode
  for (int i = 0; i <= (N_OUTPUTS-1); i++) {
      pinMode(pins[i], OUTPUT);
    }
//  this is not a good idea because if the module crashes it will restart stimulating all channels
//  demo();
}

void teach() {
  //this sends a dictionary withe information the ethoscope needs to populate a custom class
  Serial.print("{'version' : 'FW-"); Serial.print(VERSION); Serial.print(";HW-"); Serial.print(PCBVERSION); Serial.print("', ");
  Serial.print("'module_name' : "); Serial.print (MODULE_NAME); Serial.print(", ");
  Serial.print("'module_description' : "); Serial.print (MODULE_DESC); Serial.print(", ");
  Serial.print("'test_button' : { 'title' : 'Test output', 'description' : 'Test all outputs in a sequence', 'command' : 'D'}, ");
  Serial.print("'command' : 'P',");
  Serial.print("'arguments' : {'channel':  ['The channel to act on', 'MAPSTOROI'], 'duration' : ['The length of the stimulus in ms']}");
  Serial.println("}");
}

void activate_not_concurrent(int i, int duration) {

  //Serial.print("Activating channel: ");
  //Serial.println(channel);
  int channel = pins[i];
  digitalWrite(channel, HIGH);
  delay(duration);
  digitalWrite(channel, LOW);
}

void activate_concurrent(int i, int duration) {
  timers[i] = duration;
  react[i] = 1;
}

void activate(int i, int duration) {
  if (CONCURRENT == 1) {
    activate_concurrent(i, duration);
  } else if (CONCURRENT == 0) {
    activate_not_concurrent(i, duration);    
  }
}

void activate_pulse_train_not_concurrent(int i, int duration, int pulse_on, int pulse_off) {

  //Serial.print("Activating channel: ");
  //Serial.println(channel);
  int channel = pins[i];
  Serial.print("Pulse on: ");
  Serial.println(pulse_on);

  Serial.print("Pulse off: ");
  Serial.println(pulse_off);

  int computed_freq = 1000 / (pulse_on + pulse_off);
  
  Serial.print("Frequency: ");
  Serial.println(computed_freq);

  unsigned long start = millis();
  if ((millis() - start) < duration) Serial.println("Entering loop");
  
  while ((millis() - start) < duration) {
      digitalWrite(channel, HIGH);
      delay(pulse_on);
      digitalWrite(channel, LOW);
      delay(pulse_off);
  }
  Serial.println("Out of loop");
  digitalWrite(channel, LOW); 
}

void activate_pulse_train_concurrent(int i, int duration, int pulse_on, int pulse_off) {
  timers[i] = duration;
  train_on[i] = pulse_on;
  train_on_start[i] = pulse_on;
  train_off[i] = pulse_off;
  train_off_start[i] = pulse_off;
  react[i] = 1;
}

void activate_pulse_train(int i, int duration, int pulse_on, int pulse_off) {
 
  if (CONCURRENT == 1) {
    activate_pulse_train_concurrent(i, duration, pulse_on, pulse_off);
  } else if (CONCURRENT == 0) {
    activate_pulse_train_not_concurrent(i, duration, pulse_on, pulse_off); 
  }
}

void pulse_train() {

   char *arg;
   int input = 0;
   int channel = 0;
   int duration = 0;
   int pulse_on = 0;
   int pulse_off = 0;

  input = parse_int_variable();
  duration = parse_int_variable();
  pulse_on = parse_int_variable();
  pulse_off = parse_int_variable();
  activate_pulse_train(input, duration, pulse_on, pulse_off);     
}


int parse_int_variable() {

  char *arg;   
  int data;
  arg = SCmd.next();  

  if (arg!=NULL) {
    data = atoi(arg);
    return data;
  } else {
    return;
  }   
}

void control() {
  // Used by serial controller to activate pin
  // P channel duration

  int input = 0;
  int duration = 0;

  input = parse_int_variable();
  duration = parse_int_variable();
  activate(input, duration);
}


void help(){
  // Prints information regarding usage on serial terminal
  Serial.println("P CHANNEL(1-20) DURATION(ms) - e.g. P 7 750");
  Serial.println("D - Demo");
  Serial.println("T - Teach the ethoscope how to use the module");
}

void demo(){
    //demo mode - activate all pins consecutively
    for (int i = 0; i <= 19; i++) {
       activate(i, 500);
       Serial.print("P");
       Serial.print(" ");
       Serial.print(pins[i]);
       Serial.print(" ");
       Serial.println(500);
    }
}


void monitor_one_timer(int i, int timer, unsigned int tick) {
  
}

void train_loop() {
  
  for (unsigned int i = 0; i != N_OUTPUTS; ++i){
    
//    Serial.print(i);
//    Serial.print(": ");
    Serial.println(timers[i]);

    long unsigned now = millis();
    long unsigned tick = now - last_timestamp[i];
    last_timestamp[i] = now;
    

    if(timers[i] != 0){
    timers[i] -= tick;
      if(timers[i] <0){
          timers[i] = 0;
      }
    }

    if (train_on[i] != 0 & (react[i] == 1 | state[i] == 1)) {
      train_on[i] -= tick;
      if (train_on[i] <= 0) {
        train_on[i] = train_on_start[i];
        react[i] = 0;
      }
    }

    if (train_off[i] != 0 & state[i] == 0) {
      train_off[i] -= tick;
      if (train_off[i] <= 0) {
        train_off[i] = train_off_start[i];
        react[i] = 1;
      }
    }
    
    if (timers[i] == 0) {
        digitalWrite(pins[i], LOW);
        react[i] = 0;
        state[i] = 0;
        train_on[i] = 0;
        train_on_start[i] = 0;
        train_off[i] = 0;
        train_off_start[i] = 0;

    } else if (react[i] == 1) {
      digitalWrite(pins[i], HIGH);
      state[i] = 1;
    } else if (state[i] == 1) {
      digitalWrite(pins[i], LOW);
      state[i] = 0;

    }
  }
}
void default_loop(unsigned int tick) {

  for (unsigned int i = 0; i != N_OUTPUTS; ++i){
    int timer = timers[i];
  
    if(timer != 0){
    timer -= tick;
      if(timer <0){
          timer = 0;
      }
    }
    if (timer == 0) {
        digitalWrite(pins[i], LOW);
    } else if (react[i] == 1) {
      digitalWrite(pins[i], HIGH);
      react[i] = 0;      
    }
  }
}

void loop() {
  SCmd.readSerial(); 
  delay(50);
  t0 = t1;
  t1 = millis();
  
   //fixme overflow of time!
  // i.e. if t0 > t1
  unsigned int tick =  t1 - t0;
//  default_loop(tick);
  train_loop();
  
}
