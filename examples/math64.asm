.section .text
.org 0x0100
_start:
    lui t0, 0x0001
    addi t1, zero, -1
    lui t2, 0x0002
    addi t3, zero, 2

    add s0, t1, t3
    blo s0, t1, carry
    add s1, t0, t2
    beq zero, zero, end
carry:
    add s1, t0, t2
    addi s1, s1, 1
end:
    halt
