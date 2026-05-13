import numpy as np
import hashlib
import copy
from Decryption.AC_decryption import ac_dec,ac_dec1
from Decryption.DC_decryption import dc_dec2,dc_dec1
from Decryption.Decompress import BitStream_DeCompress
from Decryption.utils import *


def decrypt_each_component(dct_component,secret,type,row,col,keys):

    m = int(row/8)
    n = int(col/8)
    block8_number = dct_component.shape[2]
    mark_num = (m-1)*(n-1)

    mark_map = secret[0:mark_num]#提取出DC预测过程中的map图
    #从字符串转int型np数组
    mark_map = list(mark_map)
    mark_map = np.array(mark_map).astype(np.int16)

    dc_pred_max_diff_bin = secret[mark_num:mark_num+8]
    dc_pred_min_diff_bin = secret[mark_num+8:mark_num+16]

    bits_len = secret[mark_num+16:mark_num+16+16]#标记位，储存压缩比特的长度
    bits_len = int(bits_len,base=2)

    if type == 'Cr':
        secret = secret[mark_num+16+16+bits_len:]
        mark_map = secret[0:mark_num]#提取出DC预测过程中的map图
        mark_map = list(mark_map)
        mark_map = np.array(mark_map).astype(np.int16)
        dc_pred_max_diff_bin = secret[mark_num:mark_num+8]
        dc_pred_min_diff_bin = secret[mark_num+8:mark_num+16]
        bits_len = secret[mark_num+16:mark_num+16+16]#标记位，储存压缩比特的长度
        bits_len = int(bits_len,base=2)

    compress_bits = secret[mark_num+16+16:mark_num+16+16+bits_len]
    overDC_map = BitStream_DeCompress(compress_bits,2)
    overDC_map = list(overDC_map)
    overDC_map = np.array(overDC_map).astype(np.int16)

    if dc_pred_max_diff_bin[0] == '1':
        dc_pred_diff_max = -1 * int(dc_pred_max_diff_bin[1:],base=2)
    else:
        dc_pred_diff_max = int(dc_pred_max_diff_bin[1:],base=2)

    if dc_pred_min_diff_bin[0] == '1':
        dc_pred_diff_min = -1 * int(dc_pred_min_diff_bin[1:],base=2)
    else:
        dc_pred_diff_min = int(dc_pred_min_diff_bin[1:],base=2)

    ER_pred = np.zeros(block8_number)
    bin63 = np.zeros((block8_number,63))
    #分别取出加密后的DC系数以及AC系数
    for i in range(block8_number):
        encrypted_seq = zigzag(dct_component[:,:,i])
        ER_pred[i] = encrypted_seq[0]
        bin63[i] = encrypted_seq[1:]

    accof = -bin63
    #重构加密块
    allblock8_ACpermute = np.zeros((8,8,block8_number))
    for i in range(block8_number):
        temp = np.insert(accof[i],0,ER_pred[i])
        allblock8_ACpermute[:,:,i] = invzigzag(temp,8,8)

    #逆RSV对置换（逆全局置换、逆块内置换）
    num_nonZero = np.zeros(block8_number,dtype=np.int16)
    for i in range(block8_number):
        temp = copy.deepcopy(allblock8_ACpermute[:,:,i])   #取出一个图像块
        temp[0,0] = 0
        nonZero_pos = np.where(temp.T.flatten()!=0)
        num_nonZero[i] = len(nonZero_pos[0])
    #将每个块中非零AC系数的数量序列输入到SHA-256哈希函数中计算哈希值，即为Key3
    #逆块内置换
    allblock8_RSpermute = ac_dec(num_nonZero,allblock8_ACpermute,keys)

    last_pos = np.zeros(block8_number)
    for i in range(block8_number):
        temp = copy.deepcopy(allblock8_RSpermute[:,:,i])
        temp[0,0] = 0
        nonZero_pos = np.where(temp.T.flatten()!=0)
        if len(nonZero_pos[0])==0:
            continue
        last_pos[i] = nonZero_pos[0][-1]
    #将每个块最后一个非零系数位置序列输入到SHA-256哈希函数中计算哈希值，即为Key2
    permuted_blocks = ac_dec1(last_pos,allblock8_RSpermute,keys)

    # 逆块置换 Fisher-Yates Shuffle
    # for 8*8 blocks permutation  获取混洗块时的顺序索引
    # 将加密后的DC系数输入到SHA-256哈希函数中计算哈希值，即为Key1
    data = [i for i in range(0, block8_number)]
    encryption_key1 = generate_keys_ada(ER_pred,len(data),keys)
    p_block = yates_shuffle(data, encryption_key1)

    allblock8 = np.zeros_like(permuted_blocks)
    for i in range(len(p_block)):
        allblock8[:,:,p_block[i]] = permuted_blocks[:,:,i]

    # 逆DC加密
    #生成密钥序列，使用哈希函数
    block_AC_sum = np.zeros(block8_number)
    for i in range(0,block8_number):
        AC_sum = np.sum(allblock8[:,:,i].flatten()) - allblock8[0,0,i]
        block_AC_sum[i] = AC_sum
    #将每个块AC系数和序列输入到SHA-256哈希函数中计算哈希值，即为Key
    encryption_key = generate_keys_ada(block_AC_sum,block8_number,keys)
    #overdc = np.where(overDC_map==1)[0]
    dc_decrypt = dc_dec2(ER_pred,encryption_key,overDC_map,dc_pred_diff_max,dc_pred_diff_min)
    dc_recover = dc_dec1(dc_decrypt,mark_map,int(row/8),int(col/8),encryption_key)

    for i in range(block8_number):
        allblock8[0,0,i] = dc_recover[i]

    return allblock8