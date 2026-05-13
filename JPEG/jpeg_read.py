import numpy as np
import copy
from JPEG.invzigzag import invzigzag
from JPEG.readJpegBits import parse_ecs,parse_dc_code,parse_ac_code,get_dc_table,get_ac_table
from JPEG.HuffmanTree import build_huffman_tree
def check_table(table):
    table_head = table[:5]
    table_cat = table[5:21]
    table_value = table[21:]
    if len(table_value) <= max(table_value):
        missing = list(set(range(max(table_value)+1)) - set(table_value))
        for cat in missing:
            table_value = np.append(table_value,cat)
            table_head[3]+=1
            for i in reversed(range(len(table_cat))):
                if table_cat[i] == 0 and table_cat[i-1] != 0:
                    table_cat[i] = 1
                    break
        new_table = np.concatenate((table_head,table_cat,table_value))
        return new_table
    else:
        return table


def decode_each_component(height,width,table_dc,dc_code,dc_cat,ac_code):
    num_block = int(height*width/64)
    dct_image = np.zeros((8,8,num_block),dtype=np.float32)
    cat_len = len(table_dc)
    #构建变长整数编码表VLI
    #cat_len = max([x[0] for x in table_dc]) + 1
    decode_list = []
    for cat in range(cat_len):
        decode_list.append(
            list(range(-(2**cat)+1,(-(2**cat)>>1)+1))+list(range((2**cat)>>1,2**cat)))
    for i in range(num_block):
        cur_dc_code = dc_code[i]
        cur_dc_cat = dc_cat[i]
        cur_ac_code = ac_code[i]
        #DC系数解码
        if cur_dc_cat==0:
            cur_dc_code = 0
        else:
            cur_dc_code = cur_dc_code[-1*cur_dc_cat:]
            cur_dc_code = int(cur_dc_code,base=2)
        if i ==0:
            dc = decode_list[cur_dc_cat][cur_dc_code]
        else:
            dc = dct_image[0,0,i-1] + decode_list[cur_dc_cat][cur_dc_code]
        #AC系数解码
        ac = []
        for j in range(len(cur_ac_code)-1):
            [run,cat] = cur_ac_code[j][1]
            if run==15 and cat==0:
                ac = ac + [0]*16
            else:
                value = cur_ac_code[j][-1]
                value = int(value,base=2)
                ac = ac + [0]*run
                ac = ac + [decode_list[cat][value]]
        ac = ac + [0]*(63-len(ac))
        dct_seq = [dc]+ac
        dct_image[:,:,i] = invzigzag(dct_seq,8,8)
    return dct_image


