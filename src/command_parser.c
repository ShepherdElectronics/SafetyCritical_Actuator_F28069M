#include "command_parser.h"

static int parse_unsigned_token(const char *start, const char **end, unsigned long *value)
{
    const char *p = start;
    unsigned long result = 0UL;
    unsigned int digits = 0U;
    while ((*p >= '0') && (*p <= '9'))
    {
        unsigned long digit = (unsigned long)(*p - '0');
        if (result > ((0xFFFFFFFFUL - digit) / 10UL)) return 0;
        result = (result * 10UL) + digit;
        p++;
        digits++;
    }
    if (digits == 0U) return 0;
    *end = p;
    *value = result;
    return 1;
}

static int parse_signed_token(const char *start, const char **end, long *value)
{
    const char *p = start;
    unsigned long magnitude = 0UL;
    int negative = 0;
    if (*p == '-') { negative = 1; p++; }
    if (!parse_unsigned_token(p, &p, &magnitude)) return 0;
    if (negative)
    {
        if (magnitude > 2147483648UL) return 0;
        *value = (magnitude == 2147483648UL) ? (-2147483647L - 1L) : -(long)magnitude;
    }
    else
    {
        if (magnitude > 2147483647UL) return 0;
        *value = (long)magnitude;
    }
    *end = p;
    return 1;
}

int Controller_ParseEnableCommand(const char *line, long *setpoint, unsigned int *seq)
{
    const char *p;
    unsigned long sequence_value;
    if ((line[0] != 'E') || (line[1] != 'N') || (line[2] != ',')) return 0;
    if (!parse_signed_token(line + 3, &p, setpoint) || (*p != ',')) return 0;
    if (!parse_unsigned_token(p + 1, &p, &sequence_value) || (*p != '\0')) return 0;
    if (sequence_value > 65535UL) return 0;
    *seq = (unsigned int)sequence_value;
    return 1;
}

int Controller_ParseSimpleCommand(const char *line, const char *opcode, unsigned int *seq)
{
    const char *p;
    unsigned long sequence_value;
    if ((line[0] != opcode[0]) || (line[1] != opcode[1]) || (line[2] != opcode[2]) || (line[3] != ',')) return 0;
    if (!parse_unsigned_token(line + 4, &p, &sequence_value) || (*p != '\0')) return 0;
    if (sequence_value > 65535UL) return 0;
    *seq = (unsigned int)sequence_value;
    return 1;
}

unsigned int Controller_SetpointToPwmPercent(long setpoint)
{
    /* Every accepted 0..1000 setpoint is quantized down to whole PWM percent. */
    return (unsigned int)(setpoint / 10L);
}
