import numpy as np
import copy
from Decryption.utils import yates_shuffle

def dc_dec2(dc_enc,encryption_key,overDC_map,dc_pred_diff_max,dc_pred_diff_min,s=2024):
    '''
    逆预测误差平均化
    Input: dc_enc: 加密后的DC系数   encryption_key:DC加密密钥  
    overDC_map: 溢出的DC系数map  s用于固定随机数序列
    Output: dc_pred: 平均化之前的预测误差序列
    '''
    #取原始DC系数中最大值和最小值
    dc_max = max(dc_enc)-dc_pred_diff_max
    dc_min = min(dc_enc)-dc_pred_diff_min
    group_num = int(dc_max-dc_min+1)  #将DC系数划分为group_num组
    if group_num>len(dc_enc):
        group_num=len(dc_enc)
    num = int(len(dc_enc)/group_num)  #每组的DC系数个数
    np.random.seed(s)
    key_t = np.random.randint(dc_min,dc_max,size=(group_num+1)) #随机生成（1，group_num+1）的密钥序列

    #对密钥序列进行混洗 
    data = [i for i in range(0, group_num+1)]
    per_index = yates_shuffle(data,encryption_key)
    key = np.zeros_like(key_t)
    for i in range(0,group_num+1):
        key[i] = key_t[per_index[i]]
    #溢出的系数值需加回最大值/最小值，再减去随机数序列对应值
    dc_pred = np.zeros_like(dc_enc)
    used = 0
    over_dc = []
    for i in range(0,group_num):
        for j in range(0,num):
            if overDC_map[used+j]==1:
                if dc_enc[used+j]>0:
                    dc_add = dc_enc[used+j] + dc_max
                    dc_final = dc_add - key[i]
                elif dc_enc[used+j]<0:
                    dc_add = dc_enc[used+j] + dc_min
                    dc_final = dc_add - key[i]
                elif dc_enc[used+j]==0 and key[i]==dc_max:
                    dc_final = dc_max
                else:
                    dc_final = dc_min
            else:
                dc_final = dc_enc[used+j]- key[i]
            dc_pred[used+j] = dc_final
        used = used + num
    #最后不足整组数的那一组单独进行逆向操作
    final_num = len(dc_enc)-(num*group_num)
    for i in range(final_num):
        if overDC_map[used+i]==1:
            if dc_enc[used+i]>0:
                dc_add = dc_enc[used+i] + dc_max
                dc_final = dc_add - key[group_num]
            elif dc_enc[used+i]<0:
                dc_add = dc_enc[used+i] + dc_min
                dc_final = dc_add - key[group_num]
            elif dc_enc[used+i]==0 and key[group_num]==dc_max:
                dc_final = dc_max
            else:
                dc_final = dc_min
        else:
            dc_final = dc_enc[used+i]- key[group_num]
        dc_pred[used+i] = dc_final
    return dc_pred

def dc_dec1(dc_decrypt,mark_map,m,n,encryption_key):
    '''
    dc Prediction:
    Input: dc_decry:逆平均化后的DC系数预测误差,(m,n)每行每列中包含的8*8图像块
    encryption_key: DC加密密钥
    Output: dc_dec: 解密后的DC系数
    '''
    dc_matrix = np.zeros((m,n))
    t=0
    for i in range(m):
        for j in range(n):
            dc_matrix[i,j] = dc_decrypt[t]#将解密的DC系数预测误差转换为矩阵形式
            t=t+1
    #矩阵以行为单位进行置换
    data = [i for i in range(0, m)]
    shuffle_index = yates_shuffle(data, encryption_key)
    ER_dec = np.zeros_like(dc_matrix)
    for i in range(m):
        ER_dec[shuffle_index[i],:] = dc_matrix[i,:]
    #还原第一行和第一列系数值，当前预测误差值加上前一个已被还原的系数值
    ER = copy.deepcopy(ER_dec)
    for i in range(1,m):
        ER_dec[i,0] = ER[i,0] + ER_dec[i-1,0]
    for j in range(1,n):
        ER_dec[0,j] = ER[0,j] + ER_dec[0,j-1]
    
    used = 0
    for i in range(1,m):
        for j in range(1,n):
            dc_up = ER_dec[i-1,j]#取当前待还原系数上面的DC系数值
            dc_left = ER_dec[i,j-1]#取当前待还原系数左侧的DC系数值
            if mark_map[used]==0:#若标记图相应位置为0则表示选取了上面的系数作为预测值，反之则选择了左侧系数值
                dc_pred = dc_up
            else:
                dc_pred = dc_left
            ER_dec[i,j] = ER_dec[i,j] + dc_pred#将当前预测误差值加上预测值即可得到原始的系数值
            used = used + 1
    #得到最终解密的（1，m*n）DC系数矩阵
    dc_dec = []
    for i in range(m):
        for j in range(n):
            dc_dec.append(ER_dec[i,j])
    
    return dc_dec
    