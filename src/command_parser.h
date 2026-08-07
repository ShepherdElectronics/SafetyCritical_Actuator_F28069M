#ifndef COMMAND_PARSER_H
#define COMMAND_PARSER_H

int Controller_ParseEnableCommand(const char *line, long *setpoint, unsigned int *seq);
int Controller_ParseSimpleCommand(const char *line, const char *opcode, unsigned int *seq);
unsigned int Controller_SetpointToPwmPercent(long setpoint);

#endif
