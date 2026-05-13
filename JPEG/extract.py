import numpy as np
import pandas as pd
from collections import Counter
from JPEG.utils import count_rsv,cal_code_size,get_opt_huff_table
from JPEG.readJpegBits import get_dc_table,get_ac_table,parse_ecs,parse_dc_code,parse_ac_code
#from imgSave import gen_new_header,gen_new_ecs

def int_to_bin(num,k):
    b = bin(num)[2:]
    ret = np.zeros(k,dtype=np.int8)
    str_ind = 0
    for i in range(k-len(b),k):
        ret[i] = int(b[str_ind])
        str_ind = str_ind+1
    return list(ret)

def get_mapping_code(tbl_ac):
    counter = Counter(np.array(tbl_ac[:,2]))
    mapping_rsv = []
    for item in counter.items():
        if item[1]>1:
            mapping_rsv.append([item[0],item[1]])
    mapping_rsv = np.array(mapping_rsv)
    mapping_code = []
    for i in range(len(mapping_rsv[:,0])):
        ind = np.where(mapping_rsv[i,0]==tbl_ac[:,2])[0]
        temp=[]
        for j in range(mapping_rsv[i,1]):
            temp.append(tbl_ac[ind[j],4:4+tbl_ac[ind[j],3]])
        mapping_code.append(temp)
    return mapping_rsv,mapping_code

def extract_secret_data(ac_code,mapping_rsv,mapping_code):
    data = ''
    num_blocks = len(ac_code)

    for i in range(num_blocks):
        num_zrv = len(ac_code[i])
        for j in range(num_zrv):
            cur_rsv = ac_code[i][j][2]
            ind = np.where(cur_rsv==mapping_rsv[:,0])[0]
            if len(ind!=0): #and ptr_data<payload:
                len_bit = int(np.log2(mapping_rsv[ind[0],1]))
                for k in range(mapping_rsv[ind[0],1]):
                    if np.array_equal(ac_code[i][j][3],mapping_code[ind[0]][k]):
                        #data[ptr_data:ptr_data+len_bit] = int_to_bin(k,len_bit)
                        temp = int_to_bin(k,len_bit)
                        for item in temp:
                            data = data + str(item)
                        break
    return data

def restore_VLC(ac_code,tbl_ac):
    freq_rsv = count_rsv(ac_code,tbl_ac)
    statistic = sorted(list(set(freq_rsv[:,1])))
    freq_rsv_cover = np.zeros((len(statistic),2))
    for i in range(len(statistic)):
        ind = np.where(statistic[i]==freq_rsv)[0]
        freq_rsv_cover[i,0] = sum(freq_rsv[ind,0])
        freq_rsv_cover[i,1] = statistic[i]
    freq_rsv_cover = pd.DataFrame(freq_rsv_cover)
    freq_rsv_cover = np.array(freq_rsv_cover.sort_values(by=[0],ascending=[False]))
    code_size = cal_code_size(freq_rsv_cover[:,0])
    new_tbl_ac = get_opt_huff_table(code_size,freq_rsv_cover[:,1])
    rst_ac_code = ac_code
    num_block = len(ac_code)
    for i in range(num_block):
        num_zrv = len(ac_code[i])
        for j in range(num_zrv):
            ind = np.where(ac_code[i][j][2]==new_tbl_ac[:,2])[0]
            rst_ac_code[i][j][3] = new_tbl_ac[ind[0],4:4+new_tbl_ac[ind[0],3]]

    return new_tbl_ac,rst_ac_code

def extract_jpg_gray(name):
    #For testing usage
    data_int = []
    with open(name,'rb') as file:
        data = file.read()
        for byte_data in data:
            data_int.append(byte_data)
    image_bitstream = np.array(data_int)
    #找出jpeg文件中储存的图像编码数据，转为二进制表示
    bin_ecs = parse_ecs(image_bitstream)
    #print(len(bin_ecs))
    #找出jpeg文件中储存的哈夫曼表
    loc_ff = np.where(image_bitstream == 255)[0]	# record the positions of FF.
    loc_c4 = np.where(image_bitstream[loc_ff+1] == 196)[0]
    loc_table = loc_ff[loc_c4]
    loc_table_end = loc_ff[loc_c4[-1]+1]
    table_Y_dc = data_int[loc_table[0]:loc_table[1]]
    table_Y_dc = get_dc_table(table_Y_dc)
    table_Y_ac = data_int[loc_table[1]:loc_table_end]
    table_Y_ac = get_ac_table(table_Y_ac)

    #找出图像的高和宽
    loc_c0 = np.where(image_bitstream[loc_ff+1] == 192)[0]
    ind_c0 = loc_ff[loc_c0][0]
    height = image_bitstream[ind_c0+5]*16*16 + image_bitstream[ind_c0+6]
    width = image_bitstream[ind_c0+7]*16*16 + image_bitstream[ind_c0+8]
    num_block = int(height*width/64)
    #提取Y分量的信息
    Y_dc_code = []
    Y_ac_code = []
    pos_next_dc = 0
    pos_next_ac = 0
    for i in range(num_block):
        pos_next_ac, cat, dc_code= parse_dc_code(bin_ecs,table_Y_dc,pos_next_dc)
        Y_dc_code.append(dc_code)
        pos_next_dc, ac_code = parse_ac_code(bin_ecs,table_Y_ac,pos_next_ac)
        Y_ac_code.append(ac_code)
    
    mapping_rsv,mapping_code = get_mapping_code(table_Y_ac)
    recover = extract_secret_data(Y_ac_code,mapping_rsv,mapping_code)#.astype(np.int8)
    new_tbl_ac,rst_ac_code = restore_VLC(Y_ac_code,table_Y_ac)
    new_header = gen_new_header(image_bitstream,new_tbl_ac)
    new_ecs = gen_new_ecs(len(bin_ecs),Y_dc_code,rst_ac_code)

    new_jpg_bitstream = list(new_header)+list(new_ecs)
    with open('./recover_result.jpg','wb') as file:
        for int_data in new_jpg_bitstream:
            byte_data = int(int_data).to_bytes(1,'big')
            file.write(byte_data)

    return recover

if __name__ == '__main__':
    extract_jpg_gray('./embedding_result.jpg',5218)