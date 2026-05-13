from JPEG.jpeg_read import JPEG_OBJECT_rgb
from JPEG.imgSave import gen_new_header
from JPEG.utils import *
from JPEG.zigzag import zigzag

def encode_each_component(dct_blocks,table_dc,table_ac):
    dc_code=[]
    new_dc_cat = []
    ac_code=[]

    table_dc = np.pad(table_dc, ((0, 1), (0, 1)), 'constant', constant_values=0)
    table_dc[-1]=table_dc[-2]
    table_dc[-1][0]=max([row[0] for row in table_dc]) + 1
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

class JPEG_OBJECT_ENC(JPEG_OBJECT_rgb):
    def __init__(self,image_path):
        super().__init__(image_path)
    
    def jpeg_encode(self,dct_Y,dct_Cb,dct_Cr):
        #将dct矩阵编码
        self.Y_dc_code, self.Y_ac_code, self.Y_dc_cat = encode_each_component(
                    dct_Y, self.table_Y_dc, self.table_Y_ac)
        if max(self.Y_dc_cat) >= len(self.table_Y_dc):
            self.expand_table('Y')
        self.Cb_dc_code, self.Cb_ac_code, self.Cb_dc_cat = encode_each_component(
                    dct_Cb, self.table_C_dc, self.table_C_ac)
        self.Cr_dc_code, self.Cr_ac_code, self.Cr_dc_cat = encode_each_component(
                    dct_Cr, self.table_C_dc, self.table_C_ac)
        if max(self.Cb_dc_cat) >= len(self.table_C_dc) or max(self.Cr_dc_cat) >= len(self.table_C_dc):
            self.expand_table('C')

    def expand_table(self,component):
        #扩展DC系数的哈夫曼表
        head = copy.deepcopy(self.head)
        loc_ff = np.where(head == 255)[0]	# record the positions of FF.
        loc_c4 = np.where(head[loc_ff+1] == 196)[0]
        loc_table = loc_ff[loc_c4]
        loc_table_end = loc_ff[loc_c4[-1]+1]

        loc_sos = np.where(head[loc_ff+1] == 218)[0] #the position of FFDA
        ind_sos = loc_ff[loc_sos][0]
        length_sos = head[ind_sos+2]*16*16 + head[ind_sos+3]
        assert ind_sos==loc_table_end

        bf_dht = head[:loc_table[0]]#这里存放的是文件头到哈夫曼表的比特信息
        table_Y_dc = head[loc_table[0]:loc_table[1]]
        table_Y_ac = head[loc_table[1]:loc_table[2]]
        table_C_dc = head[loc_table[2]:loc_table[3]]
        table_C_ac = head[loc_table[3]:loc_table_end]
        af_dht = head[loc_table_end:ind_sos+length_sos+2]#这里存放的是哈夫曼表结束到jpeg文件头的结束

        if component == 'Y':
            table = table_Y_dc
            table_head = table[:5]
            table_cat = table[5:21]
            table_value = table[21:]
            table_value = np.append(table_value,max(table_value)+1)
            max_len = self.table_Y_dc[-1][1]
            table_cat[max_len]=1
            table_head[3]+=1
            temp = np.concatenate((table_head,table_cat,table_value))
            self.head = np.concatenate((bf_dht,temp,table_Y_ac,table_C_dc,table_C_ac,af_dht))
        else:
            table = table_C_dc
            table_head = table[:5]
            table_cat = table[5:21]
            table_value = table[21:]
            table_value = np.append(table_value,max(table_value)+1)
            max_len = self.table_C_dc[-1][1]
            table_cat[max_len]=1
            table_head[3]+=1
            temp = np.concatenate((table_head,table_cat,table_value))
            self.head = np.concatenate((bf_dht,table_Y_dc,table_Y_ac,temp,table_C_ac,af_dht))

    def secret_embedding(self,secret_Y,secret_Cb,secret_Cr):
        #秘密信息嵌入
        new_code_ac_Y,new_tbl_ac_Y = embedding(self.Y_ac_code,self.table_Y_ac,secret_Y)
        self.Y_ac_code = new_code_ac_Y
        self.table_Y_ac = new_tbl_ac_Y

        Cb_ac_code_len = len(self.Cb_ac_code)
        secret_C = secret_Cb + secret_Cr
        C_ac_code = self.Cb_ac_code + self.Cr_ac_code
        new_code_ac_C,new_tbl_ac_C = embedding(C_ac_code,self.table_C_ac,secret_C)
        self.Cb_ac_code = new_code_ac_C[:Cb_ac_code_len]
        self.Cr_ac_code = new_code_ac_C[Cb_ac_code_len:]
        self.table_C_ac = new_tbl_ac_C
        #更新文件头
        new_header = gen_new_header(self.head,self.table_Y_ac,self.table_C_ac)
        self.head = new_header
        self.gen_new_ecs()

        
def embedding(code_ac,tbl_ac,data):
    freq_rsv = count_rsv(code_ac,tbl_ac)
    new_tbl_ac, opt_solution = construct_code_mapping(freq_rsv,data)
    new_code_ac = replace_ac_code(data,new_tbl_ac,code_ac)
    #new_code_ac = new_code_ac.astype(np.int16)
    return new_code_ac,new_tbl_ac

def replace_ac_code(data,tbl_ac,code_ac):
    ptr_data =0
    num_block = len(code_ac)
    payload = len(data)
    for i in range(num_block):
        num_zrv = len(code_ac[i])
        for j in range(num_zrv):
            ind = np.where(tbl_ac[:,2]==code_ac[i][j][2])[0]
            if len(ind)>1:
                if ptr_data > payload:
                    len_code = tbl_ac[ind[0],3]
                    code_ac[i][j][3] = tbl_ac[ind[0],4:4+len_code]
                    continue
                len_bit = int(np.log2(len(ind)))
                if ptr_data + len_bit > payload:
                    data = data+'0'*(ptr_data+len_bit-payload)
                cur_bits = data[ptr_data:ptr_data+len_bit]
                ind_vlc = ind[int(cur_bits,base=2)]
                len_code = tbl_ac[ind_vlc,3]
                code_ac[i][j][3] = tbl_ac[ind_vlc,4:4+len_code]
                ptr_data = ptr_data + len_bit
            else:
                len_code = tbl_ac[ind[0],3]
                code_ac[i][j][3] = tbl_ac[ind[0],4:4+len_code]
    return code_ac