#include <stdlib.h>     //exit()
#include <signal.h>     //signal()
#include <time.h>
#include "ADS1256.h"
#include "stdio.h"

#include <string.h>

void  Handler(int signo)
{
    //System Exit
    printf("\r\nEND                  \r\n");
    DEV_ModuleExit();

    exit(0);
}

int main(void)
{
    double a0_val, a1_val, a2_val;
    int cnt;
    double t0, t1;
    
    printf("ASD--> ADS1256 TEST\r\n");
    DEV_ModuleInit();
	
    // Exception handling:ctrl + c
    signal(SIGINT, Handler);

    if(ADS1256_init() == 1){
        printf("\r\nEND\r\n");
        DEV_ModuleExit();
        exit(0);
    }

    cnt = 0;
    t0 = t1 = time(NULL);
    while ( t1 - t0 < 1.0 ) {
	a0_val = (ADS1256_GetChannalValue(2)*5.0/0x7FFFFF)*1000000;
        a1_val = (ADS1256_GetChannalValue(3)*5.0/0x7FFFFF)*1000000;
	a2_val = (ADS1256_GetChannalValue(4)*5.0/0x7FFFFF)*1000000;
	t1 = time(NULL);
	cnt++;
	printf("ASD--> [%f][%f][%f] at %f\r\n", a0_val, a1_val, a2_val, t1);
	printf("\33[1A");
    }
    printf("\r\n");
    printf("ASD--> count: %d, time period: %f %f\r\n", cnt, (t1-t0), (t1-t0)/cnt); 
	
    cnt = 0;
    t0 = t1 = time(NULL);
    while ( t1 - t0 < 1.0 ) {
	a0_val = (ADS1256_GetChannalValue(2)*5.0/0x7FFFFF)*1000000;
        a1_val = (ADS1256_GetChannalValue(3)*5.0/0x7FFFFF)*1000000;
	a2_val = (ADS1256_GetChannalValue(4)*5.0/0x7FFFFF)*1000000;
	t1 = time(NULL);
	cnt++;
    }
    printf("\r\n");
    printf("ASD--> count: %d, time period: %f %f\r\n", cnt, (t1-t0), (t1-t0)/cnt); 

    return 0;
}
