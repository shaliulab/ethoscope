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



void setup() {

  Serial.begin(BAUD);
  SCmd.addCommand("P", control);  
  SCmd.addCommand("D", demo);  
  SCmd.addCommand("H", help);
  SCmd.addCommand("T", teach);
  SCmd.addCommand("M", motor);
  

  // Initialise all pins to output mode
  for (int i = 0; i <= 19; i++) {
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

void control() {
  // Used by serial controller to activate pin
  // P channel duration

  char *arg;   
  int input = 0;
  int channel = 0;
  int duration = 0;

  arg = SCmd.next();  

  if (arg!=NULL)
    input = atoi(arg);
  else
    return;

  arg = SCmd.next();
  if (arg != NULL)
    duration = atoi(arg) ;
  else
    return;  

  activate(pins[input], duration);
}

void activate(int channel, int duration) {

  //Serial.print("Activating channel: ");
  //Serial.println(channel);
  
  digitalWrite (channel, HIGH);
  delay(duration);
  digitalWrite (channel, LOW);
}

void motor() {

    char *arg;
    int duration;
    
    arg = SCmd.next(); 
    if (arg!=NULL)
        duration = atoi(arg);
    else
        duration = 2000;
    
      //demo mode - activate all pins consecutively
    for (int i = 1; i <= 19; i++, i++) {
       activate (pins[i], duration);
       Serial.print("P");
       Serial.print(" ");
       Serial.print(pins[i]);
       Serial.print(" ");
       Serial.println(duration);
    }
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
       activate (pins[i], 500);
       Serial.print("P");
       Serial.print(" ");
       Serial.print(pins[i]);
       Serial.print(" ");
       Serial.println(500);
    }
}


void loop() {
  SCmd.readSerial(); 
  delay(50);
}
