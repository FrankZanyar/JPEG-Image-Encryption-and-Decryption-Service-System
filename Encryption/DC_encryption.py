import numpy as np
import copy
from Encryption.utils import yates_shuffle
def dc_enc1(dc,m,n,encryption_keys):
    dc_mat = dc.reshape([m,n])
    dc_prediction = copy.deepcopy(dc_mat)
    ER = copy.deepcopy(dc_mat)
    mark_map = []
    mark_0 = 0
    mark_1 = 0

    for i in range(1,m):
        for j in range(1,n):
            dc_up = dc_mat[i-1,j]       #取当前待预测系数上面的DC系数值
            dc_left = dc_mat[i,j-1]     #取当前待预测系数左侧的DC系数值
            diff_up=np.abs(dc_mat[i,j]-dc_up);  #分别计算上侧和左侧DC系数和当前系数的差值
            diff_left=np.abs(dc_mat[i,j]-dc_left)
            min_diff=min(diff_up,diff_left)  #取最小差值,并将相应的DC系数值记为当前预测值
            if min_diff == diff_up:
                dc_pred = dc_up
                mark_0 +=1
                mark_map.append(0)      #形成辅助信息map图
            elif min_diff == diff_left:
                dc_pred = dc_left
                mark_1 +=1
                mark_map.append(1)
            dc_prediction[i,j] = dc_pred
            ER[i,j] = dc_mat[i,j] - dc_pred#记录预测值和当前值的差作为预测误差
    
    #第一行和第一列系数值前后相减作为预测值，并计算预测误差
    for i in range(1,n):
        dc_pred = dc_mat[0,i] - dc_mat[0,i-1]
        ER[0,i] = dc_pred
    for i in range(1,m):
        dc_pred = dc_mat[i,0] - dc_mat[i-1,0]
        ER[i,0] = dc_pred

    #预测误差矩阵以行为单位进行置换
    data = [i for i in range(0, m)]
    shuffle_index = yates_shuffle(data, encryption_keys)
    ER1 = np.zeros_like(ER)
    for i in range(0,m):
        ER1[i,:] = ER[shuffle_index[i],:]
    #形成最终的（1，m*n）预测误差矩阵
    ER_prediction = ER1.flatten()
    
    return ER_prediction,mark_map

def dc_enc2(dc_ori,dc_pred,encryption_keys):
    '''
    dc_ori: 原始的DC系数   
    dc_pred: DC系数预测误差   
    encryption_key: DC加密密钥
    '''
    dc_max = max(dc_pred)  #取原始DC系数中最大值和最小值
    dc_min = min(dc_pred)

    group_num = int(dc_max-dc_min+1)  #将DC系数划分为group_num组
    if group_num>len(dc_pred):
        group_num = len(dc_pred)
    num = int(len(dc_pred)/group_num)  #每组的DC系数个数
    np.random.seed(2024)
    key_t = np.random.randint(dc_min,dc_max,size=(group_num+1)) #随机生成（1，group_num+1）的密钥序列

    #对密钥序列进行混洗 
    data = [i for i in range(0, group_num+1)]
    per_index = yates_shuffle(data,encryption_keys)
    key = np.zeros_like(key_t)
    for i in range(0,group_num+1):
        key[i] = key_t[per_index[i]]

    #将每一组预测误差值加上密钥序列中对应的值，如若超出[dc_min，dc_max]就再进一步取模，并记录溢出的系数位置
    ER_pred = np.zeros_like(dc_pred)
    used = 0
    over_dc = []
    for i in range(0,group_num):
        for j in range(0,num):
            dc_add = dc_pred[used+j] + key[i]
            if dc_add>dc_max:
                dc_final = dc_add%dc_max
                over_dc.append(used+j)
            elif dc_add<dc_min:
                dc_final = -(abs(dc_add)%abs(dc_min))
                over_dc.append(used+j)
            else:
                dc_final = dc_add
            #if dc_final==dc_min+1:
            #    print(1)
            ER_pred[used+j] = dc_final
        used = used + num
    #预测误差序列中最后不足整组数的那一组单独进行加和操作，并取模和记录
    final_num = len(dc_pred)-(num*group_num)
    for i in range(0,final_num):
        dc_add = dc_pred[used+i] +key[group_num]
        if dc_add>dc_max:
            dc_final = dc_add%dc_max
            over_dc.append(used+i)
        elif dc_add<dc_min:
            dc_final = -(abs(dc_add)%abs(dc_min))
            over_dc.append(used+i)
        else:
            dc_final = dc_add
        ER_pred[used+i] = dc_final
    
    return ER_pred,key,over_dc