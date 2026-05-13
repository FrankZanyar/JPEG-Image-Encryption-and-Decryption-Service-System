import numpy as np
import pandas as pd
import copy
from collections import Counter
from JPEG.GA import GA

def count_rsv(ac_code,tbl_ac):
    freq_rsv = np.zeros((tbl_ac.shape[0],2))
    num_block = len(ac_code)
    for i in range(num_block):
        code = ac_code[i]
        for j in range(len(code)):
            cur_row = code[j][0]
            freq_rsv[cur_row][0] = freq_rsv[cur_row][0] + 1
    freq_rsv[:,1] = tbl_ac[:,2]
    freq_rsv = pd.DataFrame(freq_rsv)
    freq_rsv = np.array(freq_rsv.sort_values(by=[0],ascending=[False]))
    return freq_rsv

def cal_code_size(freq_list):
    MAX_CLEN=32
    freq_list = np.append(freq_list,1)
    n=len(freq_list)
    code_size = np.zeros(n,dtype=np.int16)
    code_size_ret = np.zeros(n-1,dtype=np.int16)
    others = np.zeros(n,dtype=np.int16)
    others = others-1
    bits = np.zeros(MAX_CLEN+1,dtype=np.int16)
    while True:
        c1 = -1
        v = 100000000
        for i in range(n):
            if freq_list[i]!=0 and freq_list[i]<=v:
                v = freq_list[i]
                c1 = i
        c2 = -1
        v = 100000000
        for i in range(n):
            if freq_list[i]!=0 and freq_list[i]<=v and i!=c1:
                v = freq_list[i]
                c2 = i
        if c2<0:
            break
        freq_list[c1] = freq_list[c1] + freq_list[c2]
        freq_list[c2] = 0
        code_size[c1] = code_size[c1]+1
        while others[c1] >=0:
            c1 = others[c1]
            code_size[c1] = code_size[c1]+1
        others[c1] = c2
        code_size[c2] = code_size[c2]+1
        while others[c2]>=0:
            c2 = others[c2]
            code_size[c2] = code_size[c2]+1
    for i in range(n):
        if code_size[i]>0:
            bits[code_size[i]] +=1
    for i in range(MAX_CLEN,16,-1):
        while(bits[i]>0):
            j = i-2
            while(bits[j]==0):
                j=j-1
            bits[i]=bits[i]-2
            bits[i-1] = bits[i-1]+1
            bits[j+1] = bits[j+1]+2
            bits[j] = bits[j]-1
    while(bits[i]==0):
        i=i-1
    bits[i] = bits[i]-1
    ptr = 0
    for i in range(16+1):
        tmp = bits[i]
        if tmp>0:
            for j in range(tmp):
                code_size_ret[ptr] = i
                ptr = ptr+1
                     
    return code_size_ret

def get_opt_huff_table(code_size,huff_val):
    num_total = len(huff_val)
    temp_code = 0
    temp_len_code = code_size[0]
    ac_code_dec = np.zeros(num_total)
    ind = 0
    code_size = np.append(code_size,0)

    while ind <num_total:
        while code_size[ind] == temp_len_code:
            ac_code_dec[ind] = temp_code
            ind = ind + 1
            temp_code = temp_code + 1
        temp_code = temp_code<<1
        temp_len_code = temp_len_code + 1
    code_size = code_size[:-1]
    code = np.zeros((num_total,16))
    for i in range(num_total):
        for j in range(code_size[i]):
            code[i,j] = ac_code_dec[i]%2
            ac_code_dec[i] = int(ac_code_dec[i]/2)
        code[i][0:code_size[i]] = np.fliplr([code[i][0:code_size[i]]])[0]
    huff_val = huff_val.reshape((-1,1))
    code_size = code_size.reshape((-1,1))
    ac_order = np.concatenate((huff_val,code_size,code),axis=1)
    run = np.floor(ac_order[:,0]/16).reshape((-1,1))
    size = np.mod(ac_order[:,0],16).reshape((-1,1))

    ac_table = np.concatenate((run,size,huff_val,ac_order[:,1:]),axis=1)
    
    return ac_table.astype(np.int16)

