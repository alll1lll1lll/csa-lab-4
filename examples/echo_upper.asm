.section .data
.org 0x10000
done:   .word 0         ; set to 1 by ISR when '\0' received

.section .text

; Interrupt vector table
.org 0x0000
.word 0                 ; 0x0000 - unused
.word 0                 ; 0x0004 - software trap vector (unused)
.word hw_isr            ; 0x0008 - hardware interrupt vector

.org 0x0100
_start:
    lui s0, 0x10        ; s0 = 0x10000 (done flag address)

main_loop:
    lw t0, 0(s0)        ; check done flag
    bne t0, zero, halt_prog
    beq zero, zero, main_loop

halt_prog:
    halt

; Hardware interrupt service routine
; Reads one char from MMIO_IN_DATA, converts a-z → A-Z, outputs it.
; On '\0': sets done flag and returns.
hw_isr:
    addi sp, sp, -16
    sw t0, 12(sp)
    sw t1, 8(sp)
    sw t2, 4(sp)
    sw s0, 0(sp)

    lui t0, 0xFF        ; t0 = 0xFF000 (MMIO base)
    lw t1, 4(t0)        ; peek MMIO_IN_DATA

    addi t2, zero, 1
    sw t2, 16(t0)       ; MMIO_IRQ_ACK — pop from queue

    beq t1, zero, set_done

    ; Convert lowercase to uppercase if 'a' <= t1 <= 'z'
    addi t2, zero, 97   ; 'a'
    blt t1, t2, do_output
    addi t2, zero, 122  ; 'z'
    bgt t1, t2, do_output
    addi t1, t1, -32    ; to uppercase

do_output:
    sw t1, 8(t0)        ; MMIO_OUT_DATA

isr_return:
    lw s0, 0(sp)
    lw t2, 4(sp)
    lw t1, 8(sp)
    lw t0, 12(sp)
    addi sp, sp, 16
    iret

set_done:
    lui s0, 0x10        ; s0 = 0x10000 (done flag)
    addi t1, zero, 1
    sw t1, 0(s0)        ; done = 1
    beq zero, zero, isr_return