class JPEG_OBJECT_rgb():
    def __init__(self,image_path):
        data_int = []
        with open(image_path,'rb') as file:
            data = file.read()
            for byte_data in data:
                data_int.append(byte_data)
        image_bitstream = np.array(data_int)
        #找出jpeg文件中储存的图像编码数据，转为二进制表示
        #head是十六进制的文件头，bin_ecs是二进制的图像数据比特流
        #这里返回的ecs不包含最后两个字节的EOF标记
        self.head,self.bin_ecs = parse_ecs(image_bitstream)
        self.get_haffuman_table()
        self.get_dct_blocks()

    def get_haffuman_table(self):
        head = copy.deepcopy(self.head)
        loc_ff = np.where(head == 255)[0]	# record the positions of FF.
        loc_c4 = np.where(head[loc_ff+1] == 196)[0]
        loc_table = loc_ff[loc_c4]
        loc_table_end = loc_ff[loc_c4[-1]+1]

        loc_sos = np.where(head[loc_ff+1] == 218)[0] #the position of FFDA
        ind_sos = loc_ff[loc_sos][0]
        length_sos = head[ind_sos+2]*16*16 + head[ind_sos+3]
        assert ind_sos==loc_table_end

        #找出图像的高和宽
        loc_c0 = np.where(head[loc_ff+1] == 192)[0]
        ind_c0 = loc_ff[loc_c0][0]
        height = head[ind_c0+5]*16*16 + head[ind_c0+6]
        width = head[ind_c0+7]*16*16 + head[ind_c0+8]
        self.mode = head[ind_c0+11]
        if self.mode == 34:
            self.height = height if height%16 == 0 else height + (16-height%16)
            self.width = width if width%16 == 0 else width + (16-width%16)
        elif self.mode == 17:
            self.height = height if height%8 == 0 else height + (8-height%8)
            self.width = width if width%8 == 0 else width + (8-width%8)
        else:
            raise ValueError()

        bf_dht = head[:loc_table[0]]#这里存放的是文件头到哈夫曼表的比特信息
        table_Y_dc = head[loc_table[0]:loc_table[1]]
        table_Y_ac = head[loc_table[1]:loc_table[2]]
        table_C_dc = head[loc_table[2]:loc_table[3]]
        table_C_ac = head[loc_table[3]:loc_table_end]
        af_dht = head[loc_table_end:ind_sos+length_sos+2]#这里存放的是哈夫曼表结束到jpeg文件头的结束
        #找出jpeg文件中储存的哈夫曼表

        table_Y_dc = check_table(table_Y_dc)
        self.table_Y_dc = get_dc_table(table_Y_dc)
        #if max([row[0] for row in self.table_Y_dc]) >= len(self.table_Y_dc):
        #    self.table_Y_dc = expand_table(self.table_Y_dc)

        self.table_Y_ac = get_ac_table(table_Y_ac)
        
        table_C_dc = check_table(table_C_dc)
        self.table_C_dc = get_dc_table(table_C_dc)
        
        self.table_C_ac = get_ac_table(table_C_ac)

        self.head = np.concatenate((bf_dht,table_Y_dc,table_Y_ac,table_C_dc,table_C_ac,af_dht))

    def get_dct_blocks(self):
        #构建哈夫曼索引树
        tree_Y_dc = build_huffman_tree(self.table_Y_dc,'DC')
        tree_Y_ac = build_huffman_tree(self.table_Y_ac,'AC')
        tree_C_dc = build_huffman_tree(self.table_C_dc,'DC')
        tree_C_ac = build_huffman_tree(self.table_C_ac,'AC')

        self.num_block = int(self.height*self.width/64)
        #提取Y分量的信息
        Y_dc_code = []
        Y_ac_code = []
        Y_dc_cat = []
        Cb_dc_code = []
        Cb_ac_code = []
        Cb_dc_cat = []
        Cr_dc_code = []
        Cr_ac_code = []
        Cr_dc_cat = []
        pos_next_dc = 0
        pos_next_ac = 0
        for i in range(self.num_block):
            pos_next_ac, cat, dc_code= parse_dc_code(self.bin_ecs,tree_Y_dc,pos_next_dc)
            Y_dc_code.append(dc_code)
            Y_dc_cat.append(cat)
            pos_next_dc, ac_code = parse_ac_code(self.bin_ecs,tree_Y_ac,self.table_Y_ac,pos_next_ac)
            Y_ac_code.append(ac_code)
            if (i+1)%4 == 0 or self.mode == 17:
                pos_next_ac, cat, dc_code= parse_dc_code(self.bin_ecs,tree_C_dc,pos_next_dc)
                Cb_dc_code.append(dc_code)
                Cb_dc_cat.append(cat)
                pos_next_dc, ac_code = parse_ac_code(self.bin_ecs,tree_C_ac,self.table_C_ac,pos_next_ac)
                Cb_ac_code.append(ac_code)

                pos_next_ac, cat, dc_code= parse_dc_code(self.bin_ecs,tree_C_dc,pos_next_dc)
                Cr_dc_code.append(dc_code)
                Cr_dc_cat.append(cat)
                pos_next_dc, ac_code = parse_ac_code(self.bin_ecs,tree_C_ac,self.table_C_ac,pos_next_ac)
                Cr_ac_code.append(ac_code)

        self.Y_dc_code = Y_dc_code
        self.Y_ac_code = Y_ac_code
        self.Y_dc_cat = Y_dc_cat

        self.Cb_dc_code = Cb_dc_code
        self.Cb_ac_code = Cb_ac_code
        self.Cb_dc_cat = Cb_dc_cat

        self.Cr_dc_code = Cr_dc_code
        self.Cr_ac_code = Cr_ac_code
        self.Cr_dc_cat = Cr_dc_cat

        
        #--------以下为debug用，后续建议删除--------
        self.byte_data_len=0

    
    def jpeg_decode(self):
        #将二进制code转化为dct矩阵
        if self.mode == 34:
            C_h, C_w = int(self.height/2),int(self.width/2)
        else:
            C_h, C_w = self.height, self.width
        dct_Y = decode_each_component(self.height,self.width,self.table_Y_dc,
                    self.Y_dc_code,self.Y_dc_cat,self.Y_ac_code)
        dct_Cb = decode_each_component(C_h, C_w,self.table_C_dc,
                    self.Cb_dc_code,self.Cb_dc_cat,self.Cb_ac_code)
        dct_Cr = decode_each_component(C_h, C_w,self.table_C_dc,
                    self.Cr_dc_code,self.Cr_dc_cat,self.Cr_ac_code)
        return [dct_Y,dct_Cb,dct_Cr]

    def gen_new_ecs(self):
        #生成新的二进制比特流
        buffer = bytearray()
        num_block = len(self.Y_ac_code)
        C_count = 0
        for i in range(num_block):
            #写入Y分量
            buffer.extend(self.Y_dc_code[i].encode('latin1'))
            num_zrv = len(self.Y_ac_code[i])
            for j in range(num_zrv):
                temp = ''.join(str(num) for num in self.Y_ac_code[i][j][3])
                temp = temp + self.Y_ac_code[i][j][4]
                buffer.extend(temp.encode('latin1'))
            #4:2:0采样
            if (i+1)%4 == 0 or self.mode == 17:
                #写入Cb分量
                buffer.extend(self.Cb_dc_code[C_count].encode('latin1'))
                num_zrv = len(self.Cb_ac_code[C_count])
                for j in range(num_zrv):
                    temp = ''.join(str(num) for num in self.Cb_ac_code[C_count][j][3])
                    temp = temp + self.Cb_ac_code[C_count][j][4]
                    buffer.extend(temp.encode('latin1'))
                #写入Cr分量
                buffer.extend(self.Cr_dc_code[C_count].encode('latin1'))
                num_zrv = len(self.Cr_ac_code[C_count])
                for j in range(num_zrv):
                    temp = ''.join(str(num) for num in self.Cr_ac_code[C_count][j][3])
                    temp = temp + self.Cr_ac_code[C_count][j][4]
                    buffer.extend(temp.encode('latin1'))
                C_count = C_count + 1

        self.bin_ecs = buffer.decode('latin1')

    def gen_image(self,name):
        #将比特流写入文件中
        bin_ecs = copy.deepcopy(self.bin_ecs)
        num_pad = 8 - len(bin_ecs)%8
        if num_pad!=8:
            bin_ecs = bin_ecs+'1'*num_pad
        dec_ecs = np.zeros(int(len(bin_ecs)/8),dtype=np.uint8)
        byte_count = 0
        for i in range(0,len(bin_ecs),8):
            temp = bin_ecs[i:i+8]
            dec_ecs[byte_count] = int(temp,base=2)
            byte_count = byte_count + 1
        #遇到255需要添加一个无意义的0
        ind_ff = np.where(dec_ecs==255)[0]
        m = len(ind_ff)
        for i in range(m):
            dec_ecs = np.insert(dec_ecs,ind_ff[i]+1,0)
            ind_ff = ind_ff +1
        #文件尾标志位
        dec_ecs = np.append(dec_ecs,255)
        dec_ecs = np.append(dec_ecs,217)

        jpg_bitstream = list(self.head)+list(dec_ecs)
        byte_data_list=[]
        with open(name,'wb') as file:
            for int_data in jpg_bitstream:
                byte_data = int(int_data).to_bytes(1,'big')
                byte_data_list.append(byte_data)
                file.write(byte_data)

        #--------以下为debug用，后续建议删除--------
        self.byte_data_len=len(byte_data_list)