#include <8051.h>

static void timer0_init(void)
{
    TMOD = (TMOD & 0xF0) | 0x01; /* Timer 0, 16-bit mode 1 */
    TH0 = 0x00;
    TL0 = 0x10;
    ET0 = 1;                     /* Enable Timer 0 interrupt */
    EA = 1;                      /* Enable global interrupts */
    TR0 = 1;                     /* Start Timer 0 */
}


// Make sure to use the correct IRQ number here:
void timer0_isr(void) __interrupt (3)
{
    P1_0 = !P1_0;
}


static void uart_init(void)
{
    SCON = 0x50;                  /* UART mode 1, 8-bit, receiver enabled */
    TMOD = (TMOD & 0x0F) | 0x20; /* Timer 1, 8-bit auto-reload */
    TH1 = 0x2D;                   /* Some messy baud rate */
    TR1 = 1;                      /* Start Timer 1 */
    TI = 1;                       /* Mark transmitter ready */
}

/*
 * PITFALL:
 * 
 * This bad implementation exhibits a mistake that is simply not caught
 * by classical analysis tools, but will turn up in a hardware simulation.
 *
 * If the CPU is reset, TI is by default clear. It will be set after a
 * write to SBUF. Hence, if we poll prior to sending, we will hang here.
 *
 * Now, the above uart_init() explicitely sets it, so we should be fine, no?
 *
 * The problem is, if the hardware is implemented "W0C", i.e. writing a
 * '1' is not effective.
 *
 * This is where we actually deviated from classical 8051 behaviour.
 * Check sfr8051_nxp_80c552.py for instance to verify the behavour in the
 * reg_S0CON register bit description. This basic setup has only support
 * for W0C behaviour!
 *

static void uart_putc(char c)
{
    while (!TI) { }
    TI = 0;
    SBUF = c;
}
 */

static void uart_putc(char c)
{
    SBUF = c;
    while (TI == 0) { } // Wait until transmitted
    TI = 0;
}

void main(void)
{
    const char *message = "Hello, world!\r\n";

    P0_0 = 1;


    uart_init();

    P1_0 = 0;

    while (*message) {
        uart_putc(*message++);
    }

	// This is the way to enable the timer IRQ
    timer0_init();
	ET1 = 1;

    for (;;) {
        /* Keep the program running */
    }
}

