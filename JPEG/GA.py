import numpy as np
import copy
def cal_entrophy(freq):
    p = freq/sum(freq)
    p = np.round(p,15)
    t = sum(freq*(-np.log2(p)))
    return t

def Fitness(P, freq, fst_pos, payload, n_max,L):
    N = len(P)
    E = np.zeros(N)
    fits = np.zeros(N)
    for i in range(N):
        p = P[i]
        n_codes = []
        sum_code = 0
        for j in range(0,len(p),L):
            temp = int(p[j:j+2],base=2)
            n_codes.append(temp)
            sum_code = sum_code + 2**temp
        n_codes = np.array(n_codes)
        capacity = np.sum(freq[fst_pos:fst_pos+n_max]*n_codes.T)
        if capacity>=payload and sum_code<=256:
            tmp_freq = copy.deepcopy(freq)
            for j in range(n_max):
                if n_codes[j]>0:
                    cur_freq = tmp_freq[fst_pos+j]/(2**n_codes[j])
                    tmp_freq[fst_pos+j] = cur_freq
                    for _ in range(2**n_codes[j]-1):
                        tmp_freq = np.append(tmp_freq,cur_freq)
            tmp_freq = sorted(tmp_freq,reverse=True)
            E[i] = cal_entrophy(tmp_freq) + sum_code*8
        else:
            E[i] = 0
    E_max = max(E)
    for i in range(N):
        if E[i]!=0:
            fits[i] = E_max - E[i]
    prob = fits/sum(fits)
    return fits,prob,E

def Select(P,N,q):
    new_P = copy.deepcopy(P)
    for i in range(N-1):
        r = np.random.rand()
        tmp = np.where(q>=r)[0]
        new_P[i] = P[tmp[0]]
    return new_P

def Crossover(P,r_c,N):
    len_ind = len(P[0]) #染色体长度
    for i in range(0,N-3,2):#最优位保留
        r = np.random.rand()
        if r<r_c:#交换标记位
            pos = np.random.randint(0,len_ind)
            #python不允许对字符串里的字符进行修改，只能这样交换某一部分元素
            temp = P[i][0:pos]
            P[i] = P[i+1][0:pos] + P[i][pos:len_ind]
            P[i+1] = temp + P[i+1][pos:len_ind]
    
    return P

def Mutation( P, r_m, N ):
    len_ind = len(P[0])
    for i in range(N-1):
        r = np.random.rand()
        if r<r_m:#交换标记位
            pos = np.random.randint(0,len_ind)
            if P[i][pos] == '1':
                P[i] = P[i][0:pos]+'0'+P[i][pos+1:len_ind]
            elif P[i][pos] == '0':
                P[i] = P[i][0:pos]+'1'+P[i][pos+1:len_ind]
    return P


def GA(freq_rsv, payload,r_c,r_m):
    G = 50      #种群的代数
    N = 200     #种群的规模
    L = 2       #每个RS可分配的未使用VLC个数种类（1，2，4，8）

    #Reduce solution size
    N_used = 10
    freq = freq_rsv[:,0]
    ind = np.where(freq>payload)[0]
    if len(ind) == 0:
        fst_pos = 0
    else:
        fst_pos = ind[-1]

    if len(freq) - fst_pos>=N_used:
        n_max = N_used#最大映射集合数目
    else:
        n_max = len(freq)-fst_pos
    
    #Initial
    P = []
    for i in range(N):
        temp = np.random.rand(n_max*L)>0.5
        temp = temp.astype(np.int8)
        t_str = ''
        for item in temp:
            t_str = t_str + str(item)
        P.append(t_str)

    #最优适应度初值 存储每代的最优适应度 最小文件膨胀量存储 每代的最小文件膨胀量
    list_fit,list_E,list_elite = [],[],[]
    #进化迭代
    for i in range(G):
        #计算适应度
        fits,prob,E = Fitness(P,freq,fst_pos,payload,n_max,L)
        q = np.cumsum(prob)         #累加概率
        max_fit=np.max(fits)        #求当代最佳个体
        ind = np.argmax(fits)
        p_elite = P[ind]            #到目前为止最佳位串
        list_E.append(E[ind])       #存储每代的最优膨胀值
        list_fit.append(max_fit)    #存储每代的最优适应度
        list_elite.append(p_elite)
        P[N-1] = p_elite              #最优保留(精英主义选择)
        #轮盘赌选择
        P = Select(P,N,q)
        #交叉
        P = Crossover(P,r_c,N)
        #变异
        P = Mutation(P,r_m,N)
    
    list_E = np.array(list_E)
    ind = np.argmin(list_E)
    opt_solution = np.zeros(len(freq))
    #把二进制每2位转换成int，返回数组
    temp = list_elite[ind]
    output_list = []
    for i in range(0,len(temp),2):
        output_list.append(int(temp[i:i+2],base=2))

    opt_solution[fst_pos:fst_pos+n_max] = np.array(output_list)
    return opt_solution