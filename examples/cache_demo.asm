.section .data
.org 0x10000
arr: .word 10, 20, 30, 40, 50, 60, 70, 80

.section .text
.org 0x0100
_start:
    lui  a0, 0x10
    addi a1, zero, 8

    addi s0, zero, 0
    addi t2, zero, 0
    lui  a0, 0x10
cold_loop:
    beq  t2, a1, cold_done
    lw   t0, 0(a0)
    add  s0, s0, t0
    addi a0, a0, 4
    addi t2, t2, 1
    beq  zero, zero, cold_loop
cold_done:

    addi s1, zero, 0
    addi t2, zero, 0
    lui  a0, 0x10
warm_loop:
    beq  t2, a1, warm_done
    lw   t0, 0(a0)
    add  s1, s1, t0
    addi a0, a0, 4
    addi t2, t2, 1
    beq  zero, zero, warm_loop
warm_done:

    halt
