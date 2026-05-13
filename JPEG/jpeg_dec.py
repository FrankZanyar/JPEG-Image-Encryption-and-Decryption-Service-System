from JPEG.jpeg_read import JPEG_OBJECT_rgb
from JPEG.extract import get_mapping_code,extract_secret_data,restore_VLC
from JPEG.utils import *
from JPEG.imgSave import gen_new_header
from JPEG.zigzag import zigzag

def encode_each_component(dct_blocks,table_dc,table_ac):
    dc_code=[]
    new_dc_cat = []
    ac_code=[]

    table_dc = np.pad(table_dc, ((0, 1), (0, 1)), 'constant', constant_values=0)
    table_dc[-1]=table_dc[-2]
    table_dc[-1][0]+=1
    table_dc[-1][1]+=1
    table_dc[-1][-2]=1

    for i in range(len(table_dc)):
        if table_dc[i][0] == 0:
            break
    zeros_code_len = table_dc[i][1]
    zeros_code = ''.join(str(e) for e in table_dc[i][2:2+zeros_code_len])

    #cat和dc哈夫曼表行数的映射
    dic={}
    for i in range(len(table_dc)):
        dic[table_dc[i][0]] = i

    num_block = dct_blocks.shape[2]

    #建立ac系数类别索引字典
    ac_dic = {}
    for i in range(len(table_ac)):
        ac_dic[str(table_ac[i][0])+str(table_ac[i][1])] = i

    for i in range(num_block):
        block = dct_blocks[:,:,i]
        #DC系数编码
        if i == 0:
            dc_value = block[0,0]
        else:
            dc_value = block[0,0] - dct_blocks[0,0,i-1]
        if dc_value==0:
            dc_code.append(zeros_code)
            new_dc_cat.append(0)
        else:
            dc_cat = int(np.floor(np.log2(abs(dc_value)))) + 1 #类别
            new_dc_cat.append(dc_cat)
            dc_cat_code_len = table_dc[dic[dc_cat]][1]#该类在哈夫曼表中码字的长度
            dc_value_encode_index = int(dc_value) if dc_value>0 else int(2**dc_cat -1 + dc_value)#dc系数值编码
            temp = table_dc[dic[dc_cat]][2:2+dc_cat_code_len]#查哈夫曼表，得该类别对应的码字
            temp2 = bin(dc_value_encode_index)[2:].zfill(dc_cat)#dc系数实际的保存值,补0，使得长度跟类别一致
            dc_code.append(''.join(map(str, temp))+temp2)
        #AC系数编码
        dct_seq = zigzag(block)
        ac_zig = dct_seq[1:]
        #生成游程编码
        rsv = []
        nonZero_pos = np.where(ac_zig!=0)[0]#获取该图像块中非零AC系数的位置
        nonZero_pos = np.insert(nonZero_pos,0,-1)
        run_group = nonZero_pos[1:]-nonZero_pos[0:-1]-1
        for j in range(len(run_group)):
            if run_group[j]>=16:
                temp = int(run_group[j]/16)
                for i in range(temp): 
                    rsv.append([15,0])
                rsv.append([run_group[j]-16*temp,ac_zig[nonZero_pos[j+1]]])
            else:
                rsv.append([run_group[j],ac_zig[nonZero_pos[j+1]]])
        rsv.append([0,0])
        #对游程编码进行哈夫曼编码
        cur_block_ac_code = []
        for j in range(len(rsv)):
            cur_ac_code = []
            ac_value = rsv[j][1]
            run = rsv[j][0]
            if ac_value==0:#value=0时的特殊情况
                ac_cat = 0
                row = ac_dic[str(run)+str(ac_cat)]
                cur_ac_code.append(row)
                cur_ac_code.append([run,ac_cat])
                cur_ac_code.append(run*16+ac_cat)
                len_vlc = int(table_ac[row, 3])
                ac_vlc = table_ac[row,4:4+len_vlc]
                cur_ac_code.append(ac_vlc)
                cur_ac_code.append('')
            else:
                ac_cat = int(np.floor(np.log2(abs(ac_value)))) + 1 #类别
                row = ac_dic[str(run)+str(ac_cat)] #查哈希表，得该游程对应的码所在哈夫曼表的行
                cur_ac_code.append(row)
                cur_ac_code.append([run,ac_cat])
                cur_ac_code.append(run*16+ac_cat)
                len_vlc = int(table_ac[row, 3])
                ac_vlc = table_ac[row,4:4+len_vlc]
                cur_ac_code.append(ac_vlc)
                ac_value_encode_index = int(ac_value) if ac_value>0 else int(2**ac_cat -1 + ac_value)#ac系数值编码
                temp = bin(ac_value_encode_index)[2:].zfill(ac_cat) #ac系数实际的保存值,补0，使得长度跟类别一致
                cur_ac_code.append(temp)
            cur_block_ac_code.append(cur_ac_code)
        ac_code.append(cur_block_ac_code)

    return dc_code,ac_code,new_dc_cat

class JPEG_OBJECT_DEC(JPEG_OBJECT_rgb):
    def __init__(self,image_path):
        super().__init__(image_path)
    
    def jpeg_encode(self,dct_Y,dct_Cb,dct_Cr):
        self.Y_dc_code, self.Y_ac_code, self.Y_dc_cat = encode_each_component(
                    dct_Y, self.table_Y_dc, self.table_Y_ac)
        self.Cb_dc_code, self.Cb_ac_code, self.Cb_dc_cat = encode_each_component(
                    dct_Cb, self.table_C_dc, self.table_C_ac)
        self.Cr_dc_code, self.Cr_ac_code, self.Cr_dc_cat = encode_each_component(
                    dct_Cr, self.table_C_dc, self.table_C_ac)

    def secret_extract(self):
        mapping_rsv_Y,mapping_code_Y = get_mapping_code(self.table_Y_ac)
        recover_Y = extract_secret_data(self.Y_ac_code,mapping_rsv_Y,mapping_code_Y)#.astype(np.int8)

        mapping_rsv_C,mapping_code_C = get_mapping_code(self.table_C_ac)
        recover_C = extract_secret_data(self.Cb_ac_code+self.Cr_ac_code,mapping_rsv_C,mapping_code_C)#.astype(np.int8)

        return recover_Y,recover_C
    
    def restore_image(self):
        new_tbl_Y_ac,rst_Y_ac_code = restore_VLC(self.Y_ac_code,self.table_Y_ac)

        Cb_ac_code_len = len(self.Cb_ac_code)
        new_tbl_C_ac,rst_C_ac_code = restore_VLC(self.Cb_ac_code+self.Cr_ac_code,self.table_C_ac)
        rst_Cb_ac_code = rst_C_ac_code[:Cb_ac_code_len]
        rst_Cr_ac_code = rst_C_ac_code[Cb_ac_code_len:]

        new_header = gen_new_header(self.head,new_tbl_Y_ac,new_tbl_C_ac)

        self.head = new_header
        self.table_Y_ac = new_tbl_Y_ac
        self.Y_ac_code = rst_Y_ac_code

        self.table_C_ac = new_tbl_C_ac
        self.Cb_ac_code = rst_Cb_ac_code
        self.Cr_ac_code = rst_Cr_ac_code