def construct_code_mapping(freq_rsv,data):
#Constrcut the VLC Mapping Relationship according to frequencies and payload
    #Count the RSVs according to the corresponding ac huffman table.
    freq_rsv = freq_rsv[freq_rsv[:,0]>0,:]
    #Solver: Genetic Algorithm.
    payload = len(data)
    r_c = 0.8
    r_m = 0.3
    opt_solution = GA(freq_rsv, payload,r_c,r_m)
    #For debug usage
    #with open('./data/opt_solution.txt')as file:
    #    data = file.read().split('\t')
    #    opt_solution = np.zeros(len(data))
    #    for i in range(len(data)):
    #        opt_solution[i] = data[i]
    new_freq_rsv = copy.deepcopy(freq_rsv)
    for i in range(len(opt_solution)):
        if opt_solution[i]:
            curFreq = new_freq_rsv[i,0]/(2**opt_solution[i])
            new_freq_rsv[i,0] = curFreq
            for _ in range(int(2**opt_solution[i]-1)):
                new_freq_rsv = np.append(new_freq_rsv,[new_freq_rsv[i]],axis=0)

    new_freq_rsv = pd.DataFrame(new_freq_rsv)
    new_freq_rsv = np.array(new_freq_rsv.sort_values(by=[0],ascending=False))
    code_size = cal_code_size(new_freq_rsv[:,0])
    new_table_ac = get_opt_huff_table(code_size,new_freq_rsv[:,1])

    return new_table_ac,opt_solution

def gen_new_dht_table(new_tbl_ac,ac_dht_bits):  
    len_value = len(new_tbl_ac[:,0])
    ac_dht_bits[3] = len_value+19
    new_bits = Counter(np.array(new_tbl_ac)[:,3].flatten())
    new_bits = sorted(new_bits.items(),key=lambda x:x[0])
    bits = [0]*16
    for i in range(len(new_bits)):
        bits[new_bits[i][0]-1] = new_bits[i][1]
    #bits[:len(new_bits)] = new_bits
    ac_dht_bits[5:] = bits
    ac_dht_value = [0]*len_value
    for i in range(len_value):
        ac_dht_value[i] = new_tbl_ac[i,2]
    return np.concatenate((ac_dht_bits,np.array(ac_dht_value)))

def gen_new_header_gray(dec_jpg,new_tbl_Y_ac):
    loc_ff = np.where(dec_jpg == 255)[0]	# record the positions of FF.
    loc_c4 = np.where(dec_jpg[loc_ff+1] == 196)[0]
    loc_table = loc_ff[loc_c4]
    loc_table_end = loc_ff[loc_c4[-1]+1]

    loc_sos = np.where(dec_jpg[loc_ff+1] == 218)[0] #the position of FFDA
    ind_sos = loc_ff[loc_sos][0]
    length_sos = dec_jpg[ind_sos+2]*16*16 + dec_jpg[ind_sos+3]
    assert ind_sos==loc_table_end

    bf_dht = dec_jpg[:loc_table[0]]#这里存放的是文件头到哈夫曼表的比特信息
    table_Y_dc = dec_jpg[loc_table[0]:loc_table[1]]
    t = np.concatenate((bf_dht,table_Y_dc))
    table_Y_ac = dec_jpg[loc_table[1]:loc_table_end]
    #table_Y_ac = dec_jpg[loc_table[1]:loc_table[2]]
    #table_C_dc = dec_jpg[loc_table[2]:loc_table[3]]
    #table_C_ac = dec_jpg[loc_table[3]:loc_table_end]
    af_dht = dec_jpg[loc_table_end:ind_sos+length_sos+2]#这里存放的是哈夫曼表结束到jpeg文件头的结束

    ac_dht_bits_Y = copy.deepcopy(table_Y_ac[:21])
    new_table_Y_ac = gen_new_dht_table(new_tbl_Y_ac,ac_dht_bits_Y)

    return np.concatenate((bf_dht,table_Y_dc,new_table_Y_ac,af_dht))