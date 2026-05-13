import numpy as np
import copy
from JPEG.zigzag import zigzag
from JPEG.invzigzag import invzigzag
from collections import Counter
from Encryption.utils import yates_shuffle,generate_keys_ada

def ac_enc1(key_data,block,user_key):
    '''
    key_data: 密钥种子   
    block: DCT系数块
    user_key: 用户输入的密钥
    '''
    rsv = []
    num_rsv = []
    block8_number = block.shape[2]
    for i in range(block8_number):
        temp = block[:,:,i]
        temp_zig = zigzag(temp)#z字形扫描图像块
        ac_zig = temp_zig[1:64]
        nonZero_pos = np.where(ac_zig!=0)[0]#获取该图像块中非零AC系数的位置
        nonZero_pos = np.insert(nonZero_pos,0,-1)
        run_group = nonZero_pos[1:]-nonZero_pos[0:-1]-1

        for j in range(len(run_group)):
            rsv.append([run_group[j],ac_zig[nonZero_pos[j+1]]])
            
        num_rsv.append(len(run_group))

    run_type = Counter(np.array(rsv)[:,0].flatten())
    run_type = sorted(run_type.items(),key=lambda x:x[0])
    rsv = np.array(rsv)
    per_rsv = copy.deepcopy(rsv)
    for i in range(len(run_type)):
        run = run_type[i][0]    #取出一个run值
        run_num = run_type[i][1]#获取该在run值下的rsv对数量
        if run_num==1:
            continue
        data = [i for i in range(0, run_num)] 
        key = generate_keys_ada(key_data,len(data),user_key)
        per_index = yates_shuffle(data,key)#获得rsv对混洗的索引顺序
        temp_pos = np.where(rsv[:,0]==run)[0]      #获取在该run值下的rsv对位置
        temp_rsv = rsv[temp_pos,:]                 #取出在该run值下的rsv对
        per_temp = copy.deepcopy(temp_rsv)
        for j in range(run_num):
            per_temp[j,:] = temp_rsv[per_index[j],:]
        per_rsv[temp_pos,:] = per_temp
    per_block = np.zeros_like(block)
    used = 0
    for i in range(block8_number):
        ac_temp=[]
        temp_rsv = per_rsv[used:used+num_rsv[i],:]#按照块中rsv对数量的记录取出相应数目的rsv对
        for j in range(num_rsv[i]):     #将这些rsv对还原为z字形扫描的顺序
            for _ in range(int(temp_rsv[j,0])):
                ac_temp.append(0)
            ac_temp.append(temp_rsv[j,1])
        ac_len = len(ac_temp)
        zig = np.zeros(64)
        zig[0] = block[0,0,i]#DC系数
        zig[1:ac_len+1]=np.array(ac_temp)#rsv对对应的AC系数
        per_block[:,:,i]=invzigzag(zig,8,8)#逆z字形重新还原为图像块的形式
        used = used + num_rsv[i]
    
    return per_block    #进行全局RS对置换后的DCT系数块

def ac_enc2(key_data,block,user_key):
    '''
    key_data: 密钥种子   
    block: DCT系数块
    user_key: 用户输入的密钥
    '''
    num_rsv = []
    per_block = block
    block8_number = block.shape[2]

    for i in range(block8_number):
        rsv = []
        temp = block[:,:,i]
        temp_zig = zigzag(temp)
        ac_zig = temp_zig[1:64]
        nonZero_pos = np.where(ac_zig!=0)[0]#获取该图像块中非零AC系数的位置
        nonZero_pos = np.insert(nonZero_pos,0,-1)
        run_group = nonZero_pos[1:]-nonZero_pos[0:-1]-1
        num_rsv.append(len(run_group))   #记录每个块中rsv对的数量
        if num_rsv[i]==0 or num_rsv[i]==1:
            continue
        for j in range(len(run_group)):
            rsv.append([run_group[j],ac_zig[nonZero_pos[j+1]]])
        
        data = [i for i in range(0, num_rsv[i])]
        key = generate_keys_ada(key_data,len(data),user_key)
        per_index = yates_shuffle(data,key)
        rsv = np.array(rsv)
        per_rsv = np.zeros_like(rsv)
        for j in range(len(run_group)):
            per_rsv[j,:] = rsv[per_index[j],:]#块内rsv对进行置换
        ac_temp = []
        for j in range(len(run_group)):
            for _ in range(int(per_rsv[j,0])):
                ac_temp.append(0)
            ac_temp.append(per_rsv[j,1])
        ac_len = len(ac_temp)
        zig = np.zeros(64)
        zig[0] = block[0,0,i]#DC系数
        zig[1:ac_len+1]=np.array(ac_temp)#rsv对对应的AC系数
        per_block[:,:,i]=invzigzag(zig,8,8)#逆z字形重新还原为图像块的形式
    
    return per_block
