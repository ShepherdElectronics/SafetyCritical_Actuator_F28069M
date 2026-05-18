#include "F2806x_Device.h"
#include "F2806x_Examples.h"

#define RX_BUFFER_SIZE       64U
#define SETPOINT_MIN         0
#define SETPOINT_MAX         1000

#define EPWM_PERIOD_COUNTS   1000U

/*
 * Demo timeout in real milliseconds.
 * Use 3000 ms for visible scope testing.
 * Later change to 100 ms for the final safety requirement.
 */
#define COMMS_TIMEOUT_MS     3000UL

typedef enum
{
    STATE_INIT = 0,
    STATE_SELF_TEST,
    STATE_READY,
    STATE_RUN,
    STATE_FAULT_LATCHED,
    STATE_SAFE_SHUTDOWN
} ControllerState_t;

typedef enum
{
    FAULT_NONE = 0,
    FAULT_INVALID_SETPOINT,
    FAULT_SENSOR_FAULT,
    FAULT_COMMS_TIMEOUT,
    FAULT_SELF_TEST_FAILED,
    FAULT_UNKNOWN_COMMAND
} FaultCode_t;

typedef struct
{
    ControllerState_t state;
    FaultCode_t fault;
    unsigned int enabled;
    unsigned int fault_latched;
    int setpoint;
    unsigned int pwm_percent;
    unsigned int sequence;
    unsigned long last_command_ms;
    unsigned long command_age_ms;
} Controller_t;

static Controller_t g_ctrl;
static volatile unsigned long g_ms_tick = 0UL;

static void Safety_SCIA_GpioInit(void);
static void Safety_SCIA_Init(void);
static void Safety_SCIA_TxChar(char c);
static void Safety_SCIA_TxString(const char *msg);
static int  Safety_SCIA_RxAvailable(void);
static char Safety_SCIA_RxChar(void);

static void Safety_Timer0_Init(void);
interrupt void Safety_Timer0_ISR(void);

static void Actuator_PWM_GpioInit(void);
static void Actuator_PWM_Init(void);
static void Actuator_PWM_SetPercent(unsigned int percent);

static void Controller_Init(void);
static void Controller_ProcessLine(char *line);
static void Controller_LatchFault(FaultCode_t fault);
static void Controller_ForceSafeOutput(void);
static void Controller_SendTelemetry(void);
static void Controller_CheckTimeout(void);

static int  starts_with(const char *s, const char *prefix);
static int  parse_en_command(const char *line, int *setpoint, unsigned int *seq);
static unsigned int parse_seq_after_comma(const char *line);
static int  parse_int(const char *s);
static void tx_uint(unsigned int value);
static void tx_ulong(unsigned long value);
static void tx_int(int value);
static const char* state_name(ControllerState_t state);
static const char* fault_name(FaultCode_t fault);

