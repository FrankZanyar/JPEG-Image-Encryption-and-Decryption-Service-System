import numpy as np
import copy
from collections import Counter

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


def gen_new_header(dec_jpg,new_tbl_Y_ac,new_tbl_C_ac):
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
    table_Y_ac = dec_jpg[loc_table[1]:loc_table[2]]
    table_C_dc = dec_jpg[loc_table[2]:loc_table[3]]
    table_C_ac = dec_jpg[loc_table[3]:loc_table_end]
    af_dht = dec_jpg[loc_table_end:ind_sos+length_sos+2]#这里存放的是哈夫曼表结束到jpeg文件头的结束

    ac_dht_bits_Y = copy.deepcopy(table_Y_ac[:21])
    new_table_Y_ac = gen_new_dht_table(new_tbl_Y_ac,ac_dht_bits_Y)

    ac_dht_bits_C = copy.deepcopy(table_C_ac[:21])
    new_table_C_ac = gen_new_dht_table(new_tbl_C_ac,ac_dht_bits_C)

    return np.concatenate((bf_dht,table_Y_dc,new_table_Y_ac,table_C_dc,new_table_C_ac,af_dht))