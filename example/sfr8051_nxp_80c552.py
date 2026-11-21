# Generated file, editing void
# This file is part of the cyrite HDL suite
# (c) 202* section5.ch

from cyhdl import *
from cyrite.library.soc import Reg, BF
from . import mmr
# from cyrite.netpp_soc.peripheral_cores import *

sfrint_DATA_WIDTH = 8
sfr_8xc552_DATA_WIDTH = 8

_BS_ = lambda x: x * 8


##########################################
# Register map 'SFR_intern'

class rmap_sfrint(mmr.Generator):
    offset = 0
    default_size = 8
    """The stack pointer
    """
    reg_SP = Reg(_BS_(1), []
            
    )
    """Data pointer low
    """
    reg_DPL = Reg(_BS_(1), []
            
    )
    """Data pointer high
    """
    reg_DPH = Reg(_BS_(1), []
            
    )
    reg_DPL1 = Reg(_BS_(1), []
            
    )
    reg_DPH1 = Reg(_BS_(1), []
            
    )
    reg_PSW = Reg(_BS_(1), []
            
    )
    reg_ACC = Reg(_BS_(1), []
            
    )
    reg_B = Reg(_BS_(1), []
            
    )

    # Address mapping:
    register_map = {
        (0x81, "") : [ 'SP', reg_SP ],
        (0x82, "") : [ 'DPL', reg_DPL ],
        (0x83, "") : [ 'DPH', reg_DPH ],
        (0x84, "") : [ 'DPL1', reg_DPL1 ],
        (0x85, "") : [ 'DPH1', reg_DPH1 ],
        (0xd0, "") : [ 'PSW', reg_PSW ],
        (0xe0, "") : [ 'ACC', reg_ACC ],
        (0xf0, "") : [ 'B', reg_B ],
    }

##########################################
# Register map '8XC552_SFR'

