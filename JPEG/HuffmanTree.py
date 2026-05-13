class HuffmanNode:
    def __init__(self, symbol=None):
        self.symbol = symbol
        self.left = None
        self.right = None

def build_huffman_tree(table,type):
    label=[]
    code = []
    if type == 'DC':
        for i in range(len(table)):
            label.append(table[i][0])
            code.append(table[i][2:2+table[i][1]])
    else:
        for i in range(len(table)):
            label.append(i)
            code.append(table[i][4:4+table[i][3]])
    
    root = HuffmanNode()
    for i in range(len(label)):
        node = root
        for b in code[i]:
            if b == 0:
                if node.left == None:
                    node.left = HuffmanNode()
                node = node.left
            else:
                if node.right == None:
                    node.right = HuffmanNode()
                node = node.right
        assert node.symbol == None
        node.symbol = label[i]
    return root