.section .data
.org 0x10000
prompt:    .string "What is your name?\n"
hello_pre: .string "Hello, "
hello_suf: .string "!\n"
buf_done:  .word 0
buf_pos:   .word 0
name_buf:  .word 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

.section .text
.org 0x0008
.word irq_handler

.org 0x0100
_start:
    lui a0, 0x0010
    jal ra, print_string

wait_loop:
    lui t0, 0x0010
    addi t0, t0, 124
    lw t1, 0(t0)
    beq t1, zero, wait_loop

    lui a0, 0x0010
    addi a0, a0, 80
    jal ra, print_string

    lui a0, 0x0010
    addi a0, a0, 132
    jal ra, print_string

    lui a0, 0x0010
    addi a0, a0, 112
    jal ra, print_string

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

    addi t3, zero, 10
    beq t1, t3, irq_done
    beq t1, zero, irq_done

    lui t2, 0x0010
    addi t2, t2, 128
    lw t3, 0(t2)
    lui t4, 0x0010
    addi t4, t4, 132
    add t4, t4, t3
    sw t1, 0(t4)
    addi t3, t3, 4
    sw t3, 0(t2)
    beq zero, zero, irq_end

irq_done:
    lui t2, 0x0010
    addi t2, t2, 128
    lw t3, 0(t2)
    lui t4, 0x0010
    addi t4, t4, 132
    add t4, t4, t3
    sw zero, 0(t4)

    lui t2, 0x0010
    addi t2, t2, 124
    addi t3, zero, 1
    sw t3, 0(t2)

irq_end:
    lw t0, 16(sp)
    lw t1, 12(sp)
    lw t2, 8(sp)
    lw t3, 4(sp)
    lw t4, 0(sp)
    addi sp, sp, 20
    iret

print_string:
    lui t0, 0x00FF
ps_loop:
    lw t1, 0(a0)
    beq t1, zero, ps_end
    sw t1, 8(t0)
    addi a0, a0, 4
    beq zero, zero, ps_loop
ps_end:
    jalr zero, ra, 0
