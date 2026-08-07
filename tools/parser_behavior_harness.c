#include <stdio.h>
#include "../src/command_parser.h"

static int expect_enable(const char *line, int expected_valid, long expected_setpoint)
{
    long setpoint = -1L;
    unsigned int seq = 0U;
    int valid = Controller_ParseEnableCommand(line, &setpoint, &seq);
    return valid == expected_valid && (!expected_valid || setpoint == expected_setpoint);
}

int main(void)
{
    const char *malformed[] = {"EN,", "EN,500", "EN,500,1,extra", "EN,2147483648,1", "EN,-2147483649,1", "EN,500,65536", "EN,500,1x", "DISASTER,1"};
    size_t i;
    unsigned int seq = 0U;
    if (!expect_enable("EN,0,0", 1, 0) || !expect_enable("EN,9,1", 1, 9) || !expect_enable("EN,501,2", 1, 501) || !expect_enable("EN,1000,3", 1, 1000)) return 1;
    for (i=0U; i<sizeof(malformed)/sizeof(malformed[0]); ++i) if (expect_enable(malformed[i], 0, 0) == 0) return 2;
    if (Controller_SetpointToPwmPercent(0)!=0U || Controller_SetpointToPwmPercent(9)!=0U || Controller_SetpointToPwmPercent(501)!=50U || Controller_SetpointToPwmPercent(999)!=99U || Controller_SetpointToPwmPercent(1000)!=100U) return 3;
    if (!Controller_ParseSimpleCommand("DIS,1", "DIS", &seq) || Controller_ParseSimpleCommand("DISASTER,1", "DIS", &seq)) return 4;
    puts("parser behavior checks passed");
    return 0;
}
