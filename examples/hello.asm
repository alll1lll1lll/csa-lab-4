.section .data
.org 0x10000
msg: .string "hello world\n"

.section .text
.org 0x0100
_start:
    lui a0, 0x0010
    lui t1, 0x00FF
loop:
    lw t2, 0(a0)
    beq t2, zero, end
    sw t2, 8(t1)
    addi a0, a0, 4
    beq zero, zero, loop
end:
    halt