class rmap_sfr_8xc552(mmr.Generator):
    offset = 0
    default_size = 8
    """A/D converter high.
    """
    reg_ADCH = Reg(default_size, []
        , flags = Reg.READONLY    
    )
    """Adc control.
    """
    reg_ADCON = Reg(default_size,
        [    
            BF("ADC1", 7, 7),
            BF("ADC0", 6, 6),
            BF("ADEX", 5, 5),
            BF("ADCI", 4, 4, flags = BF.W0C),
            BF("ADCS", 3, 3),
            BF("AADR2", 2, 2),
            BF("AADR1", 1, 1),
            BF("AADR0", 0, 0),
        ]    
        , flags = Reg.VOLATILE    
    )
    """Capture control.
    """
    reg_CTCON = Reg(default_size,
        [    
            BF("CTN3", 7, 7),
            BF("CTP3", 6, 6),
            BF("CTN2", 5, 5),
            BF("CTP2", 4, 4),
            BF("CTN1", 3, 3),
            BF("CTP1", 2, 2),
            BF("CTN0", 1, 1),
            BF("CTP0", 0, 0),
        ]    
            
    )
    """Capture timer 3 high.
    """
    reg_CTH3 = Reg(default_size, []
            
    )
    """Capture timer 2 high.
    """
    reg_CTH2 = Reg(default_size, []
            
    )
    """Capture timer 1 high.
    """
    reg_CTH1 = Reg(default_size, []
            
    )
    """Capture timer 0 high.
    """
    reg_CTH0 = Reg(default_size, []
            
    )
    """Capture compare 2 high.
    """
    reg_CMH2 = Reg(default_size, []
            
    )
    """Capture compare 1 high.
    """
    reg_CMH1 = Reg(default_size, []
            
    )
    """Capture compare 0 high.
    """
    reg_CMH0 = Reg(default_size, []
            
    )
    """Capture timer 3 low.
    """
    reg_CTL3 = Reg(default_size, []
            
    )
    """Capture timer 2 low.
    """
    reg_CTL2 = Reg(default_size, []
            
    )
    """Capture timer 1 low.
    """
    reg_CTL1 = Reg(default_size, []
            
    )
    """Capture timer 0 low.
    """
    reg_CTL0 = Reg(default_size, []
            
    )
    """Capture compare 2 low.
    """
    reg_CML2 = Reg(default_size, []
            
    )
    """Capture compare 1 low.
    """
    reg_CML1 = Reg(default_size, []
            
    )
    """Capture compare 0 low.
    """
    reg_CML0 = Reg(default_size, []
            
    )
    """Interrupt enable 0.
    """
    reg_IEN0 = Reg(default_size,
        [    
            BF("EA", 7, 7),
            BF("EAD", 6, 6),
            BF("ES1", 5, 5),
            BF("ES0", 4, 4),
            BF("ET1", 3, 3),
            BF("EX1", 2, 2),
            BF("ET0", 1, 1),
            BF("EX0", 0, 0),
        ]    
            
    )
    """Interrupt enable 1.
    """
    reg_IEN1 = Reg(default_size,
        [    
            BF("ET2", 7, 7),
            BF("ECM2", 6, 6),
            BF("ECM1", 5, 5),
            BF("ECM0", 4, 4),
            BF("ECT3", 3, 3),
            BF("ECT2", 2, 2),
            BF("ECT1", 1, 1),
            BF("ECT0", 0, 0),
        ]    
            
    )
    """Interrupt priority 0.
    """
    reg_IP0 = Reg(default_size,
        [    
            BF("PAD", 6, 6),
            BF("PS1", 5, 5),
            BF("PS0", 4, 4),
            BF("PT1", 3, 3),
            BF("PX1", 2, 2),
            BF("PT0", 1, 1),
            BF("PX0", 0, 0),
        ]    
            
    )
    """Interrupt priority 1.
    """
    reg_IP1 = Reg(default_size,
        [    
            BF("PT2", 7, 7),
            BF("PCM2", 6, 6),
            BF("PCM1", 5, 5),
            BF("PCM0", 4, 4),
            BF("PCT3", 3, 3),
            BF("PCT2", 2, 2),
            BF("PCT1", 1, 1),
            BF("PCT0", 0, 0),
        ]    
            
    )
    """Port 5.
    """
    reg_P5 = Reg(default_size, []
        , flags = Reg.WRITEONLY    
    )
    """Port 5.
    """
    reg_P5_i = Reg(default_size, []
        , flags = Reg.READONLY    
    )
    """Port 4.
    """
    reg_P4 = Reg(default_size, []
        , flags = Reg.WRITEONLY
        , default = "11111111"    
    )
    """Port 4.
    """
    reg_P4_i = Reg(default_size, []
        , flags = Reg.READONLY    
    )
    """Port 3.
    """
    reg_P3 = Reg(default_size, []
        , flags = Reg.WRITEONLY
        , default = "11111111"    
    )
    """Port 3.
    """
    reg_P3_i = Reg(default_size, []
        , flags = Reg.READONLY    
    )
    """Port 2.
    """
    reg_P2 = Reg(default_size, []
        , flags = Reg.WRITEONLY
        , default = "11111111"    
    )
    """Port 2.
    """
    reg_P2_i = Reg(default_size, []
        , flags = Reg.READONLY    
    )
    """Port 1.
    """
    reg_P1 = Reg(default_size, []
        , flags = Reg.WRITEONLY
        , default = "11111111"    
    )
    """Port 1.
    """
    reg_P1_i = Reg(default_size, []
        , flags = Reg.READONLY    
    )
    """Port 0.
    """
    reg_P0 = Reg(default_size, []
        , flags = Reg.WRITEONLY| Reg.VOLATILE
        , default = "11111111"    
    )
    """Port 0.
    """
    reg_P0_i = Reg(default_size, []
        , flags = Reg.READONLY    
    )
    """Power control.
    """
    reg_PCON = Reg(default_size,
        [    
            BF("SMOD", 7, 7),
            BF("WLE", 4, 4),
            BF("GF1", 3, 3),
            BF("GF0", 2, 2),
            BF("PD", 1, 1),
            BF("IDL", 0, 0),
        ]    
            
    )
    """PWM prescaler.
    """
    reg_PWMP = Reg(default_size, []
            
    )
    """PWM register 1.
    """
    reg_PWM1 = Reg(default_size, []
            
    )
    """PWM register 0.
    """
    reg_PWM0 = Reg(default_size, []
            
    )
    """Reset/toggle enable.
    """
    reg_RTE = Reg(default_size,
        [    
            BF("TP47", 7, 7),
            BF("TP46", 6, 6),
            BF("RP45", 5, 5),
            BF("RP44", 4, 4),
            BF("RP43", 3, 3),
            BF("RP42", 2, 2),
            BF("RP41", 1, 1),
            BF("RP40", 0, 0),
        ]    
            
    )
    """Serial 0 data buffer. When written, triggers a selection event.
    """
    reg_S0BUF = Reg(default_size, []
        , flags = Reg.WRITEONLY| Reg.VOLATILE    
    )
    """Serial 0 data buffer. When read, triggers an event.
    """
    reg_S0BUF_r = Reg(default_size, []
        , flags = Reg.READONLY| Reg.VOLATILE    
    )
    """Serial 0 control.
    """
    reg_S0CON = Reg(default_size,
        [    
            BF("SM0", 7, 7),
            BF("SM1", 6, 6),
            BF("SM2", 5, 5),
            BF("REN", 4, 4),
            BF("TB8", 3, 3),
            BF("RB8", 2, 2, flags = BF.READONLY),
            BF("TI", 1, 1, flags = BF.W0C),
            BF("RI", 0, 0, flags = BF.W0C),
        ]    
        , flags = Reg.VOLATILE    
    )
    """Serial 1 addr.
    """
    reg_S1ADR = Reg(default_size,
        [    
            BF("SLADR", 7, 1),
            BF("GC", 0, 0),
        ]    
            
    )
    """Serial 1 data.
    """
    reg_S1DAT = Reg(default_size, []
        , flags = Reg.WRITEONLY    
    )
    """Serial 1 data read shadow
    """
    reg_S1DAT_r = Reg(default_size, []
        , flags = Reg.READONLY    
    )
    """Serial 1 status.
    """
    reg_S1STA = Reg(default_size, []
        , flags = Reg.READONLY    
    )
    """Serial 1 control.
    """
    reg_S1CON = Reg(default_size,
        [    
            BF("CR2", 7, 7),
            BF("ENS1", 6, 6),
            BF("STA", 5, 5),
            BF("STO", 4, 4),
            BF("SI", 3, 3, flags = BF.W0C),
            BF("AA", 2, 2),
            BF("CR1", 1, 1),
            BF("CR0", 0, 0),
        ]    
        , flags = Reg.VOLATILE    
    )
    """Set enable.
    """
    reg_STE = Reg(default_size,
        [    
            BF("TG47", 7, 7),
            BF("TG46", 6, 6),
            BF("SP45", 5, 5),
            BF("SP44", 4, 4),
            BF("SP43", 3, 3),
            BF("SP42", 2, 2),
            BF("SP41", 1, 1),
            BF("SP40", 0, 0),
        ]    
            
    )
    """Timer high 1.
    """
    reg_TH1 = Reg(default_size, []
        , flags = Reg.WRITEONLY| Reg.VOLATILE    
    )
    """Timer high 1.
    """
    reg_TH1_r = Reg(default_size, []
        , flags = Reg.READONLY| Reg.VOLATILE    
    )
    """Timer high 0.
    """
    reg_TH0 = Reg(default_size, []
        , flags = Reg.WRITEONLY| Reg.VOLATILE    
    )
    """Timer high 0.
    """
    reg_TH0_r = Reg(default_size, []
        , flags = Reg.READONLY| Reg.VOLATILE    
    )
    """Timer low 1.
    """
    reg_TL1 = Reg(default_size, []
        , flags = Reg.WRITEONLY| Reg.VOLATILE    
    )
    """Timer low 1.
    """
    reg_TL1_r = Reg(default_size, []
        , flags = Reg.READONLY| Reg.VOLATILE    
    )
    """Timer low 0.
    """
    reg_TL0 = Reg(default_size, []
        , flags = Reg.WRITEONLY| Reg.VOLATILE    
    )
    """Timer low 0.
    """
    reg_TL0_r = Reg(default_size, []
        , flags = Reg.READONLY| Reg.VOLATILE    
    )
    """Timer high 2.
    """
    reg_TMH2 = Reg(default_size, []
            
    )
    """Timer low 2.
    """
    reg_TML2 = Reg(default_size, []
            
    )
    """Timer mode.
    """
    reg_TMOD = Reg(default_size,
        [    
            BF("GATE1", 7, 7),
            BF("CT1", 6, 6),
            BF("MOD1", 5, 4),
            BF("GATE0", 3, 3),
            BF("CT0", 2, 2),
            BF("MOD0", 1, 0),
        ]    
            
    )
    """Timer control config flags
    """
    reg_TCON = Reg(default_size,
        [    
            BF("TF1", 7, 7, flags = BF.W0C),
            BF("TR1", 6, 6),
            BF("TF0", 5, 5, flags = BF.W0C),
            BF("TR0", 4, 4),
            BF("IE1", 3, 3, flags = BF.READONLY),
            BF("IT1", 2, 2),
            BF("IE0", 1, 1, flags = BF.READONLY),
            BF("IT0", 0, 0),
        ]    
        , flags = Reg.VOLATILE    
    )
    """Timer 2 control.
    """
    reg_TM2CON = Reg(default_size,
        [    
            BF("T2IS1", 7, 7),
            BF("T2IS0", 6, 6),
            BF("T2ER", 5, 5),
            BF("T2B0", 4, 4),
            BF("T2P1", 3, 3),
            BF("T2P0", 2, 2),
            BF("T2MS1", 1, 1),
            BF("T2MS0", 0, 0),
        ]    
            
    )
    """Timer 2 int flag reg.
    """
    reg_TM2IR = Reg(default_size,
        [    
            BF("T20V", 7, 7),
            BF("CMI2", 6, 6),
            BF("CMI1", 5, 5),
            BF("CMI0", 4, 4),
            BF("CTI3", 3, 3),
            BF("CTI2", 2, 2),
            BF("CTI1", 1, 1),
            BF("CTI0", 0, 0),
        ]    
            
    )
    """Timer 3.
    """
    reg_T3 = Reg(default_size, []
            
    )

    # Address mapping:
    register_map = {
        (0xC6, "RO") : [ 'ADCH', reg_ADCH ],
        (0xC5, "RW") : [ 'ADCON', reg_ADCON ],
        (0xEB, "RW") : [ 'CTCON', reg_CTCON ],
        (0xCF, "RW") : [ 'CTH3', reg_CTH3 ],
        (0xCE, "RW") : [ 'CTH2', reg_CTH2 ],
        (0xCD, "RW") : [ 'CTH1', reg_CTH1 ],
        (0xCC, "RW") : [ 'CTH0', reg_CTH0 ],
        (0xCB, "RW") : [ 'CMH2', reg_CMH2 ],
        (0xCA, "RW") : [ 'CMH1', reg_CMH1 ],
        (0xC9, "RW") : [ 'CMH0', reg_CMH0 ],
        (0xAF, "RW") : [ 'CTL3', reg_CTL3 ],
        (0xAE, "RW") : [ 'CTL2', reg_CTL2 ],
        (0xAD, "RW") : [ 'CTL1', reg_CTL1 ],
        (0xAC, "RW") : [ 'CTL0', reg_CTL0 ],
        (0xAB, "RW") : [ 'CML2', reg_CML2 ],
        (0xAA, "RW") : [ 'CML1', reg_CML1 ],
        (0xA9, "RW") : [ 'CML0', reg_CML0 ],
        (0xA8, "RW") : [ 'IEN0', reg_IEN0 ],
        (0xE8, "RW") : [ 'IEN1', reg_IEN1 ],
        (0xB8, "RW") : [ 'IP0', reg_IP0 ],
        (0xF8, "RW") : [ 'IP1', reg_IP1 ],
        (0xC4, "WO") : [ 'P5', reg_P5 ],
        (0xC4, "RO") : [ 'P5_i', reg_P5_i ],
        (0xC0, "WO") : [ 'P4', reg_P4 ],
        (0xC0, "RO") : [ 'P4_i', reg_P4_i ],
        (0xB0, "WO") : [ 'P3', reg_P3 ],
        (0xB0, "RO") : [ 'P3_i', reg_P3_i ],
        (0xA0, "WO") : [ 'P2', reg_P2 ],
        (0xA0, "RO") : [ 'P2_i', reg_P2_i ],
        (0x90, "WO") : [ 'P1', reg_P1 ],
        (0x90, "RO") : [ 'P1_i', reg_P1_i ],
        (0x80, "WO") : [ 'P0', reg_P0 ],
        (0x80, "RO") : [ 'P0_i', reg_P0_i ],
        (0x87, "RW") : [ 'PCON', reg_PCON ],
        (0xFE, "RW") : [ 'PWMP', reg_PWMP ],
        (0xFD, "RW") : [ 'PWM1', reg_PWM1 ],
        (0xFC, "RW") : [ 'PWM0', reg_PWM0 ],
        (0xEF, "RW") : [ 'RTE', reg_RTE ],
        (0x99, "WO") : [ 'S0BUF', reg_S0BUF ],
        (0x99, "RO") : [ 'S0BUF_r', reg_S0BUF_r ],
        (0x98, "RW") : [ 'S0CON', reg_S0CON ],
        (0xDB, "RW") : [ 'S1ADR', reg_S1ADR ],
        (0xDA, "WO") : [ 'S1DAT', reg_S1DAT ],
        (0xDA, "RO") : [ 'S1DAT_r', reg_S1DAT_r ],
        (0xD9, "RO") : [ 'S1STA', reg_S1STA ],
        (0xD8, "RW") : [ 'S1CON', reg_S1CON ],
        (0xEE, "RW") : [ 'STE', reg_STE ],
        (0x8D, "WO") : [ 'TH1', reg_TH1 ],
        (0x8D, "RO") : [ 'TH1_r', reg_TH1_r ],
        (0x8C, "WO") : [ 'TH0', reg_TH0 ],
        (0x8C, "RO") : [ 'TH0_r', reg_TH0_r ],
        (0x8B, "WO") : [ 'TL1', reg_TL1 ],
        (0x8B, "RO") : [ 'TL1_r', reg_TL1_r ],
        (0x8A, "WO") : [ 'TL0', reg_TL0 ],
        (0x8A, "RO") : [ 'TL0_r', reg_TL0_r ],
        (0xED, "RW") : [ 'TMH2', reg_TMH2 ],
        (0xEC, "RW") : [ 'TML2', reg_TML2 ],
        (0x89, "RW") : [ 'TMOD', reg_TMOD ],
        (0x88, "RW") : [ 'TCON', reg_TCON ],
        (0xEA, "RW") : [ 'TM2CON', reg_TM2CON ],
        (0xC8, "RW") : [ 'TM2IR', reg_TM2IR ],
        (0xFF, "RW") : [ 'T3', reg_T3 ],
    }

################################################################################# Generated file, editing void

# Device '8XC552'
class Device_nxp_8xc552(mmr.DeviceClass):
    pass

############################################################################
