; fast_hash.asm - High-performance hash function for critical path
; NASM syntax for x86_64

section .text
global fast_hash_assembly
global base62_encode

; uint64_t fast_hash_assembly(const char* str, size_t len)
; Optimized FNV-1a hash in assembly
fast_hash_assembly:
    ; rdi = str pointer
    ; rsi = length
    push rbx
    
    mov rax, 0xcbf29ce484222325  ; FNV offset basis
    xor rcx, rcx                  ; counter = 0
    
    .hash_loop:
        cmp rcx, rsi
        jge .done
        
        movzx rbx, byte [rdi + rcx]  ; load byte
        xor rax, rbx                  ; xor with byte
        imul rax, 0x100000001b3      ; multiply by FNV prime
        
        inc rcx
        jmp .hash_loop
    
    .done:
        pop rbx
        ret

; void base62_encode(uint64_t num, char* buffer, int length)
; Convert number to base62 string
base62_encode:
    ; rdi = num
    ; rsi = buffer
    ; rdx = length
    
    push r12
    push r13
    
    mov r12, rsi                    ; buffer pointer
    mov r13, rdx                    ; length
    mov rcx, rdx                    ; position counter
    dec rcx                         ; start from end
    
    ; Base62 character set (in data section)
    extern base62_chars
    
    .encode_loop:
        cmp rcx, 0
        jl .done
        
        mov rax, rdi
        xor rdx, rdx
        mov rbx, 62
        div rbx                     ; rax = quotient, rdx = remainder
        
        mov rdi, rax                ; num = quotient for next iteration
        
        ; Get character from lookup table
        lea rbx, [base62_chars]
        mov al, byte [rbx + rdx]
        mov byte [r12 + rcx], al    ; store character
        
        dec rcx
        jmp .encode_loop
    
    .done:
        ; Null terminate
        mov byte [r12 + r13], 0
        pop r13
        pop r12
        ret

section .data
base62_chars:
    db '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