void main(void)
{
    char rx_buffer[RX_BUFFER_SIZE];
    unsigned int rx_index = 0U;
    unsigned long heartbeat_ms_last = 0UL;

    InitSysCtrl();

    DINT;

    InitPieCtrl();

    IER = 0x0000;
    IFR = 0x0000;

    InitPieVectTable();

    InitGpio();

    Safety_SCIA_GpioInit();
    Safety_SCIA_Init();

    Actuator_PWM_GpioInit();
    Actuator_PWM_Init();

    Controller_Init();

    Safety_Timer0_Init();

    Safety_SCIA_TxString("\r\nBOOT OK\r\n");
    Safety_SCIA_TxString("COMMANDS: EN,500,1  DIS,2  RST,3  FLT,4  CLR,5\r\n");
    Safety_SCIA_TxString("PWM OUT: ePWM1A / GPIO0\r\n");
    Safety_SCIA_TxString("CPU TIMER0 TIMEOUT DEMO ENABLED\r\n");
    Controller_SendTelemetry();

    for (;;)
    {
        if (Safety_SCIA_RxAvailable())
        {
            char c = Safety_SCIA_RxChar();

            if ((c == '\r') || (c == '\n'))
            {
                if (rx_index > 0U)
                {
                    rx_buffer[rx_index] = '\0';

                    Safety_SCIA_TxString("CMD=");
                    Safety_SCIA_TxString(rx_buffer);
                    Safety_SCIA_TxString("\r\n");

                    Controller_ProcessLine(rx_buffer);
                    Controller_SendTelemetry();

                    rx_index = 0U;
                }
            }
            else
            {
                if (rx_index < (RX_BUFFER_SIZE - 1U))
                {
                    rx_buffer[rx_index] = c;
                    rx_index++;
                }
                else
                {
                    rx_index = 0U;
                    Controller_LatchFault(FAULT_UNKNOWN_COMMAND);
                    Safety_SCIA_TxString("RX_ERROR=BUFFER_OVERFLOW\r\n");
                    Controller_SendTelemetry();
                }
            }
        }

        Controller_CheckTimeout();

        /*
         * Timer-based heartbeat every 1000 ms.
         */
        if ((g_ms_tick - heartbeat_ms_last) >= 1000UL)
        {
            heartbeat_ms_last = g_ms_tick;
            Safety_SCIA_TxString("HB ");
            Controller_SendTelemetry();
        }
    }
}

static void Safety_Timer0_Init(void)
{
    EALLOW;
    PieVectTable.TINT0 = &Safety_Timer0_ISR;
    EDIS;

    /*
     * CPU Timer0 uses SYSCLKOUT.
     * With the common F28069 setup, SYSCLKOUT = 90 MHz.
     * 1 ms period = 90000 counts.
     */
    CpuTimer0Regs.TCR.bit.TSS = 1;
    CpuTimer0Regs.PRD.all = 90000UL - 1UL;
    CpuTimer0Regs.TPR.all = 0U;
    CpuTimer0Regs.TPRH.all = 0U;
    CpuTimer0Regs.TCR.bit.TRB = 1;
    CpuTimer0Regs.TCR.bit.SOFT = 1;
    CpuTimer0Regs.TCR.bit.FREE = 1;
    CpuTimer0Regs.TCR.bit.TIE = 1;

    PieCtrlRegs.PIEIER1.bit.INTx7 = 1;
    IER |= M_INT1;

    EINT;
    ERTM;

    CpuTimer0Regs.TCR.bit.TSS = 0;
}

interrupt void Safety_Timer0_ISR(void)
{
    g_ms_tick++;

    PieCtrlRegs.PIEACK.all = PIEACK_GROUP1;
}

static void Controller_Init(void)
{
    g_ctrl.state = STATE_INIT;
    g_ctrl.fault = FAULT_NONE;
    g_ctrl.enabled = 0U;
    g_ctrl.fault_latched = 0U;
    g_ctrl.setpoint = 0;
    g_ctrl.pwm_percent = 0U;
    g_ctrl.sequence = 0U;
    g_ctrl.last_command_ms = g_ms_tick;
    g_ctrl.command_age_ms = 0UL;

    Controller_ForceSafeOutput();

    g_ctrl.state = STATE_SELF_TEST;

    Controller_ForceSafeOutput();

    g_ctrl.state = STATE_READY;
}

