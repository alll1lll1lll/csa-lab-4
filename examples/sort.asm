.section .data
.org 0x10000
array:    .word 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
buf_done: .word 0
buf_pos:  .word 0
out_buf:  .word 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
space:    .string " "

.section .text
.org 0x0008
.word irq_handler

.org 0x0100
_start:
wait_loop:
    lui t0, 0x0010
    addi t0, t0, 64
    lw t1, 0(t0)
    beq t1, zero, wait_loop

sort_outer:
    add t0, zero, zero
    lui a0, 0x0010
sort_inner:
    lw t1, 0(a0)
    beq t1, zero, check_swap
    lw t2, 4(a0)
    beq t2, zero, check_swap
    ble t1, t2, no_swap
    sw t2, 0(a0)
    sw t1, 4(a0)
    addi t0, zero, 1
no_swap:
    addi a0, a0, 4
    beq zero, zero, sort_inner
check_swap:
    bne t0, zero, sort_outer

print_arr:
    lui s0, 0x0010
print_loop:
    lw a0, 0(s0)
    beq a0, zero, end
    lui a1, 0x0010
    addi a1, a1, 72
    jal ra, itoa
    lui a0, 0x0010
    addi a0, a0, 72
    jal ra, print_string
    lui a0, 0x0010
    addi a0, a0, 112
    jal ra, print_string
    addi s0, s0, 4
    beq zero, zero, print_loop
end:
    halt

irq_handler:
    addi sp, sp, -20
    sw t0, 16(sp)
    sw t1, 12(sp)
    sw t2, 8(sp)
    sw t3, 4(sp)
    sw t4, 0(sp)

    lui t0, 0x00FF
    lw t1, 4(t0)
    addi t2, zero, 1
    sw t2, 16(t0)

    beq t1, zero, isr_done

    addi t1, t1, -48

    lui t2, 0x0010
    addi t2, t2, 68
    lw t3, 0(t2)
    lui t4, 0x0010
    add t4, t4, t3
    sw t1, 0(t4)
    addi t3, t3, 4
    sw t3, 0(t2)
    beq zero, zero, isr_end

isr_done:
    lui t2, 0x0010
    addi t2, t2, 64
    addi t3, zero, 1
    sw t3, 0(t2)

isr_end:
    lw t0, 16(sp)
    lw t1, 12(sp)
    lw t2, 8(sp)
    lw t3, 4(sp)
    lw t4, 0(sp)
    addi sp, sp, 20
    iret

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
