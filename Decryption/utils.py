import numpy as np
import copy
import hashlib

def yates_shuffle(plain, key):
    p = copy.copy(plain)
    n = len(p)
    p.insert(0, 0)
    bit_len = len(bin(int(str(n), 10))) - 1
    key = '0' + key
    key_count = 1
    for i in range(n, 1, -1):
        num = int('0b' + key[key_count:key_count + bit_len], 2) + 1
        index = num % i + 1
        temp = p[i]
        p[i] = p[index]
        p[index] = temp
        key_count = key_count + 1
    del p[0]
    return p

def BitStream_Compress(origin_bits,L_fix):
    '''
    函数说明：压缩比特流
    输入:origin_bits(原始比特流),L_fix(定长编码参数)
    输出:compress_bits(压缩比特流)
    '''
    origin_bits = origin_bits.astype(np.int8)
    len_bits = len(origin_bits)#统计原始比特流的长度
    ori_t = 0                  #计数，已遍历原始比特流的数目
    compress_bit = ''          #用来记录压缩比特流
    comp_t = 0                 #计数，压缩比特流的长度

    while ori_t<len_bits:
        bit = origin_bits[ori_t]
        L = 0           #用来记录相同比特的个数
        comp_L = ''     #用来记录一串相同字符的压缩比特流
        #统计相同比特的个数
        for i in range(ori_t,len_bits):
            if origin_bits[i] == bit:
                L+=1
            else:
                break
        #相同比特流长度小于4
        if L<4:
            comp_L = comp_L+'0'
            if ori_t + L_fix<=len_bits:
                for j in range(ori_t,ori_t+L_fix):
                    comp_L = comp_L + str(origin_bits[j])
                L = L_fix
            else:
                re = len_bits - ori_t
                for j in range(ori_t,ori_t+re):
                    comp_L = comp_L + str(origin_bits[j])
                L = re
        #相同比特流长度大于等于4
        else:
            L_pre = int(np.log2(L))#前缀标记位
            for j in range(L_pre-1):
                comp_L = comp_L + '1'
            comp_L = comp_L + '0'#前缀标记：1…10（L_pre位)
            l = L - 2**(L_pre)   #剩余比特流
            bin_l = bin(int(l))[2:]#转换成二进制
            len_l = len(bin_l)
            len_zero = L_pre-len_l
            for j in range(len_zero):
                comp_L = comp_L + '0'
            comp_L = comp_L + bin_l
            comp_L =  comp_L + str(bit)
        #记录压缩的相同比特流
        len_L = len(comp_L)
        compress_bit = compress_bit + comp_L
        comp_t = comp_t + len_L
        ori_t = ori_t + L
    
    return compress_bit

'''
 Oluwadamilola (Damie) Martins Ogunbiyi
 University of Maryland, College Park
 Department of Electrical and Computer Engineering
 Communications and Signal Processing
 22-March-2010
 Copyright 2009-2010 Black Ace of Diamonds.
'''
def zigzag(ln):
    [num_rows, num_cols] = ln.shape
    out = np.zeros(num_rows*num_cols)
    cur_row = 0; cur_col = 0; cur_index = 0
    while cur_row < num_rows and cur_col < num_cols:
        if cur_row==0 and (cur_row+cur_col)%2==0 and cur_col!=(num_cols-1):
            out[cur_index] = ln[cur_row, cur_col]
            cur_col = cur_col + 1                     # move right at the top
            cur_index = cur_index + 1
        elif cur_row == (num_rows-1) and (cur_row+cur_col)%2!=0 and cur_col!=(num_cols-1):
            out[cur_index] = ln[cur_row, cur_col]
            cur_col = cur_col + 1                    # move right at the bottom                                       
            cur_index = cur_index + 1
        elif cur_col==0 and (cur_row+cur_col)%2!=0 and cur_row!=(num_rows-1):
            out[cur_index] = ln[cur_row, cur_col]
            cur_row = cur_row + 1                      # move down at the left
            cur_index = cur_index + 1
        elif cur_col==(num_cols-1) and (cur_row+cur_col)%2==0 and cur_row!=(num_rows-1):
            out[cur_index] = ln[cur_row,cur_col]
            cur_row = cur_row + 1                      # move down at the right
            cur_index = cur_index + 1
        elif cur_col!=0 and cur_row!=(num_rows-1) and (cur_row+cur_col)%2!=0:
            out[cur_index] = ln[cur_row, cur_col]
            cur_row = cur_row + 1; cur_col = cur_col - 1 # move diagonally left down
            cur_index = cur_index + 1
        elif cur_row!=0 and cur_col!=(num_cols-1) and (cur_row+cur_col)%2==0:
            out[cur_index] = ln[cur_row, cur_col]
            cur_row = cur_row - 1; cur_col = cur_col + 1 # move diagonally right up
            cur_index = cur_index + 1
        elif cur_row == (num_rows-1) and cur_col == (num_cols-1):
            out[num_rows*num_cols-1] = ln[num_rows-1, num_cols-1]  #obtain the bottom right elements                                                        
            break                                                  #end of the operation
    return out                                                     #terminate the operation

