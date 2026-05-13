## laod plain-images and secret keys
import numpy as np
import copy
from Encryption.utils import *
from Encryption.DC_encryption import dc_enc1,dc_enc2
from Encryption.AC_encryption import ac_enc1,ac_enc2

def encrypt_each_component(dct_component,type,row,col,keys):
    block8_number  = dct_component.shape[2]
    allblock8 = dct_component
    dc_ori = np.zeros(block8_number)
    #allblock8_number = 0
    for i in range(block8_number):
        dc_ori[i] = allblock8[0][0][i]

    #生成密钥序列，使用哈希函数
    block_AC_sum = np.zeros(block8_number)
    for i in range(0,block8_number):
        AC_sum = np.sum(allblock8[:,:,i].flatten()) - allblock8[0,0,i]
        block_AC_sum[i] = AC_sum
    #DC预测加密
    m = int(row/8)
    n = int(col/8)
    #将每个块AC系数和序列输入到SHA-256哈希函数中计算哈希值，即为Key
    encryption_key = generate_keys_ada(block_AC_sum,block8_number,keys)
    ER_pred1, mark_map = dc_enc1(dc_ori,m,n,encryption_key)
    ER_pred, key_num, over_dc = dc_enc2(dc_ori,ER_pred1,encryption_key)

    max_diff = int(ER_pred.max()-ER_pred1.max())
    min_diff = int(ER_pred.min()-ER_pred1.min())
    
    assert abs(max_diff)<128 and abs(min_diff)<128
    if max_diff<0:
        max_diff_bin = '1' + bin(abs(max_diff))[2:].zfill(7)
    else:
        max_diff_bin = '0' + bin(max_diff)[2:].zfill(7)
    if min_diff<0:
        min_diff_bin = '1' + bin(abs(min_diff))[2:].zfill(7)
    else:
        min_diff_bin = '0' + bin(min_diff)[2:].zfill(7)
    
    # 块置换 Fisher-Yates Shuffle
    # for 8*8 blocks permutation  获取混洗块时的顺序索引
    # 将预测误差序列输入到SHA-256哈希函数中计算哈希值，即为Key1
    data = [i for i in range(0, block8_number)]
    encryption_key1 = generate_keys_ada(ER_pred,len(data),keys)
    p_block = yates_shuffle(data, encryption_key1)
    #p_block = data
    permuted_blocks = np.zeros_like(allblock8)
    for i in range(len(p_block)):
        permuted_blocks[:, :, i] = allblock8[:, :, p_block[i]]

    #RSV对置换（全局置换、块内置换、符号翻转
    num_nonZero = np.zeros(block8_number,dtype=np.int16)
    last_pos = np.zeros(block8_number)
    for i in range(0,block8_number):
        temp = copy.deepcopy(permuted_blocks[:,:,i])   #取出一个图像块
        temp[0,0] = 0
        nonZero_pos = np.where(temp.T.flatten()!=0)
        num_nonZero[i] = len(nonZero_pos[0])
        if len(nonZero_pos[0])==0:
            continue
        last_pos[i] = nonZero_pos[0][-1]
    
    #将每个块最后一个非零系数位置序列输入到SHA-256哈希函数中计算哈希值，即为Key2
    #将每个块中非零AC系数的数量序列输入到SHA-256哈希函数中计算哈希值，即为Key3
    # key2与key3的计算现整合进ac_enc1和ac_enc2中
    #全局置换
    allblock8_RSpermute = ac_enc1(last_pos,permuted_blocks,keys)
    #块内置换
    allblock8_ACpermute = ac_enc2(num_nonZero,allblock8_RSpermute,keys)

    bin63 = np.zeros((block8_number,63))

    for i in range(block8_number):
        temp = allblock8_ACpermute[:,:,i]
        temp_zig = zigzag(temp)
        bin63[i] = temp_zig[1:]
    encrypted_dctImage = np.zeros_like(dct_component)
    accof = -bin63
    kk = 0
    for i in range(block8_number):
        temp = np.zeros(64)
        temp[0] = ER_pred[kk]
        temp[1:] = accof[kk]
        encrypted_block = invzigzag(temp,8,8)
        encrypted_dctImage[:,:,i] = encrypted_block
        kk = kk + 1
    
    #直方图加密，将辅助信息嵌入到图像中
    overDC_map=np.zeros(block8_number,dtype=np.int16)
    overDC_map[over_dc]=1

    compress_bits = BitStream_Compress(overDC_map,2)
    #嵌入长度标记位
    bits_len = len(compress_bits)
    assert bits_len <= 65535
    bits_len = bin(bits_len)[2:]
    for i in range(16-len(bits_len)):
        bits_len = '0'+bits_len

    mark_map_string = ''
    for i in range(len(mark_map)):
        mark_map_string = mark_map_string+str(mark_map[i])
    secret = mark_map_string + max_diff_bin + min_diff_bin + bits_len + compress_bits
    
    return encrypted_dctImage, secret
