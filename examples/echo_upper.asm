.section .data
.org 0x10000
done:   .word 0

.section .text

.org 0x0000
.word 0
.word 0
.word hw_isr

.org 0x0100
_start:
    lui s0, 0x10

main_loop:
    lw t0, 0(s0)
    bne t0, zero, halt_prog
    beq zero, zero, main_loop

halt_prog:
    halt

hw_isr:
    addi sp, sp, -16
    sw t0, 12(sp)
    sw t1, 8(sp)
    sw t2, 4(sp)
    sw s0, 0(sp)

    lui t0, 0xFF
    lw t1, 4(t0)

    addi t2, zero, 1
    sw t2, 16(t0)

    beq t1, zero, set_done

    addi t2, zero, 97
    blt t1, t2, do_output
    addi t2, zero, 122
    bgt t1, t2, do_output
    addi t1, t1, -32

do_output:
    sw t1, 8(t0)

isr_return:
    lw s0, 0(sp)
    lw t2, 4(sp)
    lw t1, 8(sp)
    lw t0, 12(sp)
    addi sp, sp, 16
    iret

set_done:
    lui s0, 0x10
    addi t1, zero, 1
    sw t1, 0(s0)
    beq zero, zero, isr_return
