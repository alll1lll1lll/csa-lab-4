.section .data
.org 0x10000
n:   .word 5
buf: .word 0, 0, 0, 0, 0, 0, 0, 0

.section .text
.org 0x0100
_start:
    lui  a0, 0x10
    lw   a0, 0(a0)

    addi s0, zero, 1
    add  t2, zero, a0
fact_loop:
    beq  t2, zero, fact_done
    mul  s0, s0, t2
    addi t2, t2, -1
    beq  zero, zero, fact_loop
fact_done:

    lui  a1, 0x10
    addi a1, a1, 4
    add  t4, zero, a1
    add  a0, zero, s0
    addi t0, zero, 10

    bne  a0, zero, itoa_loop
    addi t3, zero, 48
    sw   t3, 0(a1)
    addi a1, a1, 4
    beq  zero, zero, itoa_rev

itoa_loop:
    beq  a0, zero, itoa_rev
    div  t1, a0, t0
    mul  t2, t1, t0
    sub  t3, a0, t2
    addi t3, t3, 48
    sw   t3, 0(a1)
    addi a1, a1, 4
    add  a0, zero, t1
    beq  zero, zero, itoa_loop

itoa_rev:
    sw   zero, 0(a1)
    addi a1, a1, -4

rev_loop:
    bge  t4, a1, print_start
    lw   t1, 0(t4)
    lw   t2, 0(a1)
    sw   t2, 0(t4)
    sw   t1, 0(a1)
    addi t4, t4, 4
    addi a1, a1, -4
    beq  zero, zero, rev_loop

print_start:
    lui  a0, 0x10
    addi a0, a0, 4
    lui  t1, 0x00FF

print_loop:
    lw   t2, 0(a0)
    beq  t2, zero, print_nl
    sw   t2, 8(t1)
    addi a0, a0, 4
    beq  zero, zero, print_loop

print_nl:
    addi t3, zero, 10
    sw   t3, 8(t1)
    halt