static void Controller_ProcessLine(char *line)
{
    int setpoint = 0;
    unsigned int seq = 0U;

    /*
     * Any received complete command refreshes command age.
     */
    g_ctrl.last_command_ms = g_ms_tick;
    g_ctrl.command_age_ms = 0UL;

    if (parse_en_command(line, &setpoint, &seq))
    {
        g_ctrl.sequence = seq;

        if ((setpoint < SETPOINT_MIN) || (setpoint > SETPOINT_MAX))
        {
            Controller_LatchFault(FAULT_INVALID_SETPOINT);
            return;
        }

        if (g_ctrl.fault_latched)
        {
            Controller_ForceSafeOutput();
            g_ctrl.enabled = 0U;
            g_ctrl.state = STATE_FAULT_LATCHED;
            return;
        }

        g_ctrl.enabled = 1U;
        g_ctrl.setpoint = setpoint;
        g_ctrl.pwm_percent = (unsigned int)(setpoint / 10);
        g_ctrl.fault = FAULT_NONE;
        g_ctrl.state = STATE_RUN;

        Actuator_PWM_SetPercent(g_ctrl.pwm_percent);
        return;
    }

    if (starts_with(line, "DIS"))
    {
        g_ctrl.sequence = parse_seq_after_comma(line);
        g_ctrl.enabled = 0U;
        g_ctrl.setpoint = 0;
        Controller_ForceSafeOutput();

        if (g_ctrl.fault_latched)
        {
            g_ctrl.state = STATE_FAULT_LATCHED;
        }
        else
        {
            g_ctrl.fault = FAULT_NONE;
            g_ctrl.state = STATE_READY;
        }

        return;
    }

    if (starts_with(line, "RST"))
    {
        g_ctrl.sequence = parse_seq_after_comma(line);

        if (!g_ctrl.enabled)
        {
            g_ctrl.fault = FAULT_NONE;
            g_ctrl.fault_latched = 0U;
            g_ctrl.setpoint = 0;
            g_ctrl.last_command_ms = g_ms_tick;
            g_ctrl.command_age_ms = 0UL;
            Controller_ForceSafeOutput();
            g_ctrl.state = STATE_READY;
        }

        return;
    }

    if (starts_with(line, "FLT"))
    {
        g_ctrl.sequence = parse_seq_after_comma(line);
        Controller_LatchFault(FAULT_SENSOR_FAULT);
        return;
    }

    if (starts_with(line, "CLR"))
    {
        g_ctrl.sequence = parse_seq_after_comma(line);
        return;
    }

    g_ctrl.sequence = parse_seq_after_comma(line);
    Controller_LatchFault(FAULT_UNKNOWN_COMMAND);
}

static void Controller_CheckTimeout(void)
{
    if ((g_ctrl.enabled != 0U) && (g_ctrl.state == STATE_RUN))
    {
        g_ctrl.command_age_ms = g_ms_tick - g_ctrl.last_command_ms;

        if (g_ctrl.command_age_ms >= COMMS_TIMEOUT_MS)
        {
            Controller_LatchFault(FAULT_COMMS_TIMEOUT);
            Safety_SCIA_TxString("TIMEOUT\r\n");
            Controller_SendTelemetry();
        }
    }
}

static void Controller_LatchFault(FaultCode_t fault)
{
    g_ctrl.fault = fault;
    g_ctrl.fault_latched = 1U;
    g_ctrl.enabled = 0U;
    g_ctrl.setpoint = 0;
    Controller_ForceSafeOutput();
    g_ctrl.state = STATE_FAULT_LATCHED;
}

static void Controller_ForceSafeOutput(void)
{
    g_ctrl.pwm_percent = 0U;
    Actuator_PWM_SetPercent(0U);
}

static void Controller_SendTelemetry(void)
{
    Safety_SCIA_TxString("STATE=");
    Safety_SCIA_TxString(state_name(g_ctrl.state));

    Safety_SCIA_TxString(",FAULT=");
    Safety_SCIA_TxString(fault_name(g_ctrl.fault));

    Safety_SCIA_TxString(",EN=");
    tx_uint(g_ctrl.enabled);

    Safety_SCIA_TxString(",SP=");
    tx_int(g_ctrl.setpoint);

    Safety_SCIA_TxString(",PWM=");
    tx_uint(g_ctrl.pwm_percent);

    Safety_SCIA_TxString(",AGE=");
    tx_ulong(g_ctrl.command_age_ms);

    Safety_SCIA_TxString(",SEQ=");
    tx_uint(g_ctrl.sequence);

    Safety_SCIA_TxString(",LATCH=");
    tx_uint(g_ctrl.fault_latched);

    Safety_SCIA_TxString("\r\n");
}

