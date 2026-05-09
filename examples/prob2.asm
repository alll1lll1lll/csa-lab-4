.section .data
.org 0x10000
msg: .string "Difference: "
.org 0x10040
out_buf: .word 0,0,0,0,0,0,0,0,0,0

.section .text
.org 0x0100
_start:
    add a1, zero, zero
    add a2, zero, zero
    addi a3, zero, 1
    addi t3, zero, 101

loop:
    beq a3, t3, calc
    add a1, a1, a3
    mul t4, a3, a3
    add a2, a2, t4
    addi a3, a3, 1
    beq zero, zero, loop

calc:
    mul a1, a1, a1
    sub a0, a1, a2

    lui a1, 0x0010
    addi a1, a1, 64
    jal ra, itoa

    lui a0, 0x0010
    jal ra, print_string

    lui a0, 0x0010
    addi a0, a0, 64
    jal ra, print_string
    halt

itoa:
    add t4, zero, a1
    addi t0, zero, 10
itoa_loop:
    beq a0, zero, itoa_rev
    div t1, a0, t0
    mul t2, t1, t0
    sub t3, a0, t2
    addi t3, t3, 48
    sw t3, 0(a1)
    addi a1, a1, 4
    add a0, zero, t1
    beq zero, zero, itoa_loop
itoa_rev:
    sw zero, 0(a1)
    addi a1, a1, -4
rev_loop:
    bge t4, a1, itoa_end
    lw t1, 0(t4)
    lw t2, 0(a1)
    sw t2, 0(t4)
    sw t1, 0(a1)
    addi t4, t4, 4
    addi a1, a1, -4
    beq zero, zero, rev_loop
itoa_end:
    jalr zero, ra, 0

print_string:
    lui t1, 0x00FF
ps_loop:
    lw t2, 0(a0)
    beq t2, zero, ps_end
    sw t2, 8(t1)
    addi a0, a0, 4
    beq zero, zero, ps_loop
ps_end:
    jalr zero, ra, 0
