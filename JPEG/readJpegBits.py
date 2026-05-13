import numpy as np
from JPEG.utils import *
from JPEG.imgSave import *
def get_dc_table(dc_code):
    num_cat = dc_code[5:21]   #codeword of DCs for each category.
    num_total = sum(num_cat)
    code_len = np.zeros(num_total+1)
    cat= np.array(dc_code[21:21 + num_total])
    ind = 0
    for i in range(16):
        num_temp = num_cat[i]
        while num_temp>0:
            num_temp = num_temp - 1
            code_len[ind] = i+1
            ind = ind + 1
    temp_code = 0
    temp_len_code = code_len[0]
    dc_code_dec = np.zeros(num_total)
    ind = 0
    #The code assignment is followed as Canonical Huffman coding.
    while ind < num_total:
        while code_len[ind] == temp_len_code:
            dc_code_dec[ind] = temp_code
            ind = ind +1
            temp_code = temp_code+1
        temp_code = temp_code<<1
        temp_len_code = temp_len_code + 1
    code_len = code_len[0:-1]
    code = np.zeros([num_total,int(code_len[-1])])
    for i in range(0,num_total):
        dc_code_bin = format(int(dc_code_dec[i]),'b')
        for _ in range(int(code_len[i]-len(dc_code_bin))):
            dc_code_bin = '0'+dc_code_bin
        for j in range(0,int(code_len[i])):
            code[i,j] = int(dc_code_bin[j])
    dc_table = np.zeros((len(cat),int(code_len[-1]+2)),dtype=np.int8)
    dc_table[:,0] = cat.T
    dc_table[:,1] = code_len.T
    dc_table[:,2:] = code
    return dc_table

def get_ac_table(ac_code):
    num_cat = ac_code[5:21]
    num_total = sum(num_cat)
    huff_code_size = np.zeros(num_total+1)
    huff_val = np.array(ac_code[21:21 + num_total])
    ind = 0
    for i in range(16):
        num_temp = num_cat[i]
        while num_temp>0:
            num_temp = num_temp - 1
            huff_code_size[ind] = i+1
            ind = ind + 1
    temp_code = 0
    temp_len_code = huff_code_size[0]
    ac_code_dec = np.zeros(num_total)
    ind = 0
    #The code assignment is followed as Canonical Huffman coding.
    while ind < num_total:
        while huff_code_size[ind] == temp_len_code:
            ac_code_dec[ind] = temp_code
            ind = ind +1
            temp_code = temp_code + 1
        temp_code = temp_code<<1
        temp_len_code = temp_len_code+1
    
    huff_code_size = huff_code_size[:-1]
    code = np.zeros((num_total,16))
    for i in range(0,num_total):
        for j in range(0,int(huff_code_size[i])):
            code[i,j] = ac_code_dec[i]%2
            ac_code_dec[i] = int(ac_code_dec[i]/2)
        t = code[i,0:int(huff_code_size[i])]
        code[i,0:int(huff_code_size[i])] = np.fliplr(code[i,0:int(huff_code_size[i])].reshape(1,len(t)))[0]

    
    ac_order=np.concatenate((huff_val.reshape(num_total,1),huff_code_size.reshape(num_total,1),code),axis=1)
    run = np.floor(ac_order[:,0]/16).reshape(num_total,1)
    size = np.mod(ac_order[:,0],16).reshape(num_total,1)
    ac_table = np.concatenate((run,size,huff_val.reshape(num_total,1),ac_order[:,1:]),axis=1)
    return ac_table.astype(np.int16)

def parse_ecs(jpg_bitstream):
    loc_ff = np.where(jpg_bitstream == 255)[0]	# record the positions of FF.
    loc_sos = np.where(jpg_bitstream[loc_ff+1] == 218)[0] #the position of FFDA
    ind_sos = loc_ff[loc_sos][0]
    loc_eoi = np.where(jpg_bitstream[loc_ff+1] == 217)[0] #the position of FFD9
    ind_eoi = loc_ff[loc_eoi][0]

    length_sos = jpg_bitstream[ind_sos+2]*16*16 + jpg_bitstream[ind_sos+3]
    length_ecs = ind_eoi - ind_sos - length_sos - 2

    ecs = jpg_bitstream[ind_sos+length_sos+2:ind_eoi]
    head = jpg_bitstream[:ind_sos+length_sos+2]
    ind_ff = np.where(ecs == 255)[0]
    num_ff = len(ind_ff)
    #如果在图像数据流中遇到0xFF，应该检测其紧接着的字符，如果是0x00，则表示0xFF是图像流的组成部分，需要进行译码
    #并且这个0x00需要删除
    for i in range(num_ff):
        if ecs[ind_ff[i]+1-i] ==0:
            ecs = np.delete(ecs,ind_ff[i]+1-i)
        else:
            print(ecs[ind_ff[i]+1],ind_ff[i])
    bin_ecs = ''
    for i in range(len(ecs)):
        bin_code = format(int(ecs[i]),'b')
        for _ in range(8-len(bin_code)):
            bin_code = '0'+bin_code
        bin_ecs = bin_ecs + bin_code
    t = len(bin_ecs)
    return head,bin_ecs

def parse_dc_code(bits_sos, tree_huff_dc, pos_dc):
    node = tree_huff_dc
    pointer = pos_dc
    while node.symbol == None:
        if bits_sos[pointer] == '0':
            node = node.left
            pointer+=1
        else:
            node = node.right
            pointer+=1
    cat = node.symbol
    pos_next_ac = pointer + cat
    dc_code = bits_sos[pos_dc:pos_next_ac]
    return int(pos_next_ac), cat, dc_code

def parse_ac_code(bits_sos, tree_huff_ac, table_huff_ac, pos_ac):
    node = tree_huff_ac
    pointer = pos_ac
    num_ac = 0
    ac_code = []

    while num_ac<63:
        while node.symbol == None:
            if bits_sos[pointer] == '0':
                node = node.left
                pointer+=1
            else:
                node = node.right
                pointer+=1
        row = node.symbol
        cur_ac_code = []
        run = table_huff_ac[row][0]
        cat = table_huff_ac[row][1]
        len_vlc = table_huff_ac[row][3]
        ac_vlc = table_huff_ac[row][4:4+len_vlc]
        cur_ac_code = []
        cur_ac_code.append(row)
        cur_ac_code.append([run,cat])
        cur_ac_code.append(run*16+cat)
        cur_ac_code.append(ac_vlc)
        cur_ac_code.append(bits_sos[pointer: pointer + int(cat)])
        ac_code.append(cur_ac_code)
        pointer = pointer + int(cat)
        if run ==15 and cat == 0:
            num_ac = num_ac + 16
        elif run == 0 and cat == 0:
            break
        else:
            num_ac = num_ac+1+run
        node = tree_huff_ac
    return pointer, ac_code