static void Actuator_PWM_GpioInit(void)
{
    EALLOW;

    GpioCtrlRegs.GPAPUD.bit.GPIO0 = 0;
    GpioCtrlRegs.GPAMUX1.bit.GPIO0 = 1;

    EDIS;
}

static void Actuator_PWM_Init(void)
{
    EALLOW;

    SysCtrlRegs.PCLKCR1.bit.EPWM1ENCLK = 1;
    SysCtrlRegs.PCLKCR0.bit.TBCLKSYNC = 0;

    EDIS;

    EPwm1Regs.TBCTL.bit.CTRMODE = TB_COUNT_UP;
    EPwm1Regs.TBCTL.bit.PHSEN = TB_DISABLE;
    EPwm1Regs.TBCTL.bit.PRDLD = TB_SHADOW;
    EPwm1Regs.TBCTL.bit.SYNCOSEL = TB_SYNC_DISABLE;
    EPwm1Regs.TBCTL.bit.HSPCLKDIV = TB_DIV1;
    EPwm1Regs.TBCTL.bit.CLKDIV = TB_DIV1;

    EPwm1Regs.TBCTR = 0U;
    EPwm1Regs.TBPRD = EPWM_PERIOD_COUNTS;

    EPwm1Regs.CMPCTL.bit.SHDWAMODE = CC_SHADOW;
    EPwm1Regs.CMPCTL.bit.LOADAMODE = CC_CTR_ZERO;

    EPwm1Regs.CMPA.half.CMPA = 0U;

    EPwm1Regs.AQCTLA.all = 0U;
    EPwm1Regs.AQCTLA.bit.ZRO = AQ_SET;
    EPwm1Regs.AQCTLA.bit.CAU = AQ_CLEAR;

    EPwm1Regs.AQCSFRC.bit.CSFA = 1;

    EALLOW;
    SysCtrlRegs.PCLKCR0.bit.TBCLKSYNC = 1;
    EDIS;

    Actuator_PWM_SetPercent(0U);
}

static void Actuator_PWM_SetPercent(unsigned int percent)
{
    unsigned int cmp;

    if (percent > 100U)
    {
        percent = 100U;
    }

    if (percent == 0U)
    {
        EPwm1Regs.CMPA.half.CMPA = 0U;
        EPwm1Regs.AQCSFRC.bit.CSFA = 1;
        return;
    }

    if (percent >= 100U)
    {
        EPwm1Regs.CMPA.half.CMPA = EPWM_PERIOD_COUNTS;
        EPwm1Regs.AQCSFRC.bit.CSFA = 2;
        return;
    }

    cmp = (unsigned int)(((unsigned long)EPWM_PERIOD_COUNTS * (unsigned long)percent) / 100UL);

    EPwm1Regs.CMPA.half.CMPA = cmp;
    EPwm1Regs.AQCSFRC.bit.CSFA = 0;
}

static void Safety_SCIA_GpioInit(void)
{
    EALLOW;

    GpioCtrlRegs.GPAPUD.bit.GPIO28 = 0;
    GpioCtrlRegs.GPAPUD.bit.GPIO29 = 0;

    GpioCtrlRegs.GPAQSEL2.bit.GPIO28 = 3;

    GpioCtrlRegs.GPAMUX2.bit.GPIO28 = 1;
    GpioCtrlRegs.GPAMUX2.bit.GPIO29 = 1;

    EDIS;
}

static void Safety_SCIA_Init(void)
{
    SciaRegs.SCICCR.all = 0x0007;
    SciaRegs.SCICTL1.all = 0x0003;
    SciaRegs.SCICTL2.all = 0x0000;

    SciaRegs.SCIHBAUD = 0x0000;
    SciaRegs.SCILBAUD = 24;

    SciaRegs.SCIFFTX.all = 0xE040;
    SciaRegs.SCIFFRX.all = 0x2044;
    SciaRegs.SCIFFCT.all = 0x0000;

    SciaRegs.SCICTL1.all = 0x0023;
}