def invzigzag(ln, num_rows, num_cols):
    tot_elem = len(ln)
    
    # check if matrix dimensions correspond
    if tot_elem!=num_rows*num_cols:
        print('Matrix dimensions do not coincide')
        
    # Initialise the output matrix
    out = np.zeros([num_rows, num_cols])
    
    cur_row = 0; cur_col = 0; cur_index = 0
    
    while cur_index < tot_elem:
        if cur_row == 0 and (cur_row+cur_col)%2==0 and cur_col != (num_cols-1):
            out[cur_row, cur_col] = ln[cur_index]
            cur_col = cur_col + 1                   # move right at the top
            cur_index = cur_index + 1
        
        elif cur_row==(num_rows-1) and (cur_row+cur_col)%2!=0 and cur_col!=(num_cols-1):
            out[cur_row, cur_col] = ln[cur_index]
            cur_col = cur_col + 1                    # move right at the bottom
            cur_index = cur_index + 1
        
        elif cur_col==0 and (cur_row+cur_col)%2!=0 and cur_row!=(num_rows-1):
            out[cur_row,cur_col] = ln[cur_index]
            cur_row = cur_row + 1                     # move down at the left
            cur_index = cur_index + 1
            
        elif cur_col==(num_cols-1) and (cur_row+cur_col)%2==0 and cur_row!=(num_rows-1):
            out[cur_row,cur_col] = ln[cur_index]
            cur_row = cur_row + 1                     # move down at the right
            cur_index = cur_index + 1
            
        elif cur_col!=0 and cur_row!=(num_rows-1) and (cur_row+cur_col)%2!=0:
            out[cur_row,cur_col] = ln[cur_index]
            cur_row = cur_row + 1                      # move diagonally left down
            cur_col = cur_col - 1
            cur_index = cur_index + 1
        
        elif cur_row!=0 and cur_col != (num_cols-1) and (cur_row+cur_col)%2==0:
            out[cur_row, cur_col] = ln[cur_index]
            cur_row = cur_row - 1
            cur_col = cur_col + 1                      # move diagonally right down
            cur_index = cur_index + 1
        
        elif cur_index == tot_elem-1:
            out[num_rows-1,num_cols-1] = ln[tot_elem-1]
            break
    return out

def generate_keys_ada(data,control_length,user_key):
    hash = hashlib.sha256()
    hash.update(bytes(str(data), encoding='utf-8'))
    init_key = hash.hexdigest()#16进制哈希值
    hash.update(bytes(str(user_key), encoding='utf-8'))
    user_key = hash.hexdigest()#16进制哈希值
    temp = ''
    for i in range(0, len(init_key), 2):
        # 将两位十六进制数转换为整数
        int1 = int(init_key[i:i+2], 16)
        int2 = int(user_key[i:i+2], 16)
        # 进行异或操作，并转换回两位十六进制字符串
        temp += format(int1 ^ int2, '02x')
    keys=''
    while len(keys) < control_length + 500:
        hash.update(bytes(temp, encoding='utf-8'))
        temp = hash.hexdigest()
        for j in range(0, len(temp), 2):
            bin_str = bin(int(temp[j:j + 2], 16))
            keys = keys + bin_str[2:]
    return keys