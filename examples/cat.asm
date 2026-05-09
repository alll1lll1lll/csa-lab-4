.section .text
.org 0x0008
.word hw_handler
.org 0x0100
_start:
wait_loop:
    beq zero, zero, wait_loop
hw_handler:
    lui t0, 0x00FF
    lw t1, 4(t0)
    beq t1, zero, eof
    sw t1, 8(t0)
    addi t2, zero, 1
    sw t2, 16(t0)
    iret
eof:
    halt