static void Safety_SCIA_TxChar(char c)
{
    while (SciaRegs.SCIFFTX.bit.TXFFST != 0)
    {
    }

    SciaRegs.SCITXBUF = (Uint16)c;
}

static void Safety_SCIA_TxString(const char *msg)
{
    while (*msg != '\0')
    {
        Safety_SCIA_TxChar(*msg);
        msg++;
    }
}

static int Safety_SCIA_RxAvailable(void)
{
    return (SciaRegs.SCIFFRX.bit.RXFFST != 0);
}

static char Safety_SCIA_RxChar(void)
{
    return (char)(SciaRegs.SCIRXBUF.all & 0x00FF);
}

static int starts_with(const char *s, const char *prefix)
{
    while (*prefix != '\0')
    {
        if (*s != *prefix)
        {
            return 0;
        }

        s++;
        prefix++;
    }

    return 1;
}

static int parse_en_command(const char *line, int *setpoint, unsigned int *seq)
{
    const char *p;
    const char *q;

    if (!starts_with(line, "EN,"))
    {
        return 0;
    }

    p = line + 3;

    *setpoint = parse_int(p);

    q = p;
    while ((*q != '\0') && (*q != ','))
    {
        q++;
    }

    if (*q != ',')
    {
        *seq = 0U;
        return 1;
    }

    q++;
    *seq = (unsigned int)parse_int(q);

    return 1;
}

static unsigned int parse_seq_after_comma(const char *line)
{
    const char *p = line;

    while ((*p != '\0') && (*p != ','))
    {
        p++;
    }

    if (*p == ',')
    {
        p++;
        return (unsigned int)parse_int(p);
    }

    return 0U;
}

static int parse_int(const char *s)
{
    int value = 0;
    int sign = 1;

    if (*s == '-')
    {
        sign = -1;
        s++;
    }

    while ((*s >= '0') && (*s <= '9'))
    {
        value = (value * 10) + ((int)(*s - '0'));
        s++;
    }

    return value * sign;
}

static void tx_uint(unsigned int value)
{
    tx_ulong((unsigned long)value);
}

static void tx_ulong(unsigned long value)
{
    char buf[12];
    int i = 0;
    int j;

    if (value == 0UL)
    {
        Safety_SCIA_TxChar('0');
        return;
    }

    while ((value > 0UL) && (i < 12))
    {
        buf[i] = (char)('0' + (value % 10UL));
        value = value / 10UL;
        i++;
    }

    for (j = i - 1; j >= 0; j--)
    {
        Safety_SCIA_TxChar(buf[j]);
    }
}

static void tx_int(int value)
{
    if (value < 0)
    {
        Safety_SCIA_TxChar('-');
        tx_uint((unsigned int)(-value));
    }
    else
    {
        tx_uint((unsigned int)value);
    }
}

static const char* state_name(ControllerState_t state)
{
    switch (state)
    {
        case STATE_INIT:
            return "INIT";

        case STATE_SELF_TEST:
            return "SELF_TEST";

        case STATE_READY:
            return "READY";

        case STATE_RUN:
            return "RUN";

        case STATE_FAULT_LATCHED:
            return "FAULT_LATCHED";

        case STATE_SAFE_SHUTDOWN:
            return "SAFE_SHUTDOWN";

        default:
            return "UNKNOWN_STATE";
    }
}

static const char* fault_name(FaultCode_t fault)
{
    switch (fault)
    {
        case FAULT_NONE:
            return "NONE";

        case FAULT_INVALID_SETPOINT:
            return "INVALID_SETPOINT";

        case FAULT_SENSOR_FAULT:
            return "SENSOR_FAULT";

        case FAULT_COMMS_TIMEOUT:
            return "COMMS_TIMEOUT";

        case FAULT_SELF_TEST_FAILED:
            return "SELF_TEST_FAILED";

        case FAULT_UNKNOWN_COMMAND:
            return "UNKNOWN_COMMAND";

        default:
            return "UNKNOWN_FAULT";
    }
